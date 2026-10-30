#!/usr/bin/env python3
"""
Fleet Tools — harness wrappers for the vetted Dayofexploits BUILD tier.

SCOPE — STRICT: the owner's OWN machines and AUTHORIZED LABS ONLY, same as
kali_bot.py. Every tool here was statically vetted read-only BEFORE a wrapper
was written (see ~/workspace/empire/work/crew-stack-bundle/
DAYOFEXPLOITS-VETTING.md). Tools that HOLD or FAIL vetting (akha-xss,
MEXSTRIKE) are deliberately NOT registered — asking for them is refused like
any unknown action.

Registered tools (vetting verdict PASS, 2026-10-21):
  akca_scan        akca Go web scanner — target is a URL whose host must be
                   in fleet_targets.txt. (github.com/akha-security/akca,
                   Apache-2.0)
  omnisci3nt_recon omnisci3nt domain recon — target domain/host must be in
                   fleet_targets.txt. (github.com/spyboy-productions/
                   omnisci3nt, MIT)
  wifit3_audit     wifit3 USB Wi-Fi auditor — target BSSID/SSID must be in
                   fleet_targets.txt. wifit3 is an interactive TUI needing
                   root + a supported USB adapter, so the harness gates and
                   audits the target but NEVER launches it; execute mode
                   refuses with bench instructions. (github.com/derv82/
                   wifit3, GPL-2.0)

SAFETY — identical machinery to kali_bot.py, reused not reimplemented:
  - Allow-list: fleet_targets.txt via kali_bot.load_targets/target_allowed.
  - Kill switch: env FLEET_STOP=1 or STOP.txt (kali_bot.kill_switch_on).
  - Dry-run is the default; -Execute actually runs the tool (akca /
    omnisci3nt only, and only if the tool is present on this machine).
  - LIVE-APPROVAL GATE (Boss's law, 2026-10-21 — "Nothing live unless
    I approve"): every -Execute of an exploit-class tool (akca_scan,
    omnisci3nt_recon) first calls approval.check(tool, target) and is
    REFUSED without a valid per-run, time-boxed token. Tokens are
    minted only by approve_live.py, on the Boss's explicit word.
    Dry-run never needs a token. See approval.py.
  - Every attempt (allowed, refused, dry-run, executed) is appended to the
    fleet JSONL audit log via kali_bot.audit.

Staged tool sources live in the fleet sandbox
(~/workspace/empire/work/crew-stack-bundle/sandbox/tools/) since the
Boss's 2026-10-21 sandbox order; override with env FLEET_TOOLS_DIR.
Execute-mode subprocesses run through sandbox.py: cwd inside the
sandbox, environment scrubbed from scratch (no inherited keys/tokens),
network namespace isolation for non-target invocations, and the sandbox
layers actually used are recorded in every result / audit entry.
Stdlib only.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import kali_bot  # noqa: E402 — safety primitives: kill switch, allow-list, audit
import sandbox  # noqa: E402 — isolation layer for execute-mode subprocesses
import approval  # noqa: E402 — live-approval gate (Boss's law: nothing live unless he approves)

TOOLS = ("akca_scan", "omnisci3nt_recon", "wifit3_audit")

# Exploit-class wrappers: their -Execute paths are behind the
# live-approval gate (approval.py). wifit3_audit is NOT here — the
# harness never launches it at all (manual bench only, see below).
EXPLOIT_CLASS_TOOLS = ("akca_scan", "omnisci3nt_recon")


def tools_dir():
    return os.environ.get("FLEET_TOOLS_DIR") or sandbox.tools_root()


def _host_of(url_or_host):
    """Extract the host from a URL (or bare host[:port]) for allow-listing."""
    if not url_or_host:
        return ""
    parsed = urllib.parse.urlparse(
        url_or_host if "://" in url_or_host else f"//{url_or_host}")
    return parsed.hostname or ""


# ------------------------------------------------------------------ tools
# Each returns (would_run_description, result_dict_or_None_when_executed),
# or (desc, "REFUSED") when the target fails the allow-list — same contract
# as kali_bot's act_nmap_scan.

def tool_akca_scan(execute, url, targets):
    cmd = ["akca", "-u", url or ""]
    desc = " ".join(cmd)
    if not kali_bot.target_allowed(_host_of(url), targets):
        return desc, "REFUSED"
    if not execute:
        return desc, None
    binary = shutil.which("akca")
    if not binary:
        return desc, {"error": ("akca binary not installed on this machine. "
                                "Vetted source is staged in the sandbox at "
                                f"{os.path.join(tools_dir(), 'akca')} "
                                "(build with Go 1.25+). Nothing was run.")}
    # Authorized execute against an allow-listed target: real network kept,
    # but cwd + environment are sandboxed (sandbox.py).
    run = sandbox.run_sandboxed(
        [binary, "-u", url], cwd=os.path.join(tools_dir(), "akca"),
        timeout=900, network="allowlisted")
    if "error" in run:
        return desc, {"error": f"akca failed: {run['error']}",
                      "sandbox": run["sandbox"]}
    return desc, {"target": url, "returncode": run["returncode"],
                  "stdout_tail": run["stdout_tail"],
                  "stderr_tail": run["stderr_tail"],
                  "sandbox": run["sandbox"]}


def tool_omnisci3nt_recon(execute, target, targets):
    cmd = ["python3", "-m", "omnisci3nt.omnisci3nt", "-all", target or ""]
    desc = " ".join(cmd) + f"  (cwd: {os.path.join(tools_dir(), 'omnisci3nt')})"
    if not kali_bot.target_allowed(target, targets):
        return desc, "REFUSED"
    if not execute:
        return desc, None
    root = os.path.join(tools_dir(), "omnisci3nt")
    if not os.path.isdir(os.path.join(root, "omnisci3nt")):
        return desc, {"error": ("omnisci3nt source not staged in the sandbox "
                                f"at {root}. Nothing was run.")}
    # Authorized execute against an allow-listed target, run in place inside
    # the sandbox with a scrubbed environment (sandbox.py).
    run = sandbox.run_sandboxed(cmd, cwd=root, timeout=900,
                                network="allowlisted")
    if "error" in run:
        return desc, {"error": f"omnisci3nt failed: {run['error']}",
                      "sandbox": run["sandbox"]}
    return desc, {"target": target, "returncode": run["returncode"],
                  "stdout_tail": run["stdout_tail"],
                  "stderr_tail": run["stderr_tail"],
                  "sandbox": run["sandbox"]}


def tool_wifit3_audit(execute, target, targets):
    desc = (f"wifit3 (interactive TUI) scoped to BSSID/SSID '{target}' — "
            "manual bench run only; staged in the sandbox at "
            f"{os.path.join(tools_dir(), 'wifit3')}")
    if not kali_bot.target_allowed(target, targets):
        return desc, "REFUSED"
    if not execute:
        return desc, None
    # Gate passed and audited, but the harness never launches wifit3: it is
    # an interactive TUI that needs root and a supported USB Wi-Fi adapter.
    return desc, "MANUAL_ONLY"


# ------------------------------------------------------------------ dispatch

def run_tool(tool, args=None, execute=False):
    """Run (or dry-run) one vetted tool wrapper. Always audit-logged.
    Returns a result dict; refusals carry refused=True and a reason.
    Shape mirrors kali_bot.run_action."""
    args = args or {}
    base = {"action": tool, "args": args,
            "mode": "execute" if execute else "dry-run"}

    stop = kali_bot.kill_switch_on()
    if stop:
        out = dict(base, ok=False, refused=True,
                   reason=f"kill switch active: {stop}")
        kali_bot.audit(out)
        return out

    if tool not in TOOLS:
        out = dict(base, ok=False, refused=True,
                   reason=(f"unknown tool '{tool}' — only statically vetted "
                           "Dayofexploits PASS tools are registered "
                           "(see DAYOFEXPLOITS-VETTING.md)"))
        kali_bot.audit(out)
        return out

    targets = kali_bot.load_targets(kali_bot.TARGETS_PATH)
    if tool == "akca_scan":
        gate_value = args.get("url") or args.get("target")
    else:  # omnisci3nt_recon, wifit3_audit
        gate_value = args.get("target")

    # LIVE-APPROVAL GATE — exploit-class tools, execute mode only.
    # Boss's law (2026-10-21): "Nothing live unless I approve." No
    # valid per-run token -> refused here, BEFORE the tool function
    # (and its sandbox / not-installed logic) is ever reached. Dry-run
    # never reaches this block and needs no token.
    if execute and tool in EXPLOIT_CLASS_TOOLS:
        ok, why = approval.check(tool, gate_value)
        if not ok:
            out = dict(base, ok=False, refused=True, would_run=None,
                       gate="LIVE_EXECUTION_REFUSED", approval_reason=why,
                       reason=("live execution refused — nothing runs "
                               "live without the Boss's per-run approval "
                               f"({why}). A token is minted only by "
                               "approve_live.py on his explicit word; "
                               "dry-run needs no approval."))
            kali_bot.audit(out)
            return out

    if tool == "akca_scan":
        desc, res = tool_akca_scan(execute, gate_value, targets)
    elif tool == "omnisci3nt_recon":
        desc, res = tool_omnisci3nt_recon(execute, gate_value, targets)
    else:  # wifit3_audit
        desc, res = tool_wifit3_audit(execute, gate_value, targets)

    if res == "REFUSED":
        out = dict(base, ok=False, refused=True, would_run=None,
                   reason=(f"target '{gate_value}' is NOT in the allow-list "
                           f"({kali_bot.TARGETS_PATH}). Owner's own machines "
                           "/ authorized labs only. Refused."))
        kali_bot.audit(out)
        return out
    if res == "MANUAL_ONLY":
        out = dict(base, ok=False, refused=True, would_run=desc,
                   reason=("wifit3 is an interactive TUI requiring root and "
                           "a supported USB Wi-Fi adapter; the harness gates "
                           "and audits the target but does not launch it. Run "
                           "wifit3 manually on the bench box from its "
                           "sandboxed staging at "
                           f"{os.path.join(tools_dir(), 'wifit3')} against "
                           "this same allow-listed BSSID/SSID. Live bench "
                           "runs also need the Boss present in person, plus "
                           "his approval for that run."))
        kali_bot.audit(out)
        return out

    # Record the sandbox posture in the audit trail: for an executed run,
    # the layers actually used ride in the result; for a dry-run nothing
    # executed, so record the plan (root + layers that would apply).
    if isinstance(res, dict) and "sandbox" in res:
        sb = res["sandbox"]
    else:
        sb = {"root": sandbox.sandbox_root(), "executed": False,
              "network": ("n/a — dry-run, nothing executed" if not execute
                          else "n/a — nothing executed (tool not staged)"),
              "layers_if_executed": sandbox.planned_layers("allowlisted")}
    out = dict(base, ok=True, would_run=desc, result=res, sandbox=sb)
    kali_bot.audit(out)
    return out


def main():
    p = argparse.ArgumentParser(
        description="Fleet Tools — vetted Dayofexploits wrappers, allow-listed, own-machines-only")
    p.add_argument("tool", choices=TOOLS)
    p.add_argument("--target", default=None,
                   help="recon/audit target (must be allow-listed)")
    p.add_argument("--url", default=None, help="akca_scan: target URL (host must be allow-listed)")
    p.add_argument("-Execute", action="store_true",
                   help="actually run the tool (default: dry-run)")
    a = p.parse_args()
    args = {}
    if a.target:
        args["target"] = a.target
    if a.url:
        args["url"] = a.url
    out = run_tool(a.tool, args, execute=a.Execute)
    if out.get("refused"):
        print(f"REFUSED: {out['reason']}")
        return 2
    if not a.Execute:
        print(f"DRY-RUN: would run: {out['would_run']}")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
