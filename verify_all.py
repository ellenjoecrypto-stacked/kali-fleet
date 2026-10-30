#!/usr/bin/env python3
"""
Verify All — the Zero-Trust Verification Layer, executed
(Kali Fleet: OMEGA).

Doctrine (Raga Sentinel, on record): every input, alert, and artifact
starts **UNVERIFIED HOSTILE**. Provenance must be proven per item or
the item is named **UNEXPLAINED**. Triage is read-only. EXPLAINED_ALL
→ silent; UNEXPLAINED / CRITICAL → loud.

Clauses (NetworkChuck's verification habits, from the playbook skill —
prove it on screen, check the actual output/banner, never trust the
tutorial's word, break-it-then-fix-it checks, sponsor claims are
claims, research verifies against primary sources):

  * A connector's claimed state is a CLAIM. god_check's probe is the
    proof. **Proven outranks claimed (the Demotion Rule of this layer):** a
    registry entry claiming LIVE whose probe cannot prove it is
    DEMOTED in the verdict table, whatever the registry says.
  * A forged skill's provenance chain must validate, or the skill is
    UNEXPLAINED.
  * The gate must prove its negative: fed a calm model and a secret
    leak, it must still escalate (the law); fed a dead transport, it
    must fail closed.
  * The dashboard's displayed checked_at must trace to a god_check
    run — displayed state traces to a checked artifact, or it is
    decoration.

Verdicts, in the sentinel's vocabulary: VERIFIED / UNEXPLAINED /
FAILED. This tool is read-only: it runs probes, negative tests
against temp dirs, and file reads. It changes nothing it verifies.

Run:  python3 verify_all.py [--json]
"""

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

os.environ.setdefault("FLEET_AUDIT_LOG",
                      os.path.join(tempfile.mkdtemp(prefix="verify-"),
                                   "audit.jsonl"))

import connector_registry
import decision_gate
import forge
import god_check
import god_router
import heretic_slot


def verdict_for_row(row):
    """Connector verdicts from the checked row. Proven > claimed."""
    cs = row["checked_state"]
    if cs == "LIVE":
        return "VERIFIED", "probe proved the claimed LIVE state on this machine"
    if cs == "CHECK-FAILED":
        return "FAILED", f"claimed {row['registry_state']} but the probe did not confirm: {row['detail']}"
    if cs in ("KEY-PENDING", "DOOR-PENDING"):
        return "UNEXPLAINED", f"unproven here — missing input: {row['missing_input']}"
    return "UNEXPLAINED", "claimed by the registry; no probe exists on this VM"


def clause_gate_negative():
    """Break-it check: calm model + secret leak must still ESCALATE
    (driver: law); a dead transport must fail closed."""
    def calm(questions, state):
        out = {}
        for name, spec in questions.items():
            if spec["type"] == "noul":
                out[name] = decision_gate.noul_answer(0.05)
            elif spec["type"] == "score":
                probs = {o: 0.01 for o in spec["options"]}
                probs[spec["options"][0]] = 0.97
                out[name] = decision_gate.score_answer(spec["options"], probs)
            else:
                probs = {o: 0.01 for o in spec["options"]}
                probs[spec["options"][0]] = 0.97
                out[name] = decision_gate.choice_answer(spec["options"], probs)
        return out
    leak = decision_gate.decide(
        decision_gate.RAGA_QUESTIONS, state="routine",
        finding={"kind": "secret_leak", "provenance_proven": False},
        transport=calm)
    if not (leak["disposition"] == "ESCALATE" and leak["driver"] == "law"):
        return "FAILED", f"calm model talked the gate down: {leak['disposition']}"
    def boom(q, s):
        raise RuntimeError("down")
    dead = decision_gate.decide(decision_gate.RAGA_QUESTIONS, state="x",
                                transport=boom)
    if not (dead["disposition"] == "ESCALATE" and dead["driver"] == "fail-closed"):
        return "FAILED", "dead transport did not fail closed"
    return "VERIFIED", "law overrides calm model; dead transport fails closed"


def clause_forge_chain():
    """Provenance chain: a forged skill validates; a tampered one
    (verifier stripped) does not."""
    tr = [{"tool": "listening_ports", "result": "dry-run"}]
    s = forge.forge_skill("Chain Check", tr, learned_from="verify-all",
                          source="verify_all.py (clause run)")
    v = forge.verify(s, verified_by="Ghildra")
    required = ("name", "learned_from", "source", "transcript_sha256",
                "verified_by", "state")
    if any(not v.get(k) for k in required) or v["state"] != "verified":
        return "FAILED", "freshly verified skill failed chain validation"
    tampered = dict(v, verified_by=None)
    if all(tampered.get(k) for k in required):
        return "FAILED", "tampered chain validated — provenance is decorative"
    return "VERIFIED", "chain validates; verifier-stripped copy does not"


def clause_router_no_fake_success():
    r = god_router.route("decide-jev", check_approval=False)
    if r["decision"] != "BLOCKED":
        return "FAILED", f"unfueled capability routed: {r['decision']}"
    return "VERIFIED", "unfueled capability BLOCKED with its unblock named"


def clause_heretic_honesty():
    st = heretic_slot.status()
    if st["artifacts"]:
        return "UNEXPLAINED", "run artifacts exist — the trial gate must dispose before any claim"
    try:
        heretic_slot.answer({}, "")
        return "FAILED", "empty slot produced an answer"
    except heretic_slot.SlotEmpty:
        return "VERIFIED", f"slot proves its negative: state {st['state']}, answer() refuses"


def clause_fleet_dispatch():
    """Unit clause for fleet.py (war-room fix list §7 item 5 — the
    quickstart CLI itself was verified by nothing). Exercises main()'s
    dispatch with _run/serve stubbed, so the check is read-only: every
    subcommand must route to its module in order, serve must wire the
    console port, return codes must propagate, and an unknown command
    must exit 2 having run nothing."""
    import fleet
    calls, served = [], []
    real_run, real_serve = fleet._run, fleet.serve
    def fake_run(*args):
        calls.append(args)
        return 0
    def fake_serve(port=8765):
        served.append(port)
        return 0
    fleet._run, fleet.serve = fake_run, fake_serve
    try:
        if fleet.main(["fleet.py", "up"]) != 0 or calls != [
                ("build_dashboard.py",), ("verify_all.py",), ("sim/run_sim.py",)]:
            return "FAILED", f"up dispatch wrong: rc/calls={calls}"
        calls.clear()
        if fleet.main(["fleet.py", "check"]) != 0 or calls != [("god_check.py",)]:
            return "FAILED", f"check dispatch wrong: rc/calls={calls}"
        calls.clear()
        if fleet.main(["fleet.py", "sim"]) != 0 or calls != [("sim/run_sim.py",)]:
            return "FAILED", f"sim dispatch wrong: rc/calls={calls}"
        calls.clear()
        if fleet.main(["fleet.py", "serve", "8765"]) != 0 or served != [8765] or calls:
            return "FAILED", f"serve dispatch wrong: served={served} calls={calls}"
        calls.clear()
        if fleet.main(["fleet.py", "bogus"]) != 2 or calls or served != [8765]:
            return "FAILED", f"unknown command did not exit 2 cleanly: calls={calls}"
    finally:
        fleet._run, fleet.serve = real_run, real_serve
    return "VERIFIED", "up/check/sim route to their modules in order; serve wires the port; unknown command exits 2 running nothing"


def clause_dashboard_trace(report):
    path = os.path.join(HERE, "dashboard", "index.html")
    if not os.path.exists(path):
        return "UNEXPLAINED", "dashboard not built — run build_dashboard.py"
    text = open(path, encoding="utf-8").read()
    if report["checked_at"][:13] in text:  # same hour as this check run
        return "VERIFIED", "dashboard embeds a god_check table from this check window"
    return "UNEXPLAINED", "dashboard's checked_at does not trace to a current god_check run — rebuild it"


def identity_rows():
    """Pointer-existence probe for the identity plane (war-room §6a:
    contract existence was asserted, never probed). A pointer is a
    path under ~/workspace; VERIFIED = the file exists on this
    machine. Contents are NEVER read — existence only, per the
    soul-contract law."""
    rows = []
    for a in connector_registry.identity_assets():
        ptr = a.get("pointer")
        if not ptr:
            rows.append({"item": f"identity:{a['member']}",
                         "verdict": "UNEXPLAINED",
                         "detail": "no local pointer on record — existence unproven",
                         "checked_state": "pointer-probe"})
            continue
        exists = os.path.isfile(os.path.join(
            os.path.expanduser("~"), "workspace", ptr))
        rows.append({"item": f"identity:{a['member']}",
                     "verdict": "VERIFIED" if exists else "UNEXPLAINED",
                     "detail": (f"pointer target {'exists' if exists else 'NOT FOUND'} "
                                "on this machine (existence probed; contents never read)"),
                     "checked_state": "pointer-probe"})
    return rows


def run_all():
    report = god_check.check(use_cache=True)
    rows = []
    for r in report["rows"]:
        v, why = verdict_for_row(r)
        rows.append({"item": f"connector:{r['name']}", "verdict": v,
                     "detail": why, "checked_state": r["checked_state"]})
    rows.extend(identity_rows())
    for item, fn in (("module:decision_gate", clause_gate_negative),
                     ("module:forge", clause_forge_chain),
                     ("module:god_router", clause_router_no_fake_success),
                     ("module:heretic_slot", clause_heretic_honesty),
                     ("module:fleet", clause_fleet_dispatch)):
        v, why = fn()
        rows.append({"item": item, "verdict": v, "detail": why,
                     "checked_state": "clause-run"})
    v, why = clause_dashboard_trace(report)
    rows.append({"item": "artifact:dashboard", "verdict": v, "detail": why,
                 "checked_state": "clause-run"})
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    return {"checked_at": report["checked_at"], "rows": rows, "counts": counts,
            "doctrine": "UNVERIFIED HOSTILE until proven; proven outranks claimed"}


if __name__ == "__main__":
    out = run_all()
    if "--json" in sys.argv:
        print(json.dumps(out, indent=2))
    else:
        print(f"ZERO-TRUST VERIFICATION — {out['checked_at']}")
        for r in out["rows"]:
            print(f"{r['verdict']:12} {r['item']:44} {r['detail']}")
        print(f"\ncounts: {out['counts']}")
        print("EXPLAINED_ALL -> silence. Anything UNEXPLAINED or FAILED above is LOUD by doctrine.")
