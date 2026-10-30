#!/usr/bin/env python3
"""
SIMULATION — end-to-end simulated engagement (Kali Fleet: OMEGA).

This is a REAL RUN OF REAL CODE on SYNTHETIC targets: the Hermes
adapter (sim transport), the decision gate (the Equation), the God
Router, and the Ghildra Forge all execute their production code paths.
The scenario — a synthetic own-gear lab host, its listener census, its
log — is invented for the simulation and labeled as such everywhere it
surfaces. Nothing here touches a real target, a real network, or a
real connector. The fleet actions run in kali_bot DRY-RUN mode, as
they do by default everywhere in this project.

Scenario (synthetic): the owner's lab bench host reports an unknown
listener in its (simulated) posture read and a log line about an
unexplained file. The flow:
  1. scout profile proposes listening_ports  -> gate -> dry-run action
  2. auditor profile proposes log_triage     -> gate -> dry-run action
  3. a finding (unexplained process, secret-shaped string, provenance
     unproven) goes to the Equation -> the LAW disposes (ESCALATE)
  4. the router resolves three capabilities (one LIVE route, one
     KEY-PENDING block, one approval-gated hold) — routing only,
     nothing executes
  5. the engagement transcript is forged into a skill; unverified it
     lands in QUARANTINE; verified by Ghildra it enters the book

Artifacts: sim/transcript.jsonl (one event per line, replayable — the
dashboard's demo mode replays exactly this file) + sim/SUMMARY.md.
Both are regenerated on every run; the skill book append is the only
side effect, and it is the forge's real append-only path.

Run:  python3 sim/run_sim.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

os.environ.setdefault("FLEET_AUDIT_LOG", os.path.join(HERE, "sim-audit.jsonl"))

import decision_gate  # noqa: E402
import forge  # noqa: E402
import god_router  # noqa: E402
import hermes_adapter  # noqa: E402

EVENTS = []


def emit(kind, **fields):
    ev = {"sim": True, "kind": kind, **fields}
    EVENTS.append(ev)
    print(f"[{kind}] {json.dumps(fields)[:220]}")


def main():
    emit("scenario",
         label="SIMULATION — synthetic own-gear lab host; real code paths, synthetic target",
         host="lab-bench-01 (synthetic)", engagement="sim-engagement-0001")

    # 1-2. Hermes profiles propose; the gate disposes; actions dry-run.
    transcript = []
    for profile, action, args in (
            ("scout", "listening_ports", {}),
            ("auditor", "log_triage", {"path": "sim-synthetic.log"})):
        inv = hermes_adapter.build_invocation(profile, action, args)
        emit("invocation", **inv)
        result = hermes_adapter.dispatch(inv)
        emit("action_result", action=action, mode=result.get("mode"),
             ok=result.get("ok"), would_run=result.get("would_run"))
        transcript.append({"tool": action, "profile": profile,
                           "mode": result.get("mode"),
                           "result": "dry-run plan recorded"})

    # 3. The finding: the Equation + the law dispose.
    verdict = decision_gate.decide(
        decision_gate.RAGA_QUESTIONS,
        state=("simulated finding: unexplained process holding a port; "
               "a secret-shaped string in the synthetic log; no record "
               "of provenance"),
        finding={"kind": "secret_leak", "provenance_proven": False,
                 "severity": "watch"})
    emit("gate_verdict", disposition=verdict["disposition"],
         driver=verdict["driver"], reasons=verdict["reasons"],
         forced=verdict["forced"], backend=verdict["backend"])

    # 4. Router: propose -> score -> dispose (routing only).
    for cap in ("read-email", "decide-jev", "charge-card"):
        r = god_router.route(cap, check_approval=False)
        emit("route", capability=cap, decision=r["decision"],
             connector=r["connector"], scoring_source=r["scoring_source"],
             reason=r["reason"])

    # 5. Forge: transcript -> quarantined skill -> verified -> book.
    skill = forge.forge_skill(
        "Synthetic Loopback Census + Log Sweep",
        transcript, learned_from="sim-engagement-0001",
        source="sim/transcript.jsonl (SIMULATION)")
    qpath = forge.file_skill(skill, book_dir=os.path.join(HERE, "skills"))
    emit("forge_quarantine", skill=skill["name"], state=skill["state"],
         filed=os.path.basename(qpath))
    skill = forge.verify(skill, verified_by="Ghildra (Skill Forge overseer)")
    bpath = forge.file_skill(skill, book_dir=os.path.join(HERE, "skills"))
    emit("forge_verified", skill=skill["name"], state=skill["state"],
         verified_by=skill["verified_by"], filed=os.path.basename(bpath))

    with open(os.path.join(HERE, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for ev in EVENTS:
            f.write(json.dumps(ev) + "\n")
    with open(os.path.join(HERE, "SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("# SIMULATION summary — sim-engagement-0001\n\n"
                "**SIMULATION: a real run of the project's real code paths "
                "(Hermes adapter, decision gate, God Router, Ghildra Forge) "
                "against a synthetic own-gear target. No real target, "
                "network, or connector was touched. Fleet actions ran in "
                "dry-run mode.**\n\n"
                f"Events: {len(EVENTS)} (see transcript.jsonl)\n"
                f"Gate verdict on the synthetic finding: "
                f"{verdict['disposition']} (driver: {verdict['driver']}) — "
                f"the law disposed, as designed.\n"
                f"Skill forged + verified: {skill['name']} "
                f"(transcript sha256 {skill['transcript_sha256'][:16]}…)\n")
    print(f"\nSIMULATION complete: {len(EVENTS)} events -> sim/transcript.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
