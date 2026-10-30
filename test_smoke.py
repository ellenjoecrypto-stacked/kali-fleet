#!/usr/bin/env python3
"""
Kali Fleet smoke tests — stdlib only, no keys required.

Run:  ~/workspace/venv/bin/python test_smoke.py
Covers: Token Factory mock mode, allow-list load + localhost present,
non-allow-listed target refusal, kill switch, demo.py --once end to end.
Writes go to a throwaway audit log (FLEET_AUDIT_LOG in a temp dir).
Exit code 0 = all green.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAILURES = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def main():
    tmp = tempfile.mkdtemp(prefix="kali-fleet-test-")
    os.environ["FLEET_AUDIT_LOG"] = os.path.join(tmp, "audit.jsonl")
    os.environ.pop("TOKEN_FACTORY_API_KEY", None)  # force mock mode
    os.environ.pop("FLEET_STOP", None)

    import kali_bot
    from token_factory import TokenFactoryClient

    # 1. Token Factory mock mode returns a response
    client = TokenFactoryClient(api_key="")
    check("token_factory mock mode is on", client.mock_mode)
    r = client.chat([{"role": "user", "content": "what ports are listening?"}], tier="fast")
    check("mock chat returns content", bool(r["content"]) and r["mock"] is True)
    try:
        intent = json.loads(r["content"])
        check("mock intent parses to allow-listed action",
              intent.get("action") in kali_bot.ACTIONS, f"got {intent}")
    except json.JSONDecodeError:
        check("mock intent parses to allow-listed action", False, "not JSON")

    # 2. Allow-list loads and contains localhost
    targets = kali_bot.load_targets()
    check("allow-list contains 127.0.0.1", "127.0.0.1" in targets, f"targets={targets}")

    # 3. Non-allow-listed target is refused
    out = kali_bot.run_action("nmap_scan", {"target": "8.8.8.8"}, execute=False)
    check("non-allow-listed target refused", out.get("refused") is True, f"got {out}")
    out = kali_bot.run_action("nmap_scan", {"target": "127.0.0.1"}, execute=False)
    check("allow-listed localhost dry-run passes gate", out.get("ok") is True, f"got {out}")

    # 4. Unknown action refused; kill switch blocks everything
    out = kali_bot.run_action("rm_everything", {}, execute=False)
    check("unknown action refused", out.get("refused") is True)
    os.environ["FLEET_STOP"] = "1"
    out = kali_bot.run_action("sysinfo", {}, execute=False)
    check("kill switch (FLEET_STOP=1) blocks sysinfo", out.get("refused") is True, f"got {out}")
    out = kali_bot.run_action("nmap_scan", {"target": "127.0.0.1"}, execute=False)
    check("kill switch blocks scan too", out.get("refused") is True)
    del os.environ["FLEET_STOP"]

    # 5. demo.py --once runs cleanly as a subprocess (fresh interpreter)
    env = dict(os.environ)
    env["FLEET_AUDIT_LOG"] = os.path.join(tmp, "audit_demo.jsonl")
    env.pop("TOKEN_FACTORY_API_KEY", None)
    proc = subprocess.run([sys.executable, os.path.join(HERE, "demo.py"), "--once"],
                          capture_output=True, text=True, timeout=120, env=env)
    check("demo.py --once exits 0", proc.returncode == 0,
          f"rc={proc.returncode} stderr={proc.stderr[-400:]}")
    check("demo.py --once shows the full loop",
          "PARSE" in proc.stdout and "ANSWER" in proc.stdout)

    print()
    if FAILURES:
        print(f"SMOKE: {len(FAILURES)} FAILURE(S): {FAILURES}")
        return 1
    print("SMOKE: ALL GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
