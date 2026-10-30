#!/usr/bin/env python3
"""
God Check — states are CHECKED, not asserted (Kali Fleet: OMEGA).

The Boss's order (2026-10-30): "Take all off paper. No more paper."
So the registry's claims get re-verified at runtime, on this machine,
with the connectors' own status surfaces:

  * CLI probes (real subprocess calls, results cached 5 minutes):
    github / notion-cli / stripe / vercel / linear `status`,
    facebook-cli `me`, hatch_messenger_cli `check`,
    hatch_gws_cli Gmail profile read (the Google Workspace connector —
    one auth covers Gmail/Calendar/Drive), tailscale `status`.
    A probe that returns the connector's authenticated shape =>
    checked_state LIVE, with the evidence string recorded.
  * Key probes (presence only — values are NEVER read): a key-based
    connector whose env var is absent on this machine is
    KEY-PENDING, and the row names the exact missing input and its
    route in (Secure Vault). Present => the registry state is left to
    speak (presence is not proof of validity — a stored Zen key
    returned 401; only a live call proves a key, and god_check does
    not spend calls).
  * Door probes: the PC door family is DOOR-PENDING until SSH auth
    succeeds from this machine; the transport facts on record are
    stated, not upgraded.
  * Everything else: REGISTRY — not probeable from this VM; the
    registry state from the connection map is shown as-is.

Output shape (the dashboard's data source):
  {"checked_at": "...", "rows": [{"name", "registry_state",
   "checked_state", "detail", "missing_input"}]}

Stdlib only. Probes have hard timeouts; a hung connector degrades its
own row to CHECK-FAILED, never the whole table.
"""

import json
import os
import subprocess
import tempfile
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import connector_registry

CACHE_PATH = os.environ.get("OMEGA_GODCHECK_CACHE") or os.path.join(
    tempfile.gettempdir(), "omega_god_check_cache.json")  # outside the tree:
    # a cache inside the tree being verified would let a planted file
    # freeze the verifier's eyes (war-room finding, 2026-10-30)
CACHE_TTL = 300
PROBE_TIMEOUT = 30

BIN = "/opt/hatch/bin"


def _run(argv):
    try:
        out = subprocess.run(argv, capture_output=True, text=True,
                             timeout=PROBE_TIMEOUT)
        return out.returncode, (out.stdout or "") + (out.stderr or "")
    except (OSError, subprocess.SubprocessError) as e:
        return None, f"probe failed to run: {e}"


def _auth_json_ok(text):
    """The hatch MCP connectors answer status with a JSON object whose
    auth_status is 'connected' / authenticated is true. The output may
    carry trailing log lines — parse the first JSON object found."""
    start = text.find("{")
    if start < 0:
        return False, "no JSON in probe output"
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    except ValueError:
        return False, "unparseable probe output"
    if obj.get("auth_status") == "connected" or obj.get("authenticated") is True:
        return True, f"auth_status=connected ({obj.get('provider', 'connector')})"
    return False, f"auth_status={obj.get('auth_status')!r}"


def _probe_cli(argv, kind):
    rc, text = _run(argv)
    if kind == "auth-json":
        ok, why = _auth_json_ok(text)
        return ok, why
    if kind == "facebook-me":
        ok = '"fb_user_id"' in text
        return ok, "profile returned for the connected account" if ok else "no profile in output"
    if kind == "messenger-check":
        ok = '"success":true' in text.replace(" ", "")
        return ok, "messenger check success" if ok else "messenger check did not confirm"
    if kind == "gmail-profile":
        ok = '"emailAddress"' in text
        return ok, "Gmail profile read answered (Workspace auth live)" if ok else "profile read did not answer"
    if kind == "tailscale":
        ok = text.strip().startswith("Connected")
        return ok, "tailnet Connected (enrolled; per-connector doc: connected != machine reachability)" if ok else "tailscale did not report Connected"
    return False, f"unknown probe kind {kind}"


# name -> (argv, kind)
CLI_PROBES = {
    "GitHub": ([f"{BIN}/github", "status"], "auth-json"),
    "Notion": ([f"{BIN}/notion-cli", "status"], "auth-json"),
    "Stripe": ([f"{BIN}/stripe", "status"], "auth-json"),
    "Vercel": ([f"{BIN}/vercel", "status"], "auth-json"),
    "Linear": ([f"{BIN}/linear", "status"], "auth-json"),
    "Facebook": ([f"{BIN}/facebook-cli", "me"], "facebook-me"),
    "Messenger": ([f"{BIN}/hatch_messenger_cli", "check"], "messenger-check"),
    "Gmail": ([f"{BIN}/hatch_gws_cli", "gmail", "users", "getProfile",
               "--params", '{"userId":"me"}'], "gmail-profile"),
    "Tailscale": ([f"{BIN}/tailscale", "status"], "tailscale"),
}
# Calendar/Drive ride the same Google Workspace auth the Gmail probe proves.
WORKSPACE_RIDERS = {"Google Calendar": "Gmail", "Google Docs": "Gmail",
                    "Google Drive": "Gmail"}

# name -> ([env vars any-of], exact missing input description)
KEY_PROBES = {
    "OpenRouter": (["OPENROUTER_API_KEY"],
                   "OPENROUTER_API_KEY — deposit via Secure Vault"),
    "Nebius Token Factory": (["NEBIUS_API_KEY", "TOKEN_FACTORY_API_KEY"],
                             "Token Factory key — deposit via Secure Vault"),
    "Hugging Face": (["HF_TOKEN"], "HF_TOKEN — deposit via Secure Vault"),
    "Supabase": (["SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ANON_KEY"],
                 "service_role key via Secure Vault + local connector build"),
    "Manus": (["MANUS_API_KEY"], "MANUS_API_KEY via Secure Vault + a job assignment"),
    "Jev rung (a) typesafe": (["TYPESAFE_API_KEY"],
                              "TYPESAFE_API_KEY — owner account + key via Secure Vault"),
    "Jev rung (b) openrouter-decisions": (["OPENROUTER_API_KEY"],
                                          "OPENROUTER_API_KEY via Secure Vault"),
    "Jev rung (b2) opencode-zen": (["OPENCODE_ZEN_API_KEY"],
                                   "fresh Zen key — the vault-held one returns 401; mint + deposit via the vault capture link"),
    "Jev rung (c) openrouter-llm": (["OPENROUTER_API_KEY"],
                                    "OPENROUTER_API_KEY via Secure Vault"),
    "Hostinger": (["HOSTINGER_API_TOKEN"],
                  "HOSTINGER_API_TOKEN via Secure Vault (API client only; the account itself is live)"),
    "Telegram (crew bridge)": (["TELEGRAM_BOT_TOKEN", "BOTFATHER_TOKEN"],
                               "BotFather token via Secure Vault"),
    "crew_llm fleet brains": (["OPENROUTER_API_KEY"],
                              "OPENROUTER_API_KEY via Secure Vault (fleet currently executes in simulation)"),
}

DOOR_PENDING = {
    "PC door (SSH to DESKTOP-0RGKS6P)":
        "the elevated key-install paste on the PC (administrators_authorized_keys) + its read-back output",
    "Hermes (PC agent)": "the PC door, then read-only recon",
    "Ollama hermes3:8b (PC)":
        "the PC door for agent-level access (inference endpoint answered via the tailnet 2026-10-30; SSH auth unverified)",
}


def _cache_read():
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            cache = json.load(f)
        if time.time() - cache.get("at", 0) <= CACHE_TTL:
            return cache.get("probes", {})
    except (OSError, ValueError):
        pass
    return {}


def _cache_write(probes):
    try:
        tmp = CACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"at": time.time(), "probes": probes}, f)
        os.replace(tmp, CACHE_PATH)
    except OSError:
        pass


def probe_all(use_cache=True):
    """Run every CLI probe once (cached 5 min). Returns {name: (ok, why)}."""
    if use_cache:
        cached = _cache_read()
        if cached:
            return {k: tuple(v) for k, v in cached.items()}
    results = {}
    for name, (argv, kind) in CLI_PROBES.items():
        results[name] = _probe_cli(argv, kind)
    _cache_write({k: list(v) for k, v in results.items()})
    return results


def classify(entry, probes, env=None):
    """One registry entry -> its checked row. Pure apart from the probe
    table passed in, so tests classify from REAL probe results."""
    env = os.environ if env is None else env
    name = entry["name"]
    row = {"name": name, "registry_state": entry["state"],
           "checked_state": None, "detail": "", "missing_input": None}

    if name in CLI_PROBES:
        ok, why = probes.get(name, (False, "probe not run"))
        row["checked_state"] = "LIVE" if ok else "CHECK-FAILED"
        row["detail"] = f"probe {CLI_PROBES[name][0][0].split('/')[-1]}: {why}"
        return row
    if name in WORKSPACE_RIDERS:
        ok, why = probes.get(WORKSPACE_RIDERS[name], (False, "probe not run"))
        row["checked_state"] = "LIVE" if ok else "CHECK-FAILED"
        row["detail"] = f"rides the Google Workspace auth proven by the Gmail probe: {why}"
        return row
    if name in KEY_PROBES:
        vars_, missing = KEY_PROBES[name]
        present = [v for v in vars_ if env.get(v)]
        if present:
            row["checked_state"] = entry["state"]
            row["detail"] = (f"{present[0]} present in env (presence only — "
                             f"validity needs a live call, not made here)")
        else:
            row["checked_state"] = "KEY-PENDING"
            row["detail"] = "credential physically absent on this machine"
            row["missing_input"] = missing
        return row
    if name in DOOR_PENDING:
        row["checked_state"] = "DOOR-PENDING"
        row["detail"] = "transport facts on record; SSH auth never achieved from this VM"
        row["missing_input"] = DOOR_PENDING[name]
        return row
    row["checked_state"] = "REGISTRY"
    row["detail"] = "not probeable from this VM — registry state (connection map, 2026-10-30) shown as-is"
    if entry["state"] != "LIVE":
        row["missing_input"] = entry.get("unblock")
    return row


def check(use_cache=True):
    data = connector_registry.load()
    probes = probe_all(use_cache=use_cache)
    rows = [classify(c, probes) for c in data["connectors"]]
    return {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "source": "god_check.py — connector CLI status probes + env presence (values never read)",
            "rows": rows,
            "identity_assets": data["identity_assets"]}


def print_table(report):
    print(f"GOD CHECK — {report['checked_at']} (states CHECKED on this machine)")
    print(f"{'connector':44} {'registry':16} {'checked':14} detail")
    for r in report["rows"]:
        print(f"{r['name'][:43]:44} {r['registry_state']:16} "
              f"{r['checked_state']:14} {r['detail']}"
              + (f" | MISSING: {r['missing_input']}" if r["missing_input"] else ""))


if __name__ == "__main__":
    rep = check(use_cache="--fresh" not in sys.argv)
    if "--json" in sys.argv:
        print(json.dumps(rep, indent=2))
    else:
        print_table(rep)


# Zero-Trust Verification Layer — this module's clause.
VERIFICATION = {'clause': 'prove-it-on-screen', 'origin': 'networkchuck-adjacent (Pattern 3: monitor the watchers)', 'check': "its own probes: connector CLIs' status surfaces, run live (cached 5 min); test_omega.py classifies GitHub LIVE from a real probe"}
