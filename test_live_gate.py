#!/usr/bin/env python3
"""
Live-approval gate tests — stdlib only, offline.

Run:  ~/workspace/venv/bin/python test_live_gate.py
Covers the Boss's law (2026-10-21): "Nothing live unless I approve."
Exploit-class fleet tools (akca_scan, omnisci3nt_recon) in execute mode
require a valid per-run, time-boxed approval token (approval.py):
  - no token            -> refused, LIVE_EXECUTION_REFUSED in the audit log
  - expired token       -> refused
  - wrong-tool token    -> refused
  - wrong-target token  -> refused
  - valid token         -> gate passes; the run reaches the existing
                           honest "not installed / not staged" results
  - dry-run, no token   -> unchanged (no approval needed)
  - mint cap (>60 min)  -> rejected
  - revoke              -> token gone, execute refused again
  - approve_live.py CLI -> mints/revokes ONLY at the temp token path
ALL tokens in this suite live at a temp path (approval.TOKEN_PATH is
monkeypatched / FLEET_APPROVAL_FILE points into the temp dir). The real
approvals/live-approval.json is never created by these tests, and the
suite asserts that at the end. NO tool is ever executed: akca's binary
lookup is patched out and FLEET_TOOLS_DIR points at an empty temp dir,
so omnisci3nt reports "not staged".
Exit code 0 = all green.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAILURES = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def main():
    tmp = tempfile.mkdtemp(prefix="fleet-gate-test-")
    audit_path = os.path.join(tmp, "audit.jsonl")
    os.environ["FLEET_AUDIT_LOG"] = audit_path
    os.environ.pop("FLEET_STOP", None)
    empty_tools = os.path.join(tmp, "no-tools-here")
    os.makedirs(empty_tools)
    os.environ["FLEET_TOOLS_DIR"] = empty_tools

    import kali_bot
    import fleet_tools
    import approval

    token_path = os.path.join(tmp, "live-approval.json")
    old_token_path = approval.TOKEN_PATH
    approval.TOKEN_PATH = token_path

    targets_file = os.path.join(tmp, "fleet_targets.txt")
    with open(targets_file, "w", encoding="utf-8") as f:
        f.write("127.0.0.1\n")
    old_targets_path = kali_bot.TARGETS_PATH
    kali_bot.TARGETS_PATH = targets_file

    def audit_text():
        try:
            with open(audit_path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return ""

    try:
        # 1. Execute with NO token -> refused at the gate (both tools)
        out = fleet_tools.run_tool("akca_scan", {"url": "https://127.0.0.1"}, execute=True)
        check("akca execute, no token -> refused",
              out.get("refused") is True and out.get("gate") == "LIVE_EXECUTION_REFUSED",
              f"got {out}")
        out = fleet_tools.run_tool("omnisci3nt_recon", {"target": "127.0.0.1"}, execute=True)
        check("omnisci3nt execute, no token -> refused",
              out.get("refused") is True and out.get("gate") == "LIVE_EXECUTION_REFUSED",
              f"got {out}")
        check("refusals audit-logged as LIVE_EXECUTION_REFUSED",
              "LIVE_EXECUTION_REFUSED" in audit_text())

        # 2. Dry-run without a token -> unchanged, no approval needed
        out = fleet_tools.run_tool("akca_scan", {"url": "https://127.0.0.1"}, execute=False)
        check("akca dry-run, no token -> ok as before",
              out.get("ok") is True and "akca -u https://127.0.0.1" in (out.get("would_run") or ""),
              f"got {out}")
        out = fleet_tools.run_tool("omnisci3nt_recon", {"target": "127.0.0.1"}, execute=False)
        check("omnisci3nt dry-run, no token -> ok as before",
              out.get("ok") is True, f"got {out}")

        # 3. Wrong-tool token -> refused
        approval.mint("omnisci3nt_recon", "127.0.0.1", minutes=10,
                      issued_by="test", run_note="gate test")
        out = fleet_tools.run_tool("akca_scan", {"url": "https://127.0.0.1"}, execute=True)
        check("wrong-tool token -> akca refused",
              out.get("refused") is True and "covers tool" in (out.get("approval_reason") or ""),
              f"got {out}")

        # 4. Wrong-target token -> refused
        approval.mint("akca_scan", "https://127.0.0.1:9999", minutes=10,
                      issued_by="test", run_note="gate test")
        out = fleet_tools.run_tool("akca_scan", {"url": "https://127.0.0.1"}, execute=True)
        check("wrong-target token -> akca refused",
              out.get("refused") is True and "covers target" in (out.get("approval_reason") or ""),
              f"got {out}")

        # 5. Expired token -> refused
        approval.mint("akca_scan", "https://127.0.0.1", minutes=10,
                      issued_by="test", run_note="gate test")
        with open(token_path, "r", encoding="utf-8") as f:
            tok = json.load(f)
        tok["issued_at"] = "2026-01-01T00:00:00+00:00"
        tok["expires_at"] = "2026-01-01T00:30:00+00:00"
        with open(token_path, "w", encoding="utf-8") as f:
            json.dump(tok, f)
        out = fleet_tools.run_tool("akca_scan", {"url": "https://127.0.0.1"}, execute=True)
        check("expired token -> akca refused",
              out.get("refused") is True and "expired" in (out.get("approval_reason") or ""),
              f"got {out}")

        # 6. Malformed token file -> refused, fail closed
        with open(token_path, "w", encoding="utf-8") as f:
            f.write("{not json")
        ok, why = approval.check("akca_scan", "https://127.0.0.1")
        check("malformed token -> check fails closed",
              ok is False and "malformed" in why, f"got {(ok, why)}")

        # 7. Valid token -> gate passes, existing honest results reached
        approval.mint("akca_scan", "https://127.0.0.1", minutes=10,
                      issued_by="test", run_note="gate test")
        with mock.patch.object(shutil, "which", return_value=None):
            out = fleet_tools.run_tool("akca_scan", {"url": "https://127.0.0.1"}, execute=True)
        res = out.get("result") or {}
        check("valid token -> akca reaches not-installed result",
              out.get("ok") is True and "not installed" in (res.get("error") or ""),
              f"got {out}")

        approval.mint("omnisci3nt_recon", "127.0.0.1", minutes=10,
                      issued_by="test", run_note="gate test")
        out = fleet_tools.run_tool("omnisci3nt_recon", {"target": "127.0.0.1"}, execute=True)
        res = out.get("result") or {}
        check("valid token -> omnisci3nt reaches not-staged result",
              out.get("ok") is True and "not staged" in (res.get("error") or ""),
              f"got {out}")
        check("check-pass audit-logged",
              "LIVE_APPROVAL_CHECK" in audit_text() and "LIVE_APPROVAL_MINT" in audit_text())

        # 8. Revoke -> token gone, execute refused again
        check("revoke reports a token existed", approval.revoke() is True)
        out = fleet_tools.run_tool("akca_scan", {"url": "https://127.0.0.1"}, execute=True)
        check("after revoke, execute refused again",
              out.get("refused") is True and out.get("gate") == "LIVE_EXECUTION_REFUSED",
              f"got {out}")

        # 9. Mint cap: >60 minutes rejected, nothing written
        try:
            approval.mint("akca_scan", "https://127.0.0.1", minutes=61,
                          issued_by="test", run_note="gate test")
            capped = False
        except ValueError:
            capped = True
        check("mint >60 min rejected", capped and not os.path.exists(token_path))

        # 10. approve_live.py CLI: mints + revokes at the TEMP path only
        env = dict(os.environ)
        env["FLEET_APPROVAL_FILE"] = os.path.join(tmp, "cli-token.json")
        env["FLEET_AUDIT_LOG"] = audit_path
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "approve_live.py"),
             "--tool", "akca_scan", "--target", "https://127.0.0.1",
             "--minutes", "15", "--by", "test", "--note", "cli test"],
            capture_output=True, text=True, timeout=60, env=env)
        check("approve_live.py mint exits 0 and writes the temp token",
              proc.returncode == 0 and os.path.exists(env["FLEET_APPROVAL_FILE"]),
              f"rc={proc.returncode} stderr={proc.stderr[-300:]}")
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "approve_live.py"), "--revoke"],
            capture_output=True, text=True, timeout=60, env=env)
        check("approve_live.py --revoke removes the temp token",
              proc.returncode == 0 and not os.path.exists(env["FLEET_APPROVAL_FILE"]),
              f"rc={proc.returncode} stderr={proc.stderr[-300:]}")
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "approve_live.py"),
             "--tool", "akca_scan", "--target", "https://127.0.0.1",
             "--minutes", "90"],
            capture_output=True, text=True, timeout=60, env=env)
        check("approve_live.py rejects --minutes 90",
              proc.returncode != 0 and not os.path.exists(env["FLEET_APPROVAL_FILE"]),
              f"rc={proc.returncode}")
    finally:
        approval.TOKEN_PATH = old_token_path
        kali_bot.TARGETS_PATH = old_targets_path
        os.environ.pop("FLEET_TOOLS_DIR", None)

    # 11. The REAL token file must not exist — tests never mint for real
    check("no real approvals/live-approval.json exists",
          not os.path.exists(approval.DEFAULT_TOKEN_PATH))

    print()
    if FAILURES:
        print(f"SMOKE: {len(FAILURES)} FAILURE(S): {FAILURES}")
        return 1
    print("SMOKE: ALL GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
