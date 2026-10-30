#!/usr/bin/env python3
"""
approve_live.py — mint (or revoke) a live-approval token for the Kali
Fleet live-execution gate (see approval.py).

THIS CLI IS THE ONLY WAY A TOKEN GETS CREATED. It is run by Jade ONLY
on the Boss's explicit per-run word — never on a schedule, never on a
model's initiative, never "just in case". One token = one tool + one
exact target + at most 60 minutes. When the run is done (or the word
is withdrawn), revoke it:

    python3 approve_live.py --revoke

Usage:
    python3 approve_live.py --tool akca_scan \
        --target https://127.0.0.1 --minutes 30 \
        --by "Boss, in chat" --note "bench check of the shop box"
"""

import argparse
import json
import sys

import approval


def main():
    p = argparse.ArgumentParser(
        description="Mint a per-run live-approval token (Boss's word only)")
    p.add_argument("--tool", default=None,
                   help="exact fleet action name (e.g. akca_scan) — one tool only; 'all' is refused")
    p.add_argument("--target", default=None,
                   help="exact allow-listed target string the token covers")
    p.add_argument("--minutes", type=int, default=30,
                   help=f"token lifetime in minutes (hard cap {approval.MAX_MINUTES})")
    p.add_argument("--by", default="",
                   help="who approved it and how (e.g. 'Boss, in chat')")
    p.add_argument("--note", default="", help="run note for the audit trail")
    p.add_argument("--revoke", action="store_true",
                   help="delete any live token instead of minting one")
    a = p.parse_args()

    if a.revoke:
        existed = approval.revoke()
        print("Live-approval token revoked." if existed
              else "No live-approval token was on file.")
        return 0

    if not a.tool or not a.target:
        p.error("--tool and --target are required to mint a token")
    try:
        token = approval.mint(a.tool, a.target, minutes=a.minutes,
                              issued_by=a.by, run_note=a.note)
    except ValueError as e:
        print(f"REFUSED: {e}")
        return 2
    print("Live-approval token minted (one run only):")
    print(json.dumps(token, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
