# Kali Fleet — pinned container for the demo + test suite.
#
# Base image pinned by exact tag to the audited runtime (Python 3.12.3,
# see .python-version and STACK-AUDIT-2026-10-26.md).
# Zero pip installs: the fleet is standard-library only (requirements.txt
# is explicit-empty; DEPENDENCIES.md states the lock policy).
#
# Default run: smoke tests, then the one-shot demo — both fully offline
# in MOCK mode (no TOKEN_FACTORY_API_KEY). To run live, pass the key at
# run time only:  docker run --rm -e TOKEN_FACTORY_API_KEY=... kali-fleet
# Never bake a key into the image.
#
# Note: execute mode (-Execute) shells out to host tools (ss, ip, nmap,
# unshare) that are intentionally NOT in this slim image; the shipped
# demo path is dry-run/mock and never spawns them.

FROM python:3.12.3-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Whole repo (minus .dockerignore: __pycache__, audit_log.jsonl,
# approvals/, STOP.txt, audit docs). Every path the code opens at
# runtime (fleet_targets.txt, demo/) is inside this copy.
COPY . /app

# No dependencies to install — requirements.txt documents the empty lock.
# Kept as a no-op marker so the policy is visible in the build:
#   pip install -r requirements.txt  →  installs nothing, by design.

CMD ["sh", "-c", "python3 test_smoke.py && python3 demo.py --once"]
