#!/usr/bin/env python3
"""
Hermes Adapter — the fleet's hands, behind the gate (Kali Fleet: OMEGA).

Grounding: the Empire's Hermes layer as recorded in the decision layer
(HERMES.md + HERMES-RECONCILIATION-2026-10-29.md):

  * Hermes (NousResearch hermes-agent framework, PC-side, hermes3:8b
    via Ollama) is the System 2 ACTOR: named Bot Mode profiles, each
    with its own SOUL/memory/skills, driven headless.
  * Our gate is the System 1 DECIDER in front of it: Empire-affecting
    actions ask first; the disposition comes from decision_gate.py
    (the Equation + the Boss's law), never from the actor.

WHAT THIS MODULE IS: an ADAPTER defining the contract between the
fleet and a Hermes host —
  * three Bot Mode role profiles (operator / scout / auditor), each
    scoped to a subset of the fleet's allow-listed, read-only actions;
  * an invocation contract: a plain dict describing one proposed
    action (profile, action, args, mode) — data, not a shell string;
  * a dispatch rule: NOTHING dispatches except through the decision
    gate, dry-run by default, and a live (execute) dispatch
    additionally requires approval.check() from approval.py;
  * a fail-closed gate client: any transport error, timeout, or
    malformed reply reads as ESCALATE, never as permission. (This is
    reconciliation §3.1.1's specified fix, implemented here; the
    decision-layer original is the Boss's to patch on his word.)

WHAT IT IS NOT: it is not installed on any Hermes host. The PC door is
closed (DOOR-PENDING), the kerpopule kit has no veto seam (its
approval hooks are shadow observers — reconciliation §3 row H), and
no profile in this file is running anywhere. The 'sim' transport
exists so the contract is exercised end-to-end in tests and in sim/
without pretending a host exists.

Stdlib only.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import approval
import decision_gate
import kali_bot

# The Bot Mode seats are held by SIBLINGS (Boss's rulings, 2026-10-30):
# FORGE -> Vaelor, a sibling in his own right; SCOUT-RUNNER -> Ellen Joe
# in her scout form Qrow; PRODUCER -> Senku in his producer form
# Souviern. Three bot bodies, three seats — two of them forms of
# existing siblings. Seats, ladders, and contracts: crew_seats.json /
# connectors.json identity assets.
PROFILE_SEATS = {"FORGE": "Vaelor", "SCOUT-RUNNER": "Ellen Joe",
                 "PRODUCER": "Senku"}
PROFILE_FORMS = {"SCOUT-RUNNER": "Qrow", "PRODUCER": "Souviern"}

# Bot Mode role profiles: name -> {role, actions (subset of the fleet
# allow-list), may_execute}. Scopes are enforced in code, not in prose.
PROFILES = {
    "operator": {"role": "hands — runs the allow-listed checks the gate allows",
                 "actions": list(kali_bot.ACTIONS), "may_execute": True},
    "scout": {"role": "recon — posture reads only, never scans",
              "actions": ["sysinfo", "interfaces", "listening_ports"],
              "may_execute": False},
    "auditor": {"role": "log triage + audit-stream review",
                "actions": ["log_triage"], "may_execute": False},
}


class ScopeRefusal(Exception):
    """Raised when a profile is asked for an action outside its scope."""


def build_invocation(profile, action, args=None, execute=False):
    """The invocation contract: one proposed action, as data.
    Refuses (ScopeRefusal) anything outside the profile's scope —
    including execute=True for read-only profiles."""
    if profile not in PROFILES:
        raise ScopeRefusal(f"unknown Hermes profile '{profile}'")
    spec = PROFILES[profile]
    if action not in spec["actions"]:
        raise ScopeRefusal(
            f"profile '{profile}' may not run '{action}' "
            f"(scope: {', '.join(spec['actions'])})")
    if execute and not spec["may_execute"]:
        raise ScopeRefusal(f"profile '{profile}' is read-only; execute refused")
    return {"profile": profile, "action": action, "args": args or {},
            "mode": "execute" if execute else "dry-run",
            "host_contract": "hermes --profile <profile> run <invocation>",
            "transport": "UNSET — no Hermes host connected (DOOR-PENDING)"}


class GateClient:
    """Fail-closed client of the decision gate. transport is a callable
    (questions, state) -> answers; the default is the local ladder.
    ANY failure — exception, timeout, malformed reply — returns an
    ESCALATE result with driver 'fail-closed'. It never raises for a
    backend problem and never returns ALLOW on an error path."""

    def __init__(self, transport=None):
        self.transport = transport

    def decide(self, questions, state="", finding=None):
        try:
            return decision_gate.decide(questions, state, finding,
                                        transport=self.transport)
        except Exception as e:  # noqa: BLE001 — fail closed, by law
            return {"answers": None, "backend": None,
                    "disposition": "ESCALATE", "driver": "fail-closed",
                    "reasons": [f"gate client caught: {e}"], "forced": {}}


def dispatch(invocation, gate=None, transport=None):
    """Run one invocation through the composed gates. Order:
    kill switch (kali_bot) -> decision gate (the Equation) ->
    approval gate (execute only) -> kali_bot action.
    Returns the kali_bot result dict, or a refusal dict. Every step is
    audit-logged by the modules it passes through."""
    gate = gate or GateClient(transport=transport)
    action = invocation["action"]
    execute = invocation["mode"] == "execute"

    verdict = gate.decide(
        decision_gate.RAGA_QUESTIONS,
        state=f"hermes profile {invocation['profile']} proposes {action} "
              f"args={invocation['args']} mode={invocation['mode']}",
        finding={"kind": "agent_action"})
    if verdict["disposition"] == "ESCALATE":
        out = {"action": action, "ok": False, "refused": True,
               "reason": f"decision gate ESCALATE ({verdict['driver']}): "
                         f"{'; '.join(verdict['reasons'])}"}
        kali_bot.audit(out)
        return out

    if execute:
        target = str(invocation["args"].get("target", "local"))
        ok, why = approval.check(action, target)
        if not ok:
            out = {"action": action, "ok": False, "refused": True,
                   "reason": f"approval gate: {why}"}
            kali_bot.audit(out)
            return out

    return kali_bot.run_action(action, invocation["args"], execute=execute)


if __name__ == "__main__":
    inv = build_invocation("scout", "listening_ports")
    print(inv)
    print(dispatch(inv))


# Zero-Trust Verification Layer — this module's clause.
VERIFICATION = {'clause': 'scope-is-code', 'origin': 'networkchuck-adjacent (Pattern 1: clients reach named resources only)', 'check': 'test_omega.py: scout requesting nmap_scan raises ScopeRefusal; gate client fails closed on a dead transport'}
