# Kali Fleet — Dependency Lock Policy

Locked 2026-10-26. Evidence: `STACK-AUDIT-2026-10-26.md` in the parent kali-fleet tree (the audit predates this fusion tree; it is not duplicated here).

## The lock

| Layer | Locked value | Where |
|---|---|---|
| Python runtime | **3.12.3** exactly | `.python-version`, `Dockerfile` base image |
| Third-party Python packages | **None. Zero** for the base system; the optional quantum extra is pinned separately | `requirements.txt` (explicit-empty) + `requirements-quantum.txt` |
| Container base image | `python:3.12.3-slim-bookworm` (exact tag) | `Dockerfile` |

## Why zero packages is a real lock, not a missing file

Every import in every `.py` file was inventoried with an AST walk and
checked against Python 3.12's `sys.stdlib_module_names`. For the base
system the complete non-local import set is: `argparse, datetime,
ipaddress, json, os, platform, re, shutil, socket, subprocess, sys,
tempfile, time, unittest, urllib` — all standard library. Local imports
are this repo's own modules only. There are no dynamic imports
(`__import__`, `importlib`, `eval`, `exec`) anywhere in the tree.

**One scoped exception (added 2026-10-30, war-room fix):**
`quantum_router.py` — the optional QAOA route-scoring module — imports
`numpy`, `scipy`, `qiskit`, and `qiskit_aer`. Those packages are NOT
part of the base lock: they are pinned exactly in
`requirements-quantum.txt` (versions taken from the verified build
venv), and nothing else in the tree imports them. The base system —
including god_router's quantum hook, which reads the module's results
file and degrades to classical scoring without it — stays at zero
third-party packages.

**Policy:** if a future change adds a third-party import, it must land
in `requirements.txt` pinned to an exact version (`name==X.Y.Z`) in
the same change, and this file + the stack audit must be updated.
An unpinned or unlisted dependency is a build failure by policy.

## The one real external dependency: an API, not a package

**Nebius Token Factory** (OpenAI-compatible chat completions) is the
fleet's only external service dependency.

- Client: `token_factory.py` (stdlib `urllib` only).
- Endpoint: `POST {TOKEN_FACTORY_BASE_URL}/chat/completions`,
  default base `https://api.tokenfactory.nebius.com/v1`.
- Auth: `TOKEN_FACTORY_API_KEY` from the environment only.
- Model IDs: environment-configured (`TF_MODEL_FAST` / `TF_MODEL_PLAN`
  / `TF_MODEL_DEEP`). The built-in defaults are **placeholders** in
  vendor/model style — they must be verified against the Token Factory
  catalog when a key is provisioned. This is the one dependency whose
  "version" (the model identifiers) cannot be locked until the owner
  provisions the key; it is locked by configuration, not by code.
- Absent key = offline **MOCK mode**: no network calls, every payload
  labeled `"mock": true` with `mock/`-prefixed model names. The full
  demo and all tests run in this mode.

## System (non-Python) dependencies — execute mode only

The demo, mock mode, and all tests need nothing beyond Python. Actually
*executing* actions (`-Execute`) shells out to host tools:

| Binary | Used by | Needed for |
|---|---|---|
| `ss` (iproute2) | `listening_ports` | execute mode |
| `ip` (iproute2) | `interfaces` | execute mode |
| `nmap` | `nmap_scan` | execute mode, allow-listed targets only |
| `unshare` (util-linux) | `sandbox.py` | network-namespace isolation layer; absence degrades to env+cwd sandboxing and is recorded in the audit entry |

These are host prerequisites (see the audit's PREREQUISITES section),
not container contents: the shipped container runs the demo in
dry-run/mock mode, which never spawns them.

## Fleet-tools tree (outside this repo)

`fleet_tools.py` execute mode runs vetted tool clones from an external
tree — `~/workspace/empire/work/crew-stack-bundle/sandbox/tools/`
(override: `FLEET_TOOLS_DIR` / `FLEET_SANDBOX_DIR`). That tree is
deliberately **not** part of this repo or the container image; the
container covers the core copilot loop (parse → gate → dry-run →
narrate → audit) and the full test suite.
