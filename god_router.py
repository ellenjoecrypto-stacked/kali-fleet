#!/usr/bin/env python3
"""
God Router — one console, every connector, disposed by THE EQUATION
(Kali Fleet: OMEGA — the Ultimate Connector God System).

GOD MODE = total visibility + one-console routing. It is NOT a gate
removal: **God Mode does not bypass the Boss's gates — spend, send,
secrets, and production actions still stop at their approval gates.
The router shows the gates; it does not remove them.**

How a route is decided:
  1. PROPOSE — capability matching over connector_registry. Capability
     names are normalized (strip + lower) on BOTH sides before
     matching, so a connector registering `Send-Email` cannot sail
     past the gated-capability law (war-room E29).
  2. CHECK — the registry's claimed state is UNVERIFIED until
     god_check proves it. route() overlays god_check's checked states
     (5-minute probe cache): a connector demoted to KEY-PENDING routes
     as WIRED-NOT-FUELED, CHECK-FAILED / DOOR-PENDING route as
     BLOCKED. Claimed state alone never routes (war-room M9/E27).
  3. SCORE — classical scoring is the effective-state order. If the
     quantum worker's results file (quantum/results.json — QAOA on
     Qiskit Aer) names a preference among the LIVE, UNGATED
     candidates, it may reorder them and is cited per decision as
     "quantum-simulator scored (Aer)". Scoring never promotes an
     unfueled connector and never touches a gate.
  4. DISPOSE — the Equation (decision_gate.py; home:
     empire/work/decision-layer/): the Boss's standing law in route
     form —
       - No candidate             -> BLOCKED (nothing serves it).
       - No LIVE candidate        -> BLOCKED with the best candidate's
         exact unblocking step. Never a fake success.
       - MOST RESTRICTIVE GATE WINS: if ANY live candidate for the
         capability is gated, the strictest gate applies — an ungated
         duplicate listed first cannot shadow an approval or
         boss-hands route (war-room E08/E10).
       - 'approval' gate -> REQUIRES_APPROVAL unless a valid signed
         single-use live-approval token (approval.py; minted only by
         approve_live.py on the Boss's per-run word) satisfies it for
         THAT gated connector. A successful route consumes the token.
       - 'boss-hands' / 'vault' gates -> BLOCKED for the router: no
         token in this system can stand in for the Boss's hands or a
         vault deposit.
  5. Every decision is appended to the fleet audit log (action
     GOD_ROUTE) with its scoring_source — the dashboard renders it.

Stdlib only. No network of its own (god_check's probes are the
connectors' own CLI status surfaces). Routing never executes the
capability; it returns a decision.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import approval
import connector_registry
import kali_bot

# Capabilities that always stop at a gate, whatever the connector says.
GATED_CAPABILITIES = {
    "send-email", "send-payment", "charge-card", "trade-live",
    "deploy-site", "pc-access", "hermes-access", "abliterate-model",
    "run-company", "create-repo", "post-social",
}

_GATE_RANK = {"none": 0, "approval": 1, "boss-hands": 2, "vault": 2}
_STATE_RANK = {s: i for i, s in enumerate(
    ("LIVE", "WIRED-NOT-FUELED", "PAPER", "BLOCKED", "EMPTY",
     "UNVERIFIED", "NAMED-IN-RECORD", "OUT"))}

# ------------------------------------------------------------- god_check

def _checked_states(checked):
    """{connector name: checked_state} from god_check (cached probes).
    Injectable for tests; an unavailable probe layer yields {} and the
    decision is marked so — registry claims then stand as UNVERIFIED
    claims, and the six probe-less LIVE claims were already demoted
    in the registry itself."""
    if checked is not None:
        return checked
    try:
        import god_check
        report = god_check.check()
        return {r["name"]: r["checked_state"] for r in report["rows"]}
    except Exception:
        return {}


def _effective_state(entry, checked):
    """Registry claim, demoted by probe evidence where a probe exists.
    Proven > claimed (the Demotion Rule)."""
    row = checked.get(entry["name"])
    if row == "LIVE":
        return "LIVE"
    if row == "KEY-PENDING":
        return "WIRED-NOT-FUELED"
    if row in ("CHECK-FAILED", "DOOR-PENDING"):
        return "BLOCKED"
    return entry["state"]  # REGISTRY pass-through / no probe: claim as-is

# ------------------------------------------------------- quantum scoring

QUANTUM_RESULTS = os.path.join(HERE, "quantum", "results.json")
QUANTUM_CITATION = "quantum-simulator scored (Aer)"


def quantum_choice(capability, candidate_names):
    """(connector_name, citation) if quantum/results.json names a
    preferred connector for this capability among the candidates;
    else (None, None). Accepts {"routes": {cap: name}},
    {"choices": {cap: name}}, {"scores": {cap: {name: score}}}, and
    the quantum worker's own shape {"chosen_route": name} (a single
    global optimum — applied only when it names a candidate)."""
    path = os.environ.get("OMEGA_QUANTUM_RESULTS") or QUANTUM_RESULTS
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None, None
    for key in ("routes", "choices"):
        pick = (data.get(key) or {}).get(capability)
        if pick in candidate_names:
            return pick, QUANTUM_CITATION
    scores = (data.get("scores") or {}).get(capability) or {}
    ranked = [n for n in candidate_names if n in scores]
    if ranked:
        return max(ranked, key=lambda n: scores[n]), QUANTUM_CITATION
    single = data.get("chosen_route")
    if single in candidate_names:
        return single, QUANTUM_CITATION
    return None, None


# ------------------------------------------------------------------ route

def route(capability, data=None, check_approval=True, checked=None):
    """Resolve one capability request to a route decision dict:
    {capability, decision, connector, state, gate, reason, unblock,
    scoring_source, checked}. decision in ROUTE / REQUIRES_APPROVAL /
    BLOCKED. Fail-closed."""
    capability = str(capability).strip().lower()
    data = data if data is not None else connector_registry.load()
    checked_map = _checked_states(checked)
    scoring_source = "classical"

    def done(out):
        out["scoring_source"] = scoring_source
        out["checked"] = "god_check overlay" if checked_map else \
            "registry claims only (probe layer unavailable)"
        kali_bot.audit({"action": "GOD_ROUTE", **out})
        return out

    candidates = connector_registry.find_by_capability(capability, data)
    if not candidates:
        return done({"capability": capability, "decision": "BLOCKED",
                     "connector": None, "state": None, "gate": None,
                     "reason": f"no connector in the registry serves '{capability}'",
                     "unblock": "register a connector for this capability first"})

    for c in candidates:
        c["_effective"] = _effective_state(c, checked_map)
    live = [c for c in candidates if c["_effective"] == "LIVE"]
    if not live:
        best = min(candidates, key=lambda c: _STATE_RANK[c["_effective"]])
        why = (f"{best['name']} is {best['_effective']} — routing would "
               f"be a fake success")
        if best["_effective"] == "UNVERIFIED":
            why = (f"{best['name']} claims to serve '{capability}' but its "
                   f"state is UNVERIFIED — no probe on this VM proves it")
        elif best["_effective"] == "NAMED-IN-RECORD":
            why = (f"{best['name']} is NAMED-IN-RECORD — it appears in "
                   f"Marke's record and nothing more: never attempted, "
                   f"nothing probed or built on this VM")
        elif best["_effective"] != best["state"]:
            why = (f"{best['name']} claims {best['state']} but god_check "
                   f"proves {best['_effective']} — proven > claimed")
        return done({"capability": capability, "decision": "BLOCKED",
                     "connector": best["name"], "state": best["_effective"],
                     "gate": best["gate"], "reason": why,
                     "unblock": best.get("unblock")})

    # MOST RESTRICTIVE GATE WINS — scoped the way the law scopes it:
    # boss-hands/vault gates bind EVERY capability they serve; the
    # approval gate binds the GATED ACTIONS (GATED_CAPABILITIES). A
    # connector's approval gate does not double-gate its reads (Gmail
    # reads route; Gmail sends stop). But for a gated action, an
    # ungated duplicate listed first can no longer shadow the gated
    # route (war-room E08/E10).
    boss_gated = [c for c in live if c["gate"] in ("boss-hands", "vault")]
    if boss_gated:
        strictest = boss_gated[0]
        return done({"capability": capability, "decision": "BLOCKED",
                     "connector": strictest["name"], "state": "LIVE",
                     "gate": strictest["gate"],
                     "reason": (f"gate '{strictest['gate']}' on "
                                f"{strictest['name']} belongs to the Boss "
                                f"alone — the router cannot stand in for "
                                f"it (most-restrictive gate wins)"),
                     "unblock": strictest.get("unblock")
                     or "the Boss's hands / vault deposit"})
    if capability in GATED_CAPABILITIES:
        approved = [c for c in live if c["gate"] == "approval"]
        target = approved[0] if approved else live[0]
        if approved and check_approval:
            ok, why = approval.check(capability, target["name"])
            if ok:
                return done({"capability": capability, "decision": "ROUTE",
                             "connector": target["name"], "state": "LIVE",
                             "gate": "approval",
                             "reason": f"approval gate satisfied: {why}",
                             "unblock": None})
        shadowed = [c["name"] for c in live
                    if c["gate"] == "none" and c["name"] != target["name"]]
        note = (f" (ungated duplicate(s) {shadowed} do not shadow the "
                f"gate — most-restrictive wins)") if shadowed else ""
        if not approved:
            note += (" (no approval-gated connector serves this gated "
                     "capability — failing closed)")
        return done({"capability": capability,
                     "decision": "REQUIRES_APPROVAL",
                     "connector": target["name"], "state": "LIVE",
                     "gate": "approval",
                     "reason": ("connector is LIVE but this capability stops "
                                "at the approval gate — God Mode shows the "
                                "gate, it does not remove it" + note),
                     "unblock": ("Boss's per-run approval via approve_live.py "
                                 f"(tool='{capability}', "
                                 f"target='{target['name']}')")})

    # Ungated + live: classical order, quantum may reorder this tier.
    best = min(live, key=lambda c: _STATE_RANK[c["_effective"]])
    if len(live) > 1:
        pick, citation = quantum_choice(capability,
                                        [c["name"] for c in live])
        if pick:
            scoring_source = citation
            best = next(c for c in live if c["name"] == pick)
    return done({"capability": capability, "decision": "ROUTE",
                 "connector": best["name"], "state": "LIVE", "gate": "none",
                 "reason": "LIVE connector, ungated capability",
                 "unblock": None})


if __name__ == "__main__":
    for cap in ("read-email", "decide-jev", "charge-card", "telepathy"):
        print(json.dumps(route(cap, check_approval=False), indent=2))


# Zero-Trust Verification Layer — this module's clause.
VERIFICATION = {'clause': 'no-fake-success', 'origin': 'empire-doctrine (honesty law: never fabricate a result)', 'check': 'test_omega.py + test_approval_tokens.py: unfueled capability -> BLOCKED with the exact unblock; checked-state demotion routes as the demoted state; most-restrictive gate wins over ungated duplicates; forged/replayed/expired tokens fail'}
