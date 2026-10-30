#!/usr/bin/env python3
"""
Kali Bot — the Empire's Kali Linux security agent (Kali Fleet).

SCOPE — STRICT: the owner's OWN machines and AUTHORIZED LABS ONLY (the God
of Goats brand rule). This bot can only ever:
  sysinfo          OS / kernel / hostname (stdlib, read-only)
  listening_ports  parse of `ss -tlnp` (read-only)
  interfaces       parse of `ip -brief addr` (read-only)
  log_triage       error/warning counts + samples from a user-supplied log
  nmap_scan        nmap -sV service detection — ONLY against targets listed
                   in fleet_targets.txt next to this script. Anything else is
                   REFUSED. No exceptions, no overrides in code.

There are NO exploit payloads, NO credential attacks, NO brute forcing, and
nothing in this file points at third parties.

MODES: dry-run is the default — the bot prints the command it WOULD run and
does nothing. -Execute (or execute=True) actually runs the allow-listed
read-only command.

SAFETY SWITCHES:
  - Kill switch: env FLEET_STOP=1, or a STOP.txt file next to this script,
    refuses ALL actions.
  - Every attempted action (allowed, refused, dry-run, executed) is appended
    to a JSONL audit log (default: audit_log.jsonl next to this script;
    override with env FLEET_AUDIT_LOG).

Stdlib only. Runs on Kali Linux (and any Linux with ss/ip for those actions).
"""

import argparse
import json
import os
import platform
import re
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS_PATH = os.path.join(HERE, "fleet_targets.txt")
STOP_PATH = os.path.join(HERE, "STOP.txt")
DEFAULT_AUDIT = os.path.join(HERE, "audit_log.jsonl")

ACTIONS = ("sysinfo", "listening_ports", "interfaces", "log_triage", "nmap_scan")


# ------------------------------------------------------------------ safety

def kill_switch_on():
    if os.environ.get("FLEET_STOP") == "1":
        return "FLEET_STOP=1 set in environment"
    if os.path.exists(STOP_PATH):
        return "STOP.txt present next to kali_bot.py"
    return None


def load_targets(path=TARGETS_PATH):
    targets = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    targets.append(line)
    except OSError:
        return []
    return targets


def target_allowed(target, targets):
    """Exact match, or target is an IP inside an allow-listed CIDR entry."""
    if not target:
        return False
    for entry in targets:
        if target == entry:
            return True
        if "/" in entry:
            try:
                import ipaddress
                net = ipaddress.ip_network(entry, strict=False)
                if ipaddress.ip_address(target) in net:
                    return True
            except ValueError:
                continue
    return False


def audit(entry):
    path = os.environ.get("FLEET_AUDIT_LOG") or DEFAULT_AUDIT
    entry = dict(entry)
    entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass  # audit failure must not crash the bot; actions are read-only


# ------------------------------------------------------------------ actions
# Each returns (would_run_description, result_dict_or_None_when_executed).
# In dry-run mode result is None and only the description is reported.

def act_sysinfo(execute):
    desc = "stdlib platform/socket read: uname, hostname, python version"
    if not execute:
        return desc, None
    u = platform.uname()
    return desc, {"hostname": socket.gethostname(), "system": u.system,
                  "release": u.release, "machine": u.machine,
                  "python": platform.python_version()}


def act_listening_ports(execute):
    cmd = ["ss", "-tlnp"]
    desc = " ".join(cmd)
    if not execute:
        return desc, None
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        return desc, {"error": f"ss failed: {e}"}
    listeners = []
    for line in out.stdout.splitlines():
        parts = line.split()
        # ss column layout varies by build (Netid-first vs State-first);
        # skip headers and pick the first address:port-shaped token.
        if not parts or parts[0] in ("State", "Netid"):
            continue
        local = next((p for p in parts if ":" in p), "")
        if local:
            listeners.append({"local": local,
                                "state": "LISTEN" if "LISTEN" in parts else parts[0]})
    return desc, {"count": len(listeners), "listening": listeners[:100]}


def act_interfaces(execute):
    cmd = ["ip", "-brief", "addr"]
    desc = " ".join(cmd)
    if not execute:
        return desc, None
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        return desc, {"error": f"ip failed: {e}"}
    ifaces = []
    for line in out.stdout.splitlines():
        parts = line.split()
        if parts:
            ifaces.append({"name": parts[0],
                           "state": parts[1] if len(parts) > 1 else "",
                           "addresses": parts[2:]})
    return desc, {"count": len(ifaces), "interfaces": ifaces}


_LOG_LEVELS = ("error", "err", "fail", "critical", "warn", "denied", "refused")


def act_log_triage(execute, path):
    desc = f"read and triage log file: {path}"
    if not execute:
        return desc, None
    if not path or not os.path.isfile(path):
        return desc, {"error": f"log file not found: {path}"}
    counts = {lvl: 0 for lvl in _LOG_LEVELS}
    samples = []
    total = 0
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                total += 1
                low = line.lower()
                hit = next((lvl for lvl in _LOG_LEVELS if lvl in low), None)
                if hit:
                    counts[hit] += 1
                    if len(samples) < 10:
                        samples.append(line.strip()[:200])
    except OSError as e:
        return desc, {"error": str(e)}
    return desc, {"file": path, "lines": total, "flag_counts": counts,
                  "samples": samples}


def act_nmap_scan(execute, target, targets):
    cmd = ["nmap", "-sV", "--top-ports", "100", target or ""]
    desc = " ".join(cmd)
    if not target_allowed(target, targets):
        return desc, "REFUSED"
    if not execute:
        return desc, None
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        return desc, {"error": "nmap not installed on this machine"}
    except (OSError, subprocess.SubprocessError) as e:
        return desc, {"error": f"nmap failed: {e}"}
    services = []
    for line in out.stdout.splitlines():
        m = re.match(r"^(\d+)/(tcp|udp)\s+(\S+)\s+(.*)$", line.strip())
        if m:
            services.append({"port": int(m.group(1)), "proto": m.group(2),
                             "state": m.group(3), "service": m.group(4).strip()})
    return desc, {"target": target, "services_found": len(services),
                  "services": services[:100]}


# ------------------------------------------------------------------ dispatch

def run_action(action, args=None, execute=False):
    """Run (or dry-run) one allow-listed action. Always audit-logged.
    Returns a result dict; refusals carry refused=True and a reason."""
    args = args or {}
    base = {"action": action, "args": args,
            "mode": "execute" if execute else "dry-run"}

    stop = kill_switch_on()
    if stop:
        out = dict(base, ok=False, refused=True,
                   reason=f"kill switch active: {stop}")
        audit(out)
        return out

    if action not in ACTIONS:
        out = dict(base, ok=False, refused=True,
                   reason=f"unknown action '{action}' — allow-list only")
        audit(out)
        return out

    targets = load_targets()
    if action == "nmap_scan":
        desc, res = act_nmap_scan(execute, args.get("target"), targets)
        if res == "REFUSED":
            out = dict(base, ok=False, refused=True, would_run=None,
                       reason=(f"target '{args.get('target')}' is NOT in the "
                               f"allow-list ({TARGETS_PATH}). Owner's own "
                               "machines / authorized labs only. Refused."))
            audit(out)
            return out
    elif action == "sysinfo":
        desc, res = act_sysinfo(execute)
    elif action == "listening_ports":
        desc, res = act_listening_ports(execute)
    elif action == "interfaces":
        desc, res = act_interfaces(execute)
    else:  # log_triage
        desc, res = act_log_triage(execute, args.get("path"))

    out = dict(base, ok=True, would_run=desc, result=res)
    audit(out)
    return out


def main():
    p = argparse.ArgumentParser(description="Kali Bot — allow-listed, own-machines-only security agent")
    p.add_argument("action", choices=ACTIONS)
    p.add_argument("--target", default=None, help="nmap_scan target (must be allow-listed)")
    p.add_argument("--log-file", default=None, help="log_triage: path to a log file")
    p.add_argument("-Execute", action="store_true",
                   help="actually run the read-only command (default: dry-run)")
    a = p.parse_args()
    args = {}
    if a.target:
        args["target"] = a.target
    if a.log_file:
        args["path"] = a.log_file
    out = run_action(a.action, args, execute=a.Execute)
    if out.get("refused"):
        print(f"REFUSED: {out['reason']}")
        return 2
    if not a.Execute:
        print(f"DRY-RUN: would run: {out['would_run']}")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
