#!/usr/bin/env python3
"""
Live-Approval Gate — the Boss's law, in code (Kali Fleet).

THE LAW (Boss, 2026-10-21): "Never just let something go free that
literally exploits things. Only allow it to be live if I'm there and
I approve it." — "Nothing live unless I approve."

So: NO exploit-class fleet tool executes (non-dry-run) without a valid
live-approval token. The token is:
  - per-run: minted for ONE tool + ONE exact target,
  - time-boxed: expires at most MAX_MINUTES (60) after issue,
  - fail-closed: missing file, malformed JSON, expired token, tool
    mismatch, or target mismatch all mean NOT approved — each with its
    own plain reason string.

The gate controls WHEN a tool runs live, nothing else. It does not
change what any tool does once an approved execution happens.

SIGNED + SINGLE-USE (war-room fix, 2026-10-30 — the previous unsigned
JSON token was forgeable by anyone who could write the file, was
reusable until expiry, and honored a tool:"all" wildcard; all three
holes are demonstrated in warroom/sukuna.md + warroom/raga.md §5):
  - Every token carries an HMAC-SHA256 signature over its fields,
    keyed by a secret that lives OUTSIDE the repo tree (env
    KALI_FLEET_APPROVAL_SECRET, or a secret file — default
    ~/.config/kali-fleet/approval-secret, created 0600 by the first
    mint; override its path with FLEET_APPROVAL_SECRET_FILE).
    Unsigned or tampered tokens fail closed.
  - Every token carries a nonce. A SUCCESSFUL check consumes the
    nonce (recorded next to the secret, outside the tree); a replayed
    token fails. "Per-run" is now code, not prose.
  - check() enforces the 60-minute lifetime cap itself
    (expires_at - issued_at), not just mint().
  - tool:"all" is rejected at mint and never honored at check.

Tokens live at approvals/live-approval.json next to this file
(override with env FLEET_APPROVAL_FILE — tests use this). A token is
created ONLY by approve_live.py, run by Jade on the Boss's explicit
per-run word; nothing else in the codebase mints one. Revoking deletes
the token file.

Every mint, revoke, check-pass, and check-fail is appended to the
fleet's shared audit_log.jsonl via kali_bot.audit.

Stdlib only.
"""

import hashlib
import hmac
import json
import os
import secrets as _secrets
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import kali_bot  # noqa: E402 — shared audit mechanism

MAX_MINUTES = 60
DEFAULT_TOKEN_PATH = os.path.join(HERE, "approvals", "live-approval.json")
# Module-level so tests can monkeypatch the location; the real token
# path is only ever written by approve_live.py on the Boss's word.
TOKEN_PATH = os.environ.get("FLEET_APPROVAL_FILE") or DEFAULT_TOKEN_PATH


def _path():
    return TOKEN_PATH


# ------------------------------------------------------- signing secret

def _secret_file():
    return (os.environ.get("FLEET_APPROVAL_SECRET_FILE")
            or os.path.join(os.path.expanduser("~"), ".config",
                            "kali-fleet", "approval-secret"))


def _secret_bytes(create=False):
    """The HMAC key. Env first (transient), then the secret file
    outside the tree. mint() may create the file (0600); check()
    never creates — no secret on this machine means no token can
    verify, which fails closed."""
    env = os.environ.get("KALI_FLEET_APPROVAL_SECRET")
    if env:
        return env.encode("utf-8")
    path = _secret_file()
    try:
        with open(path, "rb") as f:
            return f.read().strip()
    except OSError:
        pass
    if not create:
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    key = _secrets.token_hex(32).encode("ascii")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key)
    return key


_SIGNED_FIELDS = ("tool", "target", "issued_at", "expires_at",
                  "issued_by", "run_note", "nonce")


def _sign(token, key):
    canonical = json.dumps({k: token.get(k, "") for k in _SIGNED_FIELDS},
                           sort_keys=True, separators=(",", ":"))
    return hmac.new(key, canonical.encode("utf-8"),
                    hashlib.sha256).hexdigest()


def _nonces_path():
    return os.path.join(os.path.dirname(_secret_file()), "used-nonces.json")


def _nonce_used(nonce):
    try:
        with open(_nonces_path(), "r", encoding="utf-8") as f:
            return nonce in json.load(f)
    except (OSError, ValueError):
        return False


def _consume_nonce(nonce, expires_at):
    """Record a nonce as spent. Returns False if the ledger cannot be
    written — the caller then fails closed rather than letting a
    token be replayable."""
    path = _nonces_path()
    try:
        try:
            with open(path, "r", encoding="utf-8") as f:
                used = json.load(f)
        except (OSError, ValueError):
            used = {}
        now = _now()
        used = {n: e for n, e in used.items()
                if datetime.fromisoformat(e) > now}
        used[nonce] = expires_at
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(used, f)
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat(timespec="seconds")


# ------------------------------------------------------------------ mint

def mint(tool, target, minutes=30, issued_by="", run_note=""):
    """Create a live-approval token for exactly one tool + target.
    Raises ValueError on a bad duration — tokens are hard-capped at
    MAX_MINUTES and must be positive. Returns the token dict."""
    if tool == "all":
        raise ValueError("wildcard tool 'all' is not mintable — one "
                         "token covers exactly one tool")
    minutes = int(minutes)
    if minutes <= 0:
        raise ValueError("approval minutes must be positive")
    if minutes > MAX_MINUTES:
        raise ValueError(
            f"live-approval tokens are hard-capped at {MAX_MINUTES} "
            f"minutes (got {minutes})")
    now = _now()
    token = {"tool": tool,
             "target": target,
             "issued_at": _iso(now),
             "expires_at": _iso(now + timedelta(minutes=minutes)),
             "issued_by": issued_by,
             "run_note": run_note,
             "nonce": _secrets.token_hex(16)}
    key = _secret_bytes(create=True)
    token["sig"] = _sign(token, key)
    path = _path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(token, f, indent=2)
    os.replace(tmp, path)
    kali_bot.audit({"action": "LIVE_APPROVAL_MINT", "tool": tool,
                    "target": target, "issued_by": issued_by,
                    "issued_at": token["issued_at"],
                    "expires_at": token["expires_at"],
                    "run_note": run_note})
    return token


def revoke():
    """Delete the live-approval token, if any. Returns True if a token
    was present (and is now gone)."""
    path = _path()
    existed = os.path.exists(path)
    if existed:
        os.remove(path)
    kali_bot.audit({"action": "LIVE_APPROVAL_REVOKE", "existed": existed})
    return existed


# ------------------------------------------------------------------ check

def _evaluate(tool, target, consume=True):
    path = _path()
    if not os.path.exists(path):
        return False, ("no live-approval token on file — nothing runs "
                       "live without the Boss's per-run approval")
    try:
        with open(path, "r", encoding="utf-8") as f:
            token = json.load(f)
    except (OSError, ValueError):
        return False, ("live-approval token file is malformed or "
                       "unreadable — failing closed")
    try:
        t_tool = token["tool"]
        t_target = token["target"]
        issued = datetime.fromisoformat(token["issued_at"])
        expires = datetime.fromisoformat(token["expires_at"])
    except (KeyError, TypeError, ValueError):
        return False, ("live-approval token is missing fields or has a "
                       "bad timestamp — failing closed")
    if issued.tzinfo is None:
        issued = issued.replace(tzinfo=timezone.utc)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if _now() >= expires:
        return False, f"live-approval token expired at {token['expires_at']}"
    if expires - issued > timedelta(minutes=MAX_MINUTES):
        return False, (f"live-approval token lifetime exceeds the "
                       f"{MAX_MINUTES}-minute cap — failing closed")
    if t_tool == "all":
        return False, ("wildcard tool 'all' tokens are never honored — "
                       "one token covers exactly one tool")
    if t_tool != tool:
        return False, (f"live-approval token covers tool '{t_tool}', "
                       f"not '{tool}'")
    if t_target != target:
        return False, (f"live-approval token covers target '{t_target}', "
                       f"not '{target}'")
    # Authenticity: unsigned, tampered, or foreign-signed tokens fail.
    sig = token.get("sig")
    nonce = token.get("nonce")
    if not sig or not nonce:
        return False, ("live-approval token is unsigned — tokens are "
                       "HMAC-signed at mint; failing closed")
    key = _secret_bytes()
    if key is None:
        return False, ("no approval secret on this machine — the token "
                       "cannot be verified; failing closed")
    if not hmac.compare_digest(sig, _sign(token, key)):
        return False, ("live-approval token signature does not verify — "
                       "forged or tampered; failing closed")
    # Single-use: a spent nonce never passes twice.
    if _nonce_used(nonce):
        return False, ("live-approval token was already used — tokens "
                       "are single-use (per-run); failing closed")
    if consume and not _consume_nonce(nonce, token["expires_at"]):
        return False, ("could not record the token's single use — "
                       "failing closed rather than leaving it replayable")
    return True, (f"valid signed single-use live-approval token for "
                  f"'{tool}' on '{target}' (expires {token['expires_at']})")


def check(tool, target, consume=True):
    """Fail-closed approval check for one tool + target.
    Returns (ok: bool, reason: str). Both outcomes are audit-logged.
    A successful check CONSUMES the token (single-use) unless
    consume=False is passed for a pure validity peek."""
    ok, reason = _evaluate(tool, target, consume=consume)
    kali_bot.audit({"action": "LIVE_APPROVAL_CHECK", "tool": tool,
                    "target": target, "ok": ok, "reason": reason})
    return ok, reason
