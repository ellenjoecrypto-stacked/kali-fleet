#!/usr/bin/env python3
"""
Watchdog — Hu Tao's seat: the never-down keeper (Kali Fleet: OMEGA).

The Phoenix pattern, applied to brains: every crew seat's brain ladder
(hf_brain.py) is health-checked rung by rung; a seat whose top rung is
down is RE-ROUTED to its next healthy rung, and every revival is
logged to the fleet audit log (WATCHDOG_REVIVE / WATCHDOG_OK /
WATCHDOG_FLOOR). A seat degrades, never dies — when every fueled rung
is down, the seat sits on its heuristic floor, labeled, and the
watchdog says so loudly instead of pretending otherwise.

Health, honestly defined for this machine: a rung is "healthy" when
its fuel physically exists here (env key present for keyed rungs; a
certified served model for the local rung). The watchdog checks
PRESENCE, not validity — a present-but-dead key (the vault Zen key
returned 401) is a live-call question, and the watchdog does not spend
calls. Probes are injectable so the revival logic is testable without
faking a network.

Stdlib only. Read-only except its own audit entries.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import hf_brain
import kali_bot

RUNG_ENV = {"hf": "HF_TOKEN", "openrouter": "OPENROUTER_API_KEY",
            "zen": "OPENCODE_ZEN_API_KEY"}


def default_probe(rung):
    """Presence-based health for one rung, on this machine."""
    if rung in RUNG_ENV:
        return bool(os.environ.get(RUNG_ENV[rung]))
    if rung == "ollama-local":
        return bool(os.environ.get("OMEGA_LOCAL_MODEL")
                    or os.environ.get("DECISION_LAYER_LOCAL_MODEL"))
    if rung.startswith("ollama-local"):
        return False  # the PC seat's local rung rides the closed door
    if rung == "heuristic-floor":
        return True  # the floor is code, not fuel — it cannot be down
    return False


def check_seat(member, probe=None):
    """Walk the seat's ladder; return {member, active_rung, down,
    revived}. Logs a WATCHDOG_REVIVE when the active rung is not the
    ladder's top, WATCHDOG_FLOOR when only the floor holds."""
    probe = probe or default_probe
    seat = hf_brain.assignment(member)
    down = []
    for rung in seat["ladder"]:
        if probe(rung):
            revived = rung != seat["ladder"][0]
            out = {"member": member, "active_rung": rung, "down": down,
                   "revived": revived}
            if rung == "heuristic-floor" and down:
                kali_bot.audit({"action": "WATCHDOG_FLOOR", **out})
            elif revived:
                kali_bot.audit({"action": "WATCHDOG_REVIVE", **out})
            else:
                kali_bot.audit({"action": "WATCHDOG_OK", **out})
            return out
        down.append(rung)
    raise AssertionError("unreachable — the floor probe always returns True")


def health_report(probe=None):
    return [check_seat(s["member"], probe=probe) for s in hf_brain.seats()]


VERIFICATION = {"clause": "revival-is-logged",
                "check": "test_crew.py: a seat with its top rung down is re-routed and the revival lands in the audit log; all rungs down -> floor, logged as WATCHDOG_FLOOR"}

if __name__ == "__main__":
    import json
    for row in health_report():
        print(json.dumps(row))
