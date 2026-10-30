#!/usr/bin/env python3
"""
Kali Fleet — end-to-end CLI demo.

Runs the full loop with ZERO keys (Token Factory client in mock mode):

    plain-English request
      -> mock Nemotron parse (fast tier, intent JSON)
      -> allow-list gate
      -> kali_bot action in DRY-RUN (nothing is executed)
      -> mock Nemotron narration (plan tier)
      -> every step appended to the audit log

Usage:
    python demo.py --once                 # one canned request, then exit
    python demo.py --request "what ports are listening right now?"
    python demo.py                        # interactive loop (Ctrl-C to exit)

The demo NEVER executes commands: dispatch is hard-wired to dry-run here.
Set TOKEN_FACTORY_API_KEY (owner-supplied, via Secure Vault) and the same
loop runs against live Nemotron models on Token Factory instead of mocks.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brain_tokenfactory import Brain

CANNED_REQUESTS = [
    "What ports are listening on this machine right now?",
    "Give me a system info summary of this host.",
    "Scan 8.8.8.8 for services.",  # deliberately refused: not allow-listed
]


def show(turn):
    print("=" * 72)
    print(f"REQUEST : {turn['request']}")
    intent = turn["intent"]
    model = intent.get("_model", "?")
    tag = "MOCK" if intent.get("_mock") else "LIVE"
    print(f"PARSE   : [{tag} {model}] -> action={intent['action']} args={intent.get('args', {})}")
    res = turn["result"]
    if res.get("refused"):
        print(f"GATE    : REFUSED — {res['reason']}")
    else:
        print(f"ACTION  : mode={res.get('mode')} would_run={res.get('would_run')}")
    print(f"ANSWER  : {turn['answer']}")
    print()


def main():
    p = argparse.ArgumentParser(description="Kali Fleet offline demo (mock Nemotron, dry-run actions)")
    p.add_argument("--once", action="store_true", help="run one canned request and exit")
    p.add_argument("--request", default=None, help="run a single custom request and exit")
    a = p.parse_args()

    brain = Brain()
    mode = "MOCK (no TOKEN_FACTORY_API_KEY set)" if brain.client.mock_mode else "LIVE Token Factory"
    print(f"Kali Fleet demo — brain: {mode}; actions: DRY-RUN only; audit log on.\n")

    if a.request:
        show(brain.handle(a.request, execute=False))
        return 0
    if a.once:
        show(brain.handle(CANNED_REQUESTS[0], execute=False))
        return 0
    for req in CANNED_REQUESTS:
        show(brain.handle(req, execute=False))
    print("Interactive mode — type a request, or 'quit'. (Dry-run only.)")
    try:
        while True:
            line = input("fleet> ").strip()
            if line.lower() in ("quit", "exit", ""):
                if line:
                    break
                continue
            show(brain.handle(line, execute=False))
    except (EOFError, KeyboardInterrupt):
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
