#!/usr/bin/env python3
"""
Brain adapter — how the Empire PC Agent swaps its brain to Token Factory.

The existing agent (~/workspace/empire/work/pc-control/pc_agent.py) is a
queue-driven executor with a hard allow-list (COMMANDS) and a kill switch.
It has no language brain of its own: Jade's console (jade_pc.py) sends exact
command names. This adapter is the missing brain layer, kept OUT of the
original files on purpose:

    plain-English request
        -> parse_intent()   Nemotron 3 Nano class via Token Factory (fast tier)
        -> allow-list gate  action must exist in the agent's COMMANDS table
        -> dispatch         pc_agent COMMANDS name (on the PC) or, for the
                            local Kali build, kali_bot.run_action()
        -> narrate()        Nemotron 3 Super class via Token Factory (plan
                            tier) turns the raw result into a plain answer

The mapping below is the whole swap: PC_AGENT_ACTIONS translates the Kali
Fleet action vocabulary onto pc_agent.py's existing command names, so the
same brain drives both the Kali box and Boss's PC without touching either
executor. Multi-step plans (chained actions, "check X then tell me Y") are
where the plan tier earns its keep; the deep tier (Nemotron 3 Ultra class)
is reserved for hard reasoning, e.g. correlating a week of audit logs —
call client.chat(..., tier="deep") at that layer.

With no TOKEN_FACTORY_API_KEY set, everything runs on the client's clearly
labeled mock responses, so the loop demos offline end to end.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import kali_bot
from token_factory import TokenFactoryClient, TokenFactoryError

# Kali Fleet action -> pc_agent.py COMMANDS name (identical semantics).
PC_AGENT_ACTIONS = {
    "sysinfo": "sysinfo",
    "listening_ports": "net_listen",
    "interfaces": "net_listen",      # closest PC-side equivalent (listeners)
    "log_triage": "grep",            # PC side: grep the log for error patterns
    "nmap_scan": None,               # NO PC-side equivalent — Kali box only,
                                     # and only against fleet_targets.txt
}

PARSE_SYSTEM = (
    "You are the intent parser for a security agent that may ONLY run these "
    "actions: sysinfo, listening_ports, interfaces, log_triage, nmap_scan. "
    "Reply with one JSON object and nothing else: "
    '{"action": <one of those names>, "args": {...}}. '
    "For nmap_scan include args.target exactly as the user named it — an "
    "allow-list downstream decides whether it may run. For log_triage "
    "include args.path."
)


class Brain:
    def __init__(self, client=None):
        self.client = client or TokenFactoryClient()

    def parse_intent(self, request):
        """Plain English -> {action, args}. Fast tier (Nano class)."""
        try:
            r = self.client.chat(
                [{"role": "system", "content": PARSE_SYSTEM},
                 {"role": "user", "content": request}],
                tier="fast")
            intent = json.loads(r["content"])
            if intent.get("action") not in kali_bot.ACTIONS:
                raise ValueError("model returned a non-allow-listed action")
            intent.setdefault("args", {})
            intent["_model"] = r["model"]
            intent["_mock"] = r["mock"]
            return intent
        except (TokenFactoryError, ValueError, json.JSONDecodeError) as e:
            # Fail CLOSED: an unparseable intent becomes a harmless sysinfo
            # dry-run request, never a guess at something privileged.
            return {"action": "sysinfo", "args": {},
                    "_model": "fallback", "_mock": self.client.mock_mode,
                    "_parse_error": str(e)}

    def dispatch(self, intent, execute=False):
        """Allow-list gate + executor call (kali_bot enforces its own
        target allow-list, kill switch, and audit log)."""
        action = intent["action"]
        if action not in kali_bot.ACTIONS:
            return {"ok": False, "refused": True,
                    "reason": f"'{action}' is not an allow-listed action"}
        return kali_bot.run_action(action, intent.get("args", {}), execute=execute)

    def narrate(self, request, intent, result):
        """Raw result -> plain-English answer. Plan tier (Super class)."""
        prompt = (f"User asked: {request}\n"
                  f"Action taken: {intent['action']} "
                  f"(mode: {result.get('mode', 'dry-run')})\n"
                  f"Result JSON: {json.dumps(result)[:3000]}\n"
                  "Summarize plainly in 2-4 sentences: what was checked, "
                  "what was found, anything refused and why.")
        try:
            r = self.client.chat([{"role": "user", "content": prompt}], tier="plan")
            return r["content"]
        except TokenFactoryError as e:
            return f"(narration unavailable: {e}) Raw result: {json.dumps(result)[:500]}"

    def handle(self, request, execute=False):
        """The full loop: parse -> gate -> dispatch -> narrate."""
        intent = self.parse_intent(request)
        result = self.dispatch(intent, execute=execute)
        answer = self.narrate(request, intent, result)
        return {"request": request, "intent": intent,
                "result": result, "answer": answer}
