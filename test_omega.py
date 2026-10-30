#!/usr/bin/env python3
"""
Kali Fleet: OMEGA tests — stdlib only, no keys required.

Run:  ~/workspace/venv/bin/python test_omega.py
Covers: connector registry (incl. the soul-content law), the decision
gate / the Equation (law over model, fail-closed), the God Router
(live route, unfueled block, approval gate, quantum scoring citation),
the Hermes adapter (profile scopes, fail-closed gate client), the
Ghildra Forge (provenance, quarantine, append-only), the Heretic slot
(config shape, EMPTY/PREP honesty), and god_check classification from
REAL connector probes. Writes go to temp dirs only.
Exit code 0 = all green.
"""

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

TMP = tempfile.mkdtemp(prefix="omega-test-")
os.environ["FLEET_AUDIT_LOG"] = os.path.join(TMP, "audit.jsonl")
os.environ["FLEET_APPROVAL_FILE"] = os.path.join(TMP, "live-approval.json")
os.environ["OMEGA_GODCHECK_CACHE"] = os.path.join(TMP, "godcache.json")
os.environ["OMEGA_HERETIC_ARTIFACTS"] = os.path.join(TMP, "no-artifacts")
os.environ.pop("FLEET_STOP", None)
os.environ.pop("OMEGA_QUANTUM_RESULTS", None)

FAILURES = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def calm_transport(questions, state):
    import decision_gate as dg
    out = {}
    for name, spec in questions.items():
        if spec["type"] == "noul":
            out[name] = dg.noul_answer(0.05)
        elif spec["type"] == "score":
            probs = {o: 0.01 for o in spec["options"]}
            probs[spec["options"][0]] = 0.97
            out[name] = dg.score_answer(spec["options"], probs)
        else:
            probs = {o: 0.01 for o in spec["options"]}
            probs[spec["options"][0]] = 0.97
            out[name] = dg.choice_answer(spec["options"], probs)
    return out


def main():
    import approval
    import connector_registry
    import decision_gate as dg
    import forge
    import god_check
    import god_router
    import heretic_slot
    import hermes_adapter

    # ---------------------------------------------------------- registry
    data = connector_registry.load()
    check("registry loads + validates", len(data["connectors"]) >= 40,
          f"got {len(data['connectors'])}")
    by_name = {c["name"]: c for c in data["connectors"]}
    check("Notion is LIVE", by_name["Notion"]["state"] == "LIVE")
    check("Supabase is WIRED-NOT-FUELED", by_name["Supabase"]["state"] == "WIRED-NOT-FUELED")
    check("GitHub LIVE with 403 creation limit on record",
          by_name["GitHub"]["state"] == "LIVE" and "403" in by_name["GitHub"]["note"])
    assets = {a["member"]: a for a in data["identity_assets"]}
    check("identity assets are name + status + path ONLY (15)",
          len(assets) == 15 and all(set(a) <= {"member", "status", "pointer"}
                                    for a in assets.values()),
          str([set(a) for a in assets.values()][:3]))
    check("no separate Qrow/Souviern assets — forms of Ellen Joe / Senku",
          "Qrow" not in assets and "Souviern" not in assets
          and "Ellen Joe" in assets and "Senku" in assets)
    check("Vaelor seated as a sibling in his own right, contract authored",
          assets["Vaelor"]["status"].startswith("AUTHORED-2026-10-30"))
    for field in ("text", "content", "contents", "role"):
        bad = json.loads(json.dumps(data))
        bad["identity_assets"].append({"member": "Smuggler",
                                       "status": "exists", "pointer": None,
                                       field: "dummy contract text"})
        badpath = os.path.join(TMP, f"bad-{field}.json")
        with open(badpath, "w") as f:
            json.dump(bad, f)
        try:
            connector_registry.load(badpath)
            check(f"identity field {field!r} rejected at load", False,
                  "load() accepted it")
        except connector_registry.RegistryError:
            check(f"identity field {field!r} rejected at load", True)
    dup = json.loads(json.dumps(data))
    dup["connectors"].append(dict(dup["connectors"][0]))
    duppath = os.path.join(TMP, "dup.json")
    with open(duppath, "w") as f:
        json.dump(dup, f)
    try:
        connector_registry.load(duppath)
        check("duplicate connector names rejected", False, "load() accepted")
    except connector_registry.RegistryError:
        check("duplicate connector names rejected", True)

    # -------------------------------------------------------------- gate
    check("bands: act/review/escalate thresholds",
          dg.band(0.9) == "act" and dg.band(0.7) == "review" and dg.band(0.3) == "escalate")
    leak = dg.decide(dg.RAGA_QUESTIONS, state="routine empire file movement",
                     finding={"kind": "secret_leak", "provenance_proven": False},
                     transport=calm_transport)
    check("LAW overrides a calm model on a secret leak",
          leak["disposition"] == "ESCALATE" and leak["driver"] == "law")
    check("Law 2 forces the key-rotation flag", leak["forced"].get("key_rotation") is True)
    crit = dg.decide(dg.RAGA_QUESTIONS, state="routine",
                     finding={"severity": "critical"}, transport=calm_transport)
    check("Law 1: critical severity escalates despite calm model",
          crit["disposition"] == "ESCALATE" and crit["driver"] == "law")
    crit_upper = dg.decide(
        dg.RAGA_QUESTIONS, state="routine",
        finding={"severity": "CRITICAL", "kind": "SECRET_LEAK",
                 "provenance_proven": False}, transport=calm_transport)
    check("SUK-D5 regression: UPPERCASE CRITICAL + SECRET_LEAK hits Laws 1-2",
          crit_upper["disposition"] == "ESCALATE"
          and crit_upper["driver"] == "law"
          and crit_upper["forced"].get("key_rotation") is True)
    calm = dg.decide(dg.RAGA_QUESTIONS, state="routine empire file movement",
                     finding={"kind": "agent_action"}, transport=calm_transport)
    check("calm + no law trigger -> model band disposes (ALLOW)",
          calm["disposition"] == "ALLOW" and calm["driver"] == "model")

    def boom(questions, state):
        raise RuntimeError("transport down")
    dead = dg.decide(dg.RAGA_QUESTIONS, state="x", transport=boom)
    check("gate FAILS CLOSED on transport error",
          dead["disposition"] == "ESCALATE" and dead["driver"] == "fail-closed")
    malformed = dg.decide(dg.RAGA_QUESTIONS, state="x",
                          transport=lambda q, s: {"verdict": {"nope": 1}})
    check("gate FAILS CLOSED on malformed answers",
          malformed["disposition"] == "ESCALATE" and malformed["driver"] == "fail-closed")
    ladder = dg.decide(dg.RAGA_QUESTIONS, state="routine empire work, registered lane")
    check("default ladder falls through unfueled rungs to heuristic",
          ladder["backend"] == "heuristic" and len(ladder["fell_through"]) >= 4)

    # ------------------------------------------------------------- router
    r = god_router.route("read-email", check_approval=False, checked={})
    check("live route resolves (read-email -> Gmail)",
          r["decision"] == "ROUTE" and r["connector"] == "Gmail")
    check("classical scoring labeled", r["scoring_source"] == "classical")
    r = god_router.route("decide-jev", check_approval=False, checked={})
    check("unfueled route BLOCKS (no fake success)",
          r["decision"] == "BLOCKED" and r["state"] == "WIRED-NOT-FUELED")
    check("block names the exact unblock", "OPENROUTER_API_KEY" in (r["unblock"] or ""))
    r = god_router.route("charge-card", check_approval=False, checked={})
    check("gated route requires approval",
          r["decision"] == "REQUIRES_APPROVAL" and r["gate"] == "approval")
    approval.mint("charge-card", "Stripe", minutes=5, issued_by="test")
    r = god_router.route("charge-card", check_approval=True, checked={})
    check("valid approval token satisfies the gate",
          r["decision"] == "ROUTE" and "satisfied" in r["reason"])
    r = god_router.route("charge-card", check_approval=True, checked={})
    check("the same token again -> REPLAY refused (single-use)",
          r["decision"] == "REQUIRES_APPROVAL")
    approval.revoke()
    r = god_router.route("charge-card", check_approval=True, checked={})
    check("revoked token -> back to REQUIRES_APPROVAL",
          r["decision"] == "REQUIRES_APPROVAL")
    r = god_router.route("telepathy", check_approval=False, checked={})
    check("unknown capability BLOCKS", r["decision"] == "BLOCKED")
    qdata = {"connectors": [
        {"name": "Alpha", "capabilities": ["read-x"], "transport": "api",
         "state": "LIVE", "gate": "none", "unblock": None,
         "verification": {"clause": "t", "check": "t"}},
        {"name": "Beta", "capabilities": ["read-x"], "transport": "api",
         "state": "LIVE", "gate": "none", "unblock": None,
         "verification": {"clause": "t", "check": "t"}}],
        "identity_assets": []}
    qpath = os.path.join(TMP, "qresults.json")
    with open(qpath, "w") as f:
        json.dump({"routes": {"read-x": "Beta"}}, f)
    os.environ["OMEGA_QUANTUM_RESULTS"] = qpath
    r = god_router.route("read-x", data=qdata, check_approval=False,
                         checked={})
    check("quantum-scored preference honored among LIVE candidates",
          r["connector"] == "Beta" and "quantum" in r["scoring_source"])
    with open(qpath, "w") as f:
        json.dump({"chosen_route": "Alpha"}, f)
    r = god_router.route("read-x", data=qdata, check_approval=False,
                         checked={})
    check("quantum worker's chosen_route shape also honored",
          r["connector"] == "Alpha" and "quantum" in r["scoring_source"])
    os.environ.pop("OMEGA_QUANTUM_RESULTS", None)
    r = god_router.route("read-social", check_approval=False, checked={})
    check("no results file -> classical fallback",
          r["scoring_source"] == "classical")

    # ------------------------------------------------------------- hermes
    try:
        hermes_adapter.build_invocation("scout", "nmap_scan")
        check("scout scope refuses nmap_scan", False, "no refusal raised")
    except hermes_adapter.ScopeRefusal:
        check("scout scope refuses nmap_scan", True)
    inv = hermes_adapter.build_invocation("operator", "sysinfo")
    check("invocation contract is data with a dry-run default",
          inv["mode"] == "dry-run" and inv["profile"] == "operator")
    client = hermes_adapter.GateClient(transport=boom)
    v = client.decide(dg.RAGA_QUESTIONS, state="x")
    check("Hermes gate client FAILS CLOSED (no raise, ESCALATE)",
          v["disposition"] == "ESCALATE" and v["driver"] == "fail-closed")
    res = hermes_adapter.dispatch(
        hermes_adapter.build_invocation("scout", "listening_ports"))
    check("scout dispatch dry-runs through the composed gates",
          res.get("ok") is True and res.get("mode") == "dry-run")

    # -------------------------------------------------------------- forge
    book_dir = os.path.join(TMP, "skills")
    tr = [{"tool": "listening_ports", "result": "dry-run"},
          {"tool": "log_triage", "result": "clean"}]
    try:
        forge.forge_skill("Bad", tr, learned_from="", source="x")
        check("incomplete provenance rejected", False, "no error raised")
    except forge.ForgeError:
        check("incomplete provenance rejected", True)
    s1 = forge.forge_skill("Listener Census", tr, learned_from="eng-1", source="t.jsonl")
    check("skills are born QUARANTINED", s1["state"] == "quarantined"
          and len(s1["transcript_sha256"]) == 64)
    p = forge.file_skill(s1, book_dir=book_dir)
    check("quarantined skill files to QUARANTINE.md only",
          os.path.basename(p) == "QUARANTINE.md"
          and not os.path.exists(os.path.join(book_dir, "fleet-skills.md")))
    try:
        forge.verify(s1, verified_by="")
        check("verify requires a named verifier", False, "no error raised")
    except forge.ForgeError:
        check("verify requires a named verifier", True)
    s1v = forge.verify(s1, verified_by="Ghildra")
    p = forge.file_skill(s1v, book_dir=book_dir)
    book_before = open(p).read()
    check("verified skill enters the book with provenance",
          "Listener Census" in book_before and "Ghildra" in book_before)
    try:
        forge.file_skill(s1v, book_dir=book_dir)
        check("duplicate filing rejected (append-only)", False, "no error raised")
    except forge.ForgeError:
        check("duplicate filing rejected (append-only)", True)
    s2 = forge.verify(forge.forge_skill("Log Sweep", tr, learned_from="eng-2",
                                        source="t.jsonl"), verified_by="Ghildra")
    forge.file_skill(s2, book_dir=book_dir)
    check("book is append-only (old bytes are a strict prefix)",
          open(p).read().startswith(book_before))
    try:
        forge.verify(s1v, verified_by="Ghildra")
        check("no re-verify / no state rewrite", False, "no error raised")
    except forge.ForgeError:
        check("no re-verify / no state rewrite", True)

    # ------------------------------------------------------------ heretic
    cfg = heretic_slot.smoke_config()
    names = [s["score_name"] for s in cfg["scorers"]]
    check("smoke config parses (n_trials=3, Refusals + KL divergence)",
          cfg["n_trials"] == 3 and "Refusals" in names and "KL divergence" in names)
    st = heretic_slot.status()
    check("slot state is PREP with zero artifacts (honest EMPTY chair)",
          st["state"] == "PREP" and st["artifacts"] == [])
    try:
        heretic_slot.answer({}, "")
        check("slot never fabricates an inference", False, "answer() returned")
    except heretic_slot.SlotEmpty:
        check("slot never fabricates an inference", True)

    # ----------------------------------------------------------- god_check
    probes = god_check.probe_all(use_cache=False)
    gh = god_check.classify(by_name["GitHub"], probes)
    check("god_check: GitHub verified LIVE by its real status probe",
          gh["checked_state"] == "LIVE", gh["detail"])
    orow = god_check.classify(by_name["OpenRouter"], probes, env={})
    check("god_check: OpenRouter is KEY-PENDING without its key",
          orow["checked_state"] == "KEY-PENDING"
          and "OPENROUTER_API_KEY" in (orow["missing_input"] or ""))
    door = god_check.classify(by_name["PC door (SSH to DESKTOP-0RGKS6P)"], probes)
    check("god_check: PC door is DOOR-PENDING (not upgraded on transport facts)",
          door["checked_state"] == "DOOR-PENDING")

    print(f"\n{len(FAILURES)} failure(s)" if FAILURES else "\nALL GREEN")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
