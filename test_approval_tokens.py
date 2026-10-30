#!/usr/bin/env python3
"""
Gate-integrity tests — the war-room fix list (raga.md §7 items 1-4),
written for the re-sweep probe, not for a summary.

Covers, against the REAL modules:
  - forged token (hand-written, unsigned, expiry 9999) FAILS
  - tampered token (signed, then edited) FAILS
  - replayed token FAILS (nonce consumed on first successful check)
  - expired token FAILS (reason names the expiry)
  - over-cap token (lifetime > 60 min, validly signed) FAILS
  - tool:"all" — mint refuses; a hand-written wildcard FAILS
  - router: an ungated duplicate cannot shadow a gated route
    (most-restrictive gate wins)
  - router: capability names are case-normalized ('Send-Email'
    cannot bypass the gated-capability law)
  - router: god_check demotions are wired in — a connector checked
    KEY-PENDING routes as its demoted state, not its claim
  - hf_brain: an unknown rung name and a raw transport error both
    step down to the floor (Hermes seat regression)

Run:  ~/workspace/venv/bin/python test_approval_tokens.py
Exit code 0 = all green. All token/secret/nonce state lives in a
temp dir (FLEET_APPROVAL_FILE + FLEET_APPROVAL_SECRET_FILE); the
real approval secret is never touched.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
TMP = tempfile.mkdtemp(prefix="omega-gatefix-")
os.environ["FLEET_AUDIT_LOG"] = os.path.join(TMP, "audit.jsonl")
os.environ["FLEET_APPROVAL_SECRET_FILE"] = os.path.join(
    TMP, "approval-secret")

import approval
import god_router
import hf_brain

approval.TOKEN_PATH = os.path.join(TMP, "live-approval.json")
FAILURES = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}"
          + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def write_token(tok):
    with open(approval.TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(tok, f)


def iso(dt):
    return dt.isoformat(timespec="seconds")


def main():
    now = datetime.now(timezone.utc)

    # ---- forged: hand-written, unsigned, expiry 9999 ------------------
    write_token({"tool": "charge-card", "target": "Stripe",
                 "issued_at": iso(now),
                 "expires_at": "9999-01-01T00:00:00+00:00",
                 "issued_by": "attacker", "run_note": ""})
    ok, why = approval.check("charge-card", "Stripe")
    check("forged unsigned token (expiry 9999) FAILS", not ok, why)

    # ---- forged within the cap: unsigned but plausible ---------------
    write_token({"tool": "charge-card", "target": "Stripe",
                 "issued_at": iso(now),
                 "expires_at": iso(now + timedelta(minutes=30)),
                 "issued_by": "attacker", "run_note": ""})
    ok, why = approval.check("charge-card", "Stripe")
    check("forged unsigned token (plausible dates) FAILS", not ok, why)

    # ---- tampered: mint for real, then edit the target ----------------
    approval.mint("charge-card", "Stripe", minutes=10, issued_by="test")
    with open(approval.TOKEN_PATH) as f:
        tok = json.load(f)
    tok["target"] = "Gmail"
    write_token(tok)
    ok, why = approval.check("charge-card", "Gmail")
    check("tampered token (target edited post-signing) FAILS",
          not ok and "signature" in why, why)

    # ---- replay: a genuine token works exactly once -------------------
    approval.mint("charge-card", "Stripe", minutes=10, issued_by="test")
    ok1, _ = approval.check("charge-card", "Stripe")
    ok2, why2 = approval.check("charge-card", "Stripe")
    check("genuine token passes once", ok1)
    check("replayed token FAILS (nonce consumed)",
          not ok2 and "already used" in why2, why2)

    # ---- expired: genuine token, clock moved past it ------------------
    approval.mint("charge-card", "Stripe", minutes=10, issued_by="test")
    with open(approval.TOKEN_PATH) as f:
        tok = json.load(f)
    tok["issued_at"] = "2026-01-01T00:00:00+00:00"
    tok["expires_at"] = "2026-01-01T00:10:00+00:00"
    write_token(tok)
    ok, why = approval.check("charge-card", "Stripe")
    check("expired token FAILS with the expiry named",
          not ok and "expired" in why, why)

    # ---- over-cap: validly signed, lifetime 999 minutes ---------------
    tok = approval.mint("charge-card", "Stripe", minutes=60,
                        issued_by="test")
    tok["expires_at"] = iso(datetime.fromisoformat(tok["issued_at"])
                            + timedelta(minutes=999))
    tok["sig"] = approval._sign(tok, approval._secret_bytes())
    write_token(tok)
    ok, why = approval.check("charge-card", "Stripe")
    check("over-cap lifetime FAILS even when validly signed",
          not ok and "cap" in why, why)

    # ---- wildcard: mint refuses, hand-written 'all' never honored -----
    try:
        approval.mint("all", "Stripe", minutes=10, issued_by="test")
        check("mint(tool='all') refused", False, "mint accepted 'all'")
    except ValueError:
        check("mint(tool='all') refused", True)
    write_token({"tool": "all", "target": "Stripe",
                 "issued_at": iso(now),
                 "expires_at": iso(now + timedelta(minutes=30)),
                 "issued_by": "attacker", "run_note": "",
                 "nonce": "x", "sig": "y"})
    ok, why = approval.check("charge-card", "Stripe")
    check("hand-written wildcard token FAILS", not ok, why)

    # ---- router: ungated duplicate cannot shadow a gated route --------
    shadow = {"connectors": [
        {"name": "Open Clone", "capabilities": ["charge-card"],
         "transport": "api", "state": "LIVE", "gate": "none",
         "unblock": None, "verification": {"clause": "t", "check": "t"}},
        {"name": "Stripe", "capabilities": ["charge-card"],
         "transport": "connector", "state": "LIVE", "gate": "approval",
         "unblock": None, "verification": {"clause": "t", "check": "t"}}],
        "identity_assets": []}
    approval.revoke()
    r = god_router.route("charge-card", data=shadow, checked={})
    check("most-restrictive gate wins over an ungated duplicate",
          r["decision"] == "REQUIRES_APPROVAL"
          and r["connector"] == "Stripe"
          and "shadow" in r["reason"], json.dumps(r))

    # ---- router: case-normalized capability matching ------------------
    # checked={} = registry-only mode: these two checks test MATCHING,
    # not probe health (the demotion path is tested separately below
    # with injected maps; a live 401 must not make matching untestable)
    r = god_router.route("Send-Email", check_approval=False, checked={})
    check("'Send-Email' (capitalized) still hits the approval gate",
          r["decision"] == "REQUIRES_APPROVAL"
          and r["connector"] == "Gmail", json.dumps(r))
    r = god_router.route("  READ-EMAIL ", check_approval=False, checked={})
    check("whitespace/case-normalized read routes",
          r["decision"] == "ROUTE" and r["connector"] == "Gmail",
          json.dumps(r))

    # ---- router: god_check demotion is wired into routing -------------
    r = god_router.route("read-email", check_approval=False,
                         checked={"Gmail": "KEY-PENDING"})
    check("checked KEY-PENDING demotes the route to BLOCKED",
          r["decision"] == "BLOCKED" and "proven > claimed" in r["reason"],
          json.dumps(r))
    r = god_router.route("read-email", check_approval=False,
                         checked={"Gmail": "CHECK-FAILED"})
    check("checked CHECK-FAILED demotes the route to BLOCKED",
          r["decision"] == "BLOCKED", json.dumps(r))

    # ---- hf_brain: unknown rung + raw error both reach the floor ------
    def raw_boom(member, prompt):
        raise ConnectionError("raw transport error, not a RungDown")
    dead = {"hf": raw_boom, "openrouter": raw_boom, "zen": raw_boom,
            "ollama-local": raw_boom}
    out = hf_brain.chat("Hermes", "status?", transports=dead, token="t")
    check("Hermes: raw transport errors step down to the floor",
          out["rung"] == "heuristic-floor", str(out["fell_through"]))
    out = hf_brain.chat("Vaelor", "status?",
                        transports={"bogus-rung": raw_boom}, token="t")
    check("standard seat still floors with all rungs down",
          out["rung"] == "heuristic-floor")

    print()
    if FAILURES:
        print(f"GATEFIX: {len(FAILURES)} FAILURE(S): {FAILURES}")
        return 1
    print("GATEFIX: ALL GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
