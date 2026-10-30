#!/usr/bin/env python3
"""
Crew seats / HF brains / watchdog / sibling-seat tests — stdlib only.

Run:  ~/workspace/venv/bin/python test_crew.py
Covers: crew_seats.json shape + verified HF model assignments; the
HF ladder (fake transports prove order + fall-through; no token means
KeyPending BEFORE any network); the watchdog (re-route + logged
revival; floor when all fueled rungs are down); and the three Hermes
sibling seats (Vaelor / Qrow / Souviern — three seats, no merged
identity anywhere). Temp dirs only. Exit 0 = all green.
"""

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

TMP = tempfile.mkdtemp(prefix="omega-crew-test-")
AUDIT = os.path.join(TMP, "audit.jsonl")
os.environ["FLEET_AUDIT_LOG"] = AUDIT
for var in ("HF_TOKEN", "OPENROUTER_API_KEY", "OPENCODE_ZEN_API_KEY",
            "OMEGA_LOCAL_MODEL", "DECISION_LAYER_LOCAL_MODEL", "FLEET_STOP"):
    os.environ.pop(var, None)

FAILURES = []

# Model names verified against the live HF API 2026-10-30 (gated: false).
VERIFIED_UNGATED = {"Qwen/Qwen2.5-7B-Instruct", "Qwen/Qwen2.5-Coder-7B-Instruct",
                    "mistralai/Mistral-7B-Instruct-v0.3", "HuggingFaceH4/zephyr-7b-beta",
                    "microsoft/Phi-3.5-mini-instruct", "Qwen/Qwen2.5-3B-Instruct",
                    "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"}


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def main():
    import hf_brain
    import watchdog

    seats = hf_brain.seats()
    members = [s["member"] for s in seats]
    check("11 crew seats, each with subsystem + ladder + HF model",
          len(seats) == 11 and all(s.get("subsystem") and s.get("ladder")
                                   and s.get("hf_model") for s in seats),
          str(members))
    check("every HF assignment is a verified ungated model name",
          all(s["hf_model"] in VERIFIED_UNGATED for s in seats),
          str({s["member"]: s["hf_model"] for s in seats
               if s["hf_model"] not in VERIFIED_UNGATED}))
    check("no merged 'Trine' identity anywhere in the seats",
          not any("Trine" in m for m in members)
          and "Trine" not in open(os.path.join(HERE, "crew_seats.json")).read())
    for member in ("Vaelor", "Hermes"):
        check(f"seat exists: {member}", member in members)
    check("no separate Qrow/Souviern seats — they are forms, not siblings",
          "Qrow" not in members and "Souviern" not in members)
    ellen = hf_brain.assignment("Ellen Joe")
    check("Ellen Joe holds SCOUT-RUNNER as her scout form Qrow",
          "SCOUT-RUNNER" in ellen["subsystem"]
          and any("Qrow" in f for f in ellen.get("forms", [])))
    senku = hf_brain.assignment("Senku")
    check("Senku holds PRODUCER as his producer form Souviern",
          "PRODUCER" in senku["subsystem"]
          and any("Souviern" in f for f in senku.get("forms", [])))

    import hermes_adapter
    check("adapter PROFILE_SEATS: Vaelor + Ellen (Qrow form) + Senku (Souviern form)",
          hermes_adapter.PROFILE_SEATS == {"FORGE": "Vaelor",
                                           "SCOUT-RUNNER": "Ellen Joe",
                                           "PRODUCER": "Senku"}
          and hermes_adapter.PROFILE_FORMS == {"SCOUT-RUNNER": "Qrow",
                                               "PRODUCER": "Souviern"})

    # ------------------------------------------------------------ ladder
    out = hf_brain.chat("Senku", "ping",
                        transports={"hf": lambda m, p: "hf-answer"})
    check("HF rung answers first when fueled",
          out["rung"] == "hf" and out["text"] == "hf-answer"
          and out["model"] == "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B")

    def down(member, prompt):
        raise hf_brain.RungDown("fake down")
    out = hf_brain.chat("Senku", "ping",
                        transports={"hf": down,
                                    "openrouter": lambda m, p: "or-answer"})
    check("HF down -> OpenRouter answers; fall-through recorded",
          out["rung"] == "openrouter" and len(out["fell_through"]) == 1)
    out = hf_brain.chat("Senku", "ping",
                        transports={"hf": down, "openrouter": down,
                                    "zen": down, "ollama-local": down})
    check("all fueled rungs down -> heuristic floor, honestly labeled",
          out["rung"] == "heuristic-floor" and "NOT a model" in out["text"])
    out = hf_brain.chat("Senku", "ping")  # no token, no fakes for HF
    check("no HF_TOKEN -> HF rung is KEY-PENDING and the seat still answers (floor)",
          out["rung"] == "heuristic-floor"
          and any("HF_TOKEN" in f for f in out["fell_through"]))

    # ----------------------------------------------------------- watchdog
    probes = {"hf": False, "openrouter": True}
    row = watchdog.check_seat(
        "Ellen Joe", probe=lambda r: probes.get(r, r == "heuristic-floor"))
    check("watchdog re-routes a seat whose top rung is down",
          row["active_rung"] == "openrouter" and row["revived"] is True
          and row["down"] == ["hf"])
    logged = open(AUDIT).read()
    check("the revival is in the audit log",
          '"WATCHDOG_REVIVE"' in logged and "Ellen Joe" in logged)
    row = watchdog.check_seat("Ellen Joe", probe=lambda r: r == "heuristic-floor")
    check("all fueled rungs down -> watchdog lands the seat on its floor",
          row["active_rung"] == "heuristic-floor")
    check("the floor landing is logged as WATCHDOG_FLOOR",
          '"WATCHDOG_FLOOR"' in open(AUDIT).read())
    report = watchdog.health_report()
    check("health report covers every seat; all sit on the floor today (no keys on this machine)",
          len(report) == 11
          and all(r["active_rung"] == "heuristic-floor" for r in report))

    print(f"\n{len(FAILURES)} failure(s)" if FAILURES else "\nALL GREEN")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
