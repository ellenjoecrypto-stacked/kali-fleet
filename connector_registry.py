#!/usr/bin/env python3
"""
Connector Registry — the God System's phone book (Kali Fleet: OMEGA).

Every Empire connector / integration / brain / identity asset, in one
validated registry. Data lives in connectors.json next to this file,
hand-authored from the verified connection map
(empire/work/crew-jobs/CONNECTION-MAP.md, 2026-10-30). States are copied
truthfully from that map — LIVE / WIRED-NOT-FUELED / PAPER / BLOCKED /
EMPTY / UNVERIFIED / NAMED-IN-RECORD / OUT. (NAMED-IN-RECORD, added
2026-10-30 with the connector-universe merge: the service is named in
Marke's record and nothing more — never attempted, nothing probed or
built; distinct from UNVERIFIED, where a surface exists.) Nothing here
invents a connector, a state, or a capability.

Identity assets (soul contracts) are NAME + STATUS + PATH ONLY. HARD
LAW (Boss, 2026-10-29): soul-contract CONTENTS never enter any repo,
snapshot, or submission — not even a private one. An identity entry
carries exactly three keys — member, status, pointer — and load()
REJECTS an entry carrying anything else (war-room fix, 2026-10-30:
the earlier ban-list missed the file's own `contents` field and the
`role` prose field; both shipped. Exact-key enforcement replaces the
ban-list.)

Stdlib only.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REGISTRY_PATH = os.path.join(HERE, "connectors.json")

STATES = ("LIVE", "WIRED-NOT-FUELED", "PAPER", "BLOCKED", "EMPTY",
          "UNVERIFIED", "NAMED-IN-RECORD", "OUT")
GATES = ("none", "approval", "boss-hands", "vault")
TRANSPORTS = ("connector", "api", "mcp", "browser", "local")
# An identity asset may carry EXACTLY these keys — name, status, path.
# Anything else (content, contents, role, text, ...) fails the load.
IDENTITY_KEYS = ("member", "status", "pointer")
FORBIDDEN_IDENTITY_FIELDS = ("text", "content", "contents", "body",
                             "contract_text", "soul", "markdown",
                             "excerpt", "summary_text", "role")


class RegistryError(ValueError):
    pass


def load(path=None):
    """Load + validate the registry. Raises RegistryError on any entry
    that breaks the schema or the soul-content law."""
    path = path or os.environ.get("OMEGA_REGISTRY") or DEFAULT_REGISTRY_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    seen_names = set()
    for entry in data.get("connectors", []):
        key = str(entry.get("name", "")).strip().lower()
        if key in seen_names:
            raise RegistryError(
                f"duplicate connector name {entry.get('name')!r} — names "
                f"bind approval tokens and must be unique")
        seen_names.add(key)
        for field in ("name", "capabilities", "transport", "state", "gate"):
            if field not in entry:
                raise RegistryError(f"connector entry missing {field}: {entry!r}")
        if entry["state"] not in STATES:
            raise RegistryError(f"{entry['name']}: bad state {entry['state']!r}")
        if entry["gate"] not in GATES:
            raise RegistryError(f"{entry['name']}: bad gate {entry['gate']!r}")
        if entry["transport"] not in TRANSPORTS:
            raise RegistryError(f"{entry['name']}: bad transport {entry['transport']!r}")
        if not isinstance(entry["capabilities"], list) or not entry["capabilities"]:
            raise RegistryError(f"{entry['name']}: capabilities must be a non-empty list")
        if entry["state"] != "LIVE" and not entry.get("unblock"):
            raise RegistryError(
                f"{entry['name']}: non-LIVE entries must name their unblocking step")
    for asset in data.get("identity_assets", []):
        extra = [k for k in asset if k not in IDENTITY_KEYS]
        if extra:
            raise RegistryError(
                f"identity asset {asset.get('member')!r} carries field(s) "
                f"{extra} — identity entries are name + status + path ONLY "
                f"(soul-contract law); rejected at load")
        if "member" not in asset or "status" not in asset:
            raise RegistryError(f"identity asset missing member/status: {asset!r}")
    return data


def connectors(data=None):
    return (data if data is not None else load()).get("connectors", [])


def identity_assets(data=None):
    return (data if data is not None else load()).get("identity_assets", [])


def find_by_capability(capability, data=None):
    """All connectors offering a capability, best state first
    (LIVE > WIRED-NOT-FUELED > PAPER > BLOCKED > EMPTY > UNVERIFIED >
    NAMED-IN-RECORD > OUT)."""
    rank = {s: i for i, s in enumerate(
        ("LIVE", "WIRED-NOT-FUELED", "PAPER", "BLOCKED", "EMPTY",
         "UNVERIFIED", "NAMED-IN-RECORD", "OUT"))}
    want = str(capability).strip().lower()
    hits = [c for c in connectors(data)
            if want in [str(x).strip().lower() for x in c["capabilities"]]]
    return sorted(hits, key=lambda c: rank[c["state"]])


def summary(data=None):
    data = data if data is not None else load()
    counts = {}
    for c in data["connectors"]:
        counts[c["state"]] = counts.get(c["state"], 0) + 1
    return {"connectors": len(data["connectors"]),
            "by_state": counts,
            "identity_assets": len(data.get("identity_assets", [])),
            "identity_missing": [a["member"] for a in data.get("identity_assets", [])
                                 if a["status"].startswith("MISSING")]}


if __name__ == "__main__":
    print(json.dumps(summary(), indent=2))


# Zero-Trust Verification Layer — this module's clause.
VERIFICATION = {'clause': 'schema-or-reject', 'origin': 'networkchuck-adjacent (Pattern 2 stage 5: structured output)', 'check': 'test_omega.py: registry validates; identity entries carrying content, contents, or role fields are rejected at load (exact-key enforcement)'}
