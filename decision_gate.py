#!/usr/bin/env python3
"""
Decision Gate — THE EQUATION, as the fleet's go/no-go interface
(Kali Fleet: OMEGA).

THE EQUATION is the Empire's governing decision math, and its home is
the decision layer (empire/work/decision-layer/). This module is a
faithful port of what is RECORDED there — nothing invented:

  * Typed questions, answered in one pass — Choice (pick 1 of N),
    Score (ordered levels), Noul (truth probability) — each answer
    carrying per-option probabilities and a confidence, where
    confidence is the probability mass on the returned answer.
    (decision-layer README, "The three primitives".)
  * The confidence policy: act >= 0.85, review 0.60-0.85,
    escalate < 0.60. (README, "Confidence policy".)
  * THE DISPOSITION LAW: the model advises, the law disposes.
    law_disposition() (decision_layer/raga.py, documented in
    RAGA-SYSTEM-ONE.md) is deterministic code and the final gate:
      Law 1 — critical severity disposes to ESCALATE (the sentinel's
              own CRITICAL, or the top severity score). Either suffices.
      Law 2 — a secret-leak finding without proven sanctioned
              provenance IN THE RECORD escalates + forces the
              key-rotation flag, whatever any model answer says.
      Law 3 — verdict unexplained/hostile at confidence >= 0.60
              escalates.
    The law is one-directional: it can force an escalation, it never
    forces an allow. Only when no law trigger fires does the advising
    band dispose.

BACKEND LADDER (same order + labels as the decision layer):
  (a) typesafe BLOCKED-on-key · (b) openrouter-decisions
  WIRED-NOT-FUELED · (b2) opencode-zen WIRED-NOT-FUELED ·
  (c) openrouter-llm WIRED-NOT-FUELED · (d) ollama-local EMPTY
  (the Heretic chair — see heretic_slot.py) · (e) heuristic LIVE.

Only rung (e) answers in this build. The LLM rungs exist as adapters:
calling one raises UnfueledRung and the ladder falls through, exactly
like the real ladder — it never fabricates an answer. And the gate
FAILS CLOSED: any backend error, malformed reply, or transport failure
disposes to ESCALATE with driver "fail-closed", never to allow.
(That wrapper is the fix the 2026-10-29 Hermes reconciliation §3.1.1
specified for HermesGateClient; it lives here so every caller inherits
it.)

Stdlib only.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import kali_bot  # shared audit mechanism

ACT_BAND = 0.85
REVIEW_BAND = 0.60

DISPOSITIONS = ("ALLOW", "REVIEW", "ESCALATE")


class UnfueledRung(Exception):
    """An adapter rung with no fuel (no key / no model). The ladder
    falls through; it never treats this as an answer."""


class GateError(Exception):
    """Malformed backend output. The gate fails closed on this."""


# ------------------------------------------------------------ primitives

def choice_answer(options, probabilities):
    if set(probabilities) != set(options):
        raise GateError("choice probabilities must cover exactly the options")
    total = sum(probabilities.values())
    if total <= 0:
        raise GateError("choice probabilities sum to zero")
    probs = {k: v / total for k, v in probabilities.items()}
    pick = max(options, key=lambda o: probs[o])
    return {"type": "choice", "choice": pick, "probabilities": probs,
            "confidence": probs[pick]}


def score_answer(levels, probabilities):
    a = choice_answer(levels, probabilities)
    return {"type": "score", "score": a["choice"],
            "index": levels.index(a["choice"]),
            "probabilities": a["probabilities"],
            "confidence": a["confidence"]}


def noul_answer(probability):
    p = min(1.0, max(0.0, float(probability)))
    return {"type": "noul", "probability": p, "verdict": p > 0.5,
            "confidence": p if p > 0.5 else 1.0 - p}


def band(confidence):
    """The recorded confidence policy: act >= 0.85, escalate < 0.60,
    review between."""
    if confidence >= ACT_BAND:
        return "act"
    if confidence < REVIEW_BAND:
        return "escalate"
    return "review"


# ------------------------------------------------------------------ law

def law_disposition(answers, finding=None):
    """The Boss's standing law, ported from decision_layer/raga.py as
    documented in RAGA-SYSTEM-ONE.md. Returns (disposition, driver,
    reasons, forced_flags). One-directional: law can force ESCALATE;
    it can never force ALLOW."""
    finding = finding or {}
    reasons = []
    forced = {}

    severity = answers.get("severity") or {}
    sev_top = (severity.get("type") == "score"
               and severity.get("index", -1) == len(severity.get("probabilities", {})) - 1
               and severity.get("confidence", 0) >= REVIEW_BAND)
    # Case-normalize BEFORE the law reads the finding: the sentinel's
    # real vocabulary is UPPERCASE (severity "CRITICAL", kind
    # "SECRET_LEAK"). The pre-fix port matched lowercase only, so a
    # CRITICAL secret-leak finding missed Laws 1-2 and a calm model
    # answer disposed to ALLOW — a fail-open (SUK-D5, war-room Lane 3).
    _sev = str(finding.get("severity", "")).strip().lower()
    _kind = str(finding.get("kind", "")).strip().lower()
    if _sev in ("critical", "crit", "severe") or sev_top:
        reasons.append("Law 1: critical severity disposes")

    if _kind == "secret_leak" and not finding.get("provenance_proven"):
        reasons.append("Law 2: secret-leak without proven sanctioned provenance")
        forced["key_rotation"] = True

    verdict = answers.get("verdict") or {}
    if (verdict.get("type") == "choice"
            and verdict.get("choice") in ("unexplained", "hostile")
            and verdict.get("confidence", 0) >= REVIEW_BAND):
        reasons.append("Law 3: verdict unexplained/hostile at confidence >= 0.60")

    if reasons:
        return "ESCALATE", "law", reasons, forced

    # No law trigger: the model's own advice disposes — on the `bark`
    # answer when the question set carries one (RAGA-SYSTEM-ONE: "bark
    # at act-band confidence, review in the middle bands, silence when
    # calm"). The recorded confidence policy supplies the bands:
    # act => the bark verdict stands; review => REVIEW; escalate-band
    # confidence (< 0.60) => ESCALATE — unsure goes up, never down.
    bark = answers.get("bark")
    if bark and bark.get("type") == "noul":
        b = band(bark.get("confidence", 0))
        if b == "act":
            return ("ESCALATE", "model", ["model advises bark (act band)"], forced) \
                if bark["verdict"] else \
                ("ALLOW", "model", ["model calm (act band)"], forced)
        if b == "review":
            return "REVIEW", "model", ["model advice in the review band"], forced
        return "ESCALATE", "model", ["model confidence below the escalate band"], forced
    # Question sets without a bark answer: the weakest band disposes.
    bands = [band(a.get("confidence", 0)) for a in answers.values()]
    if "escalate" in bands:
        return "ESCALATE", "model", ["advising band: escalate"], forced
    if "review" in bands:
        return "REVIEW", "model", ["advising band: review"], forced
    return "ALLOW", "model", ["advising band: act"], forced


# --------------------------------------------------------------- backends

def _heuristic_answers(questions, state):
    """Rung (e): the offline deterministic cue-scorer. Probabilities are
    normalized cue scores — uncalibrated, and labeled as such, exactly
    as the decision layer labels them. Cue hints ride on each question
    spec under 'hints': {answer: [cue phrases]}."""
    text = (state or "").lower()
    out = {}
    for name, spec in questions.items():
        hints = spec.get("hints", {})
        if spec["type"] == "noul":
            cues = hints.get("true", [])
            hits = sum(1 for c in cues if c.lower() in text)
            p = 0.15 + 0.2 * hits if cues else 0.15
            out[name] = noul_answer(min(p, 0.95))
            continue
        options = spec["options"]
        scores = {}
        for opt in options:
            cues = hints.get(opt, [])
            scores[opt] = 1.0 + 2.0 * sum(1 for c in cues if c.lower() in text)
        out[name] = (score_answer(options, scores) if spec["type"] == "score"
                     else choice_answer(options, scores))
    return out


def _unfueled(rung, why):
    def call(questions, state):
        raise UnfueledRung(f"rung {rung} is an adapter with no fuel: {why}")
    return call


RUNGS = [
    ("typesafe", "BLOCKED",
     _unfueled("typesafe", "TYPESAFE_API_KEY unset; account is the Boss's tap")),
    ("openrouter-decisions", "WIRED-NOT-FUELED",
     _unfueled("openrouter-decisions", "OPENROUTER_API_KEY unset")),
    ("opencode-zen", "WIRED-NOT-FUELED",
     _unfueled("opencode-zen", "stored key returns 401; fresh key is the Boss's vault deposit")),
    ("openrouter-llm", "WIRED-NOT-FUELED",
     _unfueled("openrouter-llm", "OPENROUTER_API_KEY unset")),
    ("ollama-local", "EMPTY", None),  # wired to heretic_slot below
    ("heuristic", "LIVE", _heuristic_answers),
]


def _local_rung(questions, state):
    import heretic_slot
    return heretic_slot.answer(questions, state)  # raises SlotEmpty unless armed


RUNGS[4] = ("ollama-local", "EMPTY", _local_rung)


# ------------------------------------------------------------------ gate

def decide(questions, state="", finding=None, transport=None):
    """Run the ladder; dispose by the Equation (law over bands).
    transport: optional callable(questions, state) -> answers, used by
    tests and by future live rungs. FAIL-CLOSED: transport exceptions,
    malformed answers, and a fully-failed ladder all dispose to
    ESCALATE with driver 'fail-closed'. Never raises for backend
    problems; raises GateError only for a malformed QUESTION set."""
    for name, spec in questions.items():
        if spec.get("type") not in ("choice", "score", "noul"):
            raise GateError(f"question {name!r}: unknown type {spec.get('type')!r}")
        if spec["type"] in ("choice", "score") and not spec.get("options"):
            raise GateError(f"question {name!r}: options required")

    answers, backend, fell_through = None, None, []
    if transport is not None:
        try:
            answers = transport(questions, state)
            backend = "transport"
        except Exception as e:  # noqa: BLE001 — fail closed, by law
            result = {"answers": None, "backend": None,
                      "disposition": "ESCALATE", "driver": "fail-closed",
                      "reasons": [f"transport failed: {e}"], "forced": {},
                      "fell_through": []}
            kali_bot.audit({"action": "DECISION_GATE", **result})
            return result
    else:
        for rung_name, _state, call in RUNGS:
            try:
                answers = call(questions, state)
                backend = rung_name
                break
            except Exception as e:  # noqa: BLE001 — fall through / fail closed
                fell_through.append(f"{rung_name}: {e}")
        if answers is None:
            result = {"answers": None, "backend": None,
                      "disposition": "ESCALATE", "driver": "fail-closed",
                      "reasons": ["every rung failed"] + fell_through,
                      "forced": {}, "fell_through": fell_through}
            kali_bot.audit({"action": "DECISION_GATE", **result})
            return result

    try:
        for name, a in answers.items():
            if "confidence" not in a or "type" not in a:
                raise GateError(f"answer {name!r} missing type/confidence")
    except (AttributeError, TypeError, GateError) as e:
        result = {"answers": None, "backend": backend,
                  "disposition": "ESCALATE", "driver": "fail-closed",
                  "reasons": [f"malformed answers: {e}"], "forced": {},
                  "fell_through": fell_through}
        kali_bot.audit({"action": "DECISION_GATE", **result})
        return result

    disposition, driver, reasons, forced = law_disposition(answers, finding)
    result = {"answers": answers, "backend": backend,
              "disposition": disposition, "driver": driver,
              "reasons": reasons, "forced": forced,
              "fell_through": fell_through}
    kali_bot.audit({"action": "DECISION_GATE", "backend": backend,
                    "disposition": disposition, "driver": driver,
                    "reasons": reasons})
    return result


# Canonical Raga question set (RAGA-SYSTEM-ONE.md) with heuristic hints.
RAGA_QUESTIONS = {
    "verdict": {"type": "choice",
                "options": ["explained_empire_work", "false_positive",
                            "unexplained", "hostile"],
                "hints": {"explained_empire_work": ["empire", "registered lane", "own work"],
                          "false_positive": ["sample", "fixture", "test data"],
                          "unexplained": ["unknown", "unexplained", "no record"],
                          "hostile": ["exfil", "injection", "payload", "stolen"]}},
    "severity": {"type": "score",
                 "options": ["log_only", "watch", "alert", "critical"],
                 "hints": {"critical": ["critical", "secret", "key", "leak"],
                           "alert": ["alert", "failed", "denied"],
                           "watch": ["watch", "drift"]}},
    "quarantine": {"type": "noul", "hints": {"true": ["quarantine", "isolate", "unknown origin"]}},
    "key_rotation": {"type": "noul", "hints": {"true": ["secret", "key", "token", "leak"]}},
    "bark": {"type": "noul", "hints": {"true": ["critical", "hostile", "leak", "unexplained"]}},
}


if __name__ == "__main__":
    out = decide(RAGA_QUESTIONS,
                 state="unexplained file with a secret-shaped key value, no record",
                 finding={"kind": "secret_leak", "provenance_proven": False})
    print(json.dumps(out, indent=2))


# Zero-Trust Verification Layer — this module's clause.
VERIFICATION = {'clause': 'break-it-then-fix-it', 'origin': 'networkchuck-adjacent (Pattern 2 stage 3: fix a narrow class of failures + verify)', 'check': 'test_omega.py negative tests: calm model + secret leak -> ESCALATE (law); dead transport -> ESCALATE (fail-closed); malformed answers -> ESCALATE'}
