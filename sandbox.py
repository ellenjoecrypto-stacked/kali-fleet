#!/usr/bin/env python3
"""
Sandbox — isolation layer for fleet tool execution (Kali Fleet).

WHY: the vetted Dayofexploits tool clones used to sit loose in the
crew-stack-bundle workspace, where akca's own test fixtures (intentionally
fake sample keys) tripped the Raga Sentinel leak scan. The Boss's answer
(2026-10-21): "Just sandbox them." The clones now live under
crew-stack-bundle/sandbox/tools/, and every tool subprocess the harness
spawns goes through this module.

LAYERS (each one is reported honestly — never claimed if inactive):
  1. cwd-in-sandbox — the child process starts inside the sandbox (its
     tool dir under sandbox/tools/, or sandbox/home/ by default).
  2. env-scrub — the child environment is BUILT FROM SCRATCH: only PATH
     (a fixed minimal value, not inherited), HOME=sandbox/home/,
     TMPDIR=sandbox/tmp/, LANG/LC_ALL. Nothing from the parent environment
     is inherited, so no API key, token, or credential in the harness's
     own environment can leak into a tool run.
  3. netns — network-namespace isolation via `unshare -n`, applied when
     the invocation is NOT an authorized execute against an allow-listed
     target (dry-run / recon-prep class work stays net-isolated). If
     unshare is missing or fails its probe, this layer DEGRADES: the run
     proceeds with layers 1+2 only and the metadata says so, loudly.

network modes:
  "isolated"    — netns applied when available (default).
  "allowlisted" — authorized execute against a fleet_targets.txt target:
                  real network kept (the scan target must be reachable),
                  layers 1+2 still apply.

This module changes NOTHING about the harness gates: allow-list, kill
switch, and dry-run default live in kali_bot.py / fleet_tools.py and are
checked before anything reaches run_sandboxed(). Stdlib only.
"""

import os
import shutil
import subprocess

DEFAULT_SANDBOX_ROOT = os.path.expanduser(
    "~/workspace/empire/work/crew-stack-bundle/sandbox")

# Fixed minimal PATH for children — deliberately NOT inherited, so a
# poisoned or credential-adjacent PATH in the parent cannot redirect
# tool lookups, and only system binary dirs are reachable.
MINIMAL_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

_netns_cache = None


def sandbox_root():
    return os.environ.get("FLEET_SANDBOX_DIR") or DEFAULT_SANDBOX_ROOT


def sandbox_paths():
    root = sandbox_root()
    return {"root": root,
            "tools": os.path.join(root, "tools"),
            "home": os.path.join(root, "home"),
            "tmp": os.path.join(root, "tmp")}


def ensure_sandbox():
    paths = sandbox_paths()
    for p in paths.values():
        os.makedirs(p, exist_ok=True)
    return paths


def tools_root():
    return sandbox_paths()["tools"]


def build_env():
    """The complete child environment, built from scratch. NOTHING is
    inherited from os.environ — that is the point of the scrub."""
    paths = ensure_sandbox()
    return {"PATH": MINIMAL_PATH,
            "HOME": paths["home"],
            "TMPDIR": paths["tmp"],
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8"}


def netns_available():
    """Probe once: unshare exists AND can actually create a net namespace
    on this machine. Cached; a failed probe is remembered, not retried."""
    global _netns_cache
    if _netns_cache is None:
        _netns_cache = False
        if shutil.which("unshare"):
            try:
                rc = subprocess.run(["unshare", "-n", "true"],
                                    capture_output=True, timeout=10).returncode
                _netns_cache = (rc == 0)
            except (OSError, subprocess.SubprocessError):
                _netns_cache = False
    return _netns_cache


def planned_layers(network="isolated"):
    """Layer names that a run with this network mode WOULD use, given
    what this machine actually supports. Used for dry-run audit entries,
    where nothing executes but the plan is recorded honestly."""
    layers = ["cwd-in-sandbox", "env-scrub"]
    if network == "isolated":
        layers.append("netns" if netns_available()
                      else "netns-DEGRADED(unavailable)")
    return layers


def run_sandboxed(cmd, cwd=None, timeout=900, network="isolated"):
    """Run cmd inside the sandbox. Always returns a dict:

      {"returncode": int|None, "stdout_tail": str, "stderr_tail": str,
       "sandbox": {root, cwd, network, layers, netns, degraded, notes}}
      — or {"error": str, "sandbox": {...}} if the spawn itself failed.

    cwd defaults to sandbox/home/; pass a tool's dir under sandbox/tools/
    to run it in place. network="allowlisted" skips netns (authorized
    execute against an allow-listed target); every other mode is
    net-isolated when unshare works, degraded-and-labeled when it doesn't.
    """
    paths = ensure_sandbox()
    workdir = cwd or paths["home"]
    layers = ["cwd-in-sandbox", "env-scrub"]
    notes = []
    degraded = False
    netns = False
    argv = list(cmd)
    if network == "isolated":
        if netns_available():
            argv = ["unshare", "-n"] + argv
            layers.append("netns")
            netns = True
        else:
            degraded = True
            layers.append("netns-DEGRADED")
            notes.append("unshare -n unavailable on this machine; network "
                         "isolation degraded to env+cwd only")
    else:  # allowlisted — authorized execute vs an allow-listed target
        layers.append("network:allow-listed-target")
    meta = {"root": paths["root"], "cwd": workdir, "network": network,
            "layers": layers, "netns": netns, "degraded": degraded,
            "notes": notes}
    try:
        out = subprocess.run(argv, cwd=workdir, env=build_env(),
                             capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return {"error": f"sandboxed run failed to spawn: {e}",
                "sandbox": meta}
    return {"returncode": out.returncode,
            "stdout_tail": out.stdout[-2000:],
            "stderr_tail": out.stderr[-500:],
            "sandbox": meta}
