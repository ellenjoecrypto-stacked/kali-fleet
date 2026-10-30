#!/usr/bin/env python3
"""
Zero-Trust Verification Layer tests — stdlib only.

Run:  ~/workspace/venv/bin/python test_verify.py
The centerpiece is the Demotion Rule (proven outranks claimed): a registry entry
that CLAIMS a state its probe cannot prove gets demoted in the
verdict table. Also: the module clauses (gate negative, forge chain,
router no-fake-success, heretic honesty) and the connectors.json
verification fields. Temp dirs only. Exit 0 = all green.
"""

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

TMP = tempfile.mkdtemp(prefix="omega-verify-test-")
os.environ["FLEET_AUDIT_LOG"] = os.path.join(TMP, "audit.jsonl")
os.environ["OMEGA_GODCHECK_CACHE"] = os.path.join(TMP, "godcache.json")
os.environ["OMEGA_HERETIC_ARTIFACTS"] = os.path.join(TMP, "none")

FAILURES = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def main():
    import connector_registry
    import god_check
    import verify_all

    data = connector_registry.load()
    check("every registry entry carries a verification clause",
          all("verification" in c and c["verification"].get("clause")
              and c["verification"].get("check") for c in data["connectors"]))
    import decision_gate, forge, god_router, heretic_slot, hermes_adapter
    check("every new module carries its VERIFICATION clause",
          all(hasattr(m, "VERIFICATION") for m in
              (decision_gate, forge, god_router, heretic_slot,
               hermes_adapter, god_check, connector_registry)))

    # ---- The Demotion Rule: proven outranks claimed ------------------------------
    # Deliberately FALSE claims: OpenRouter 'LIVE', GitHub 'OUT'.
    probes = god_check.probe_all(use_cache=False)
    by_name = {c["name"]: c for c in data["connectors"]}
    liar = dict(by_name["OpenRouter"], state="LIVE")
    row = god_check.classify(liar, probes, env={})
    verdict, _ = verify_all.verdict_for_row(row)
    check("LAW 5: false LIVE claim for an unfueled connector is DEMOTED",
          row["checked_state"] == "KEY-PENDING" and verdict == "UNEXPLAINED",
          f"checked={row['checked_state']} verdict={verdict}")
    inflated = dict(by_name["GitHub"], state="OUT")
    row = god_check.classify(inflated, probes)
    verdict, _ = verify_all.verdict_for_row(row)
    check("LAW 5: probe proof outranks a false non-LIVE claim too",
          row["checked_state"] == "LIVE" and verdict == "VERIFIED")

    # ---- module clauses ----------------------------------------------
    v, why = verify_all.clause_gate_negative()
    check("gate clause: negative tests prove law + fail-closed", v == "VERIFIED", why)
    v, why = verify_all.clause_forge_chain()
    check("forge clause: provenance chain validates, tamper fails", v == "VERIFIED", why)
    v, why = verify_all.clause_router_no_fake_success()
    check("router clause: no fake success on unfueled capability", v == "VERIFIED", why)
    v, why = verify_all.clause_heretic_honesty()
    check("heretic clause: empty slot proves its negative", v == "VERIFIED", why)

    out = verify_all.run_all()
    check("verify_all emits the sentinel vocabulary",
          set(out["counts"]) <= {"VERIFIED", "UNEXPLAINED", "FAILED"}
          and out["counts"].get("VERIFIED", 0) >= 10,
          str(out["counts"]))
    failed_rows = [r for r in out["rows"] if r["verdict"] == "FAILED"]
    check("verify_all: FAILED only ever comes from probe evidence "
          "(a CHECK-FAILED row), never from a claim",
          all(r.get("checked_state") == "CHECK-FAILED" for r in failed_rows),
          str([(r["item"], r.get("checked_state")) for r in failed_rows]))

    print(f"\n{len(FAILURES)} failure(s)" if FAILURES else "\nALL GREEN")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
