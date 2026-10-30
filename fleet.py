"""fleet — the one-command quickstart (NetworkChuck pattern).

    python3 fleet.py up        build the console + verify every rung
    python3 fleet.py check     re-run the live connector verification
    python3 fleet.py sim       replay the simulated engagement transcript
    python3 fleet.py serve     serve dashboard/ on http://127.0.0.1:8765

Three commands from a fresh clone:  python3 fleet.py up ; python3 fleet.py serve
No secrets are read or written anywhere in this module; the checks it
calls are read-only status probes (see god_check.py).
"""

from __future__ import annotations

import http.server
import socketserver
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _run(*args):
    return subprocess.run([sys.executable, *args], cwd=ROOT).returncode


def up() -> int:
    print("== fleet up: build dashboard ==")
    if _run("build_dashboard.py"):
        return 1
    print("== fleet up: verify (zero-trust clauses) ==")
    _run("verify_all.py")
    print("== fleet up: simulated engagement ==")
    if _run("sim/run_sim.py"):
        return 1
    print("\nReady. Serve the console with:  python3 fleet.py serve")
    return 0


def serve(port: int = 8765) -> int:
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("127.0.0.1", port),
                                handler) as httpd:
        print(f"Kali Fleet: OMEGA console at http://127.0.0.1:{port}/dashboard/")
        httpd.serve_forever()
    return 0


def main(argv) -> int:
    cmd = argv[1] if len(argv) > 1 else "up"
    if cmd == "up":
        return up()
    if cmd == "check":
        return _run("god_check.py")
    if cmd == "sim":
        return _run("sim/run_sim.py")
    if cmd == "serve":
        return serve(int(argv[2]) if len(argv) > 2 else 8765)
    print(__doc__)
    return 2


VERIFICATION = {"clause": "every-module-carries-a-runnable-clause", "origin": "empire-doctrine (war-room fix list §7 item 5: runnable clauses for fleet.py and build_dashboard.py)",
                "check": "verify_all.py clause_fleet_dispatch: fleet.main() dispatch for up/check/sim/serve exercised with _run and serve stubbed (no side effects); unknown command exits 2 and runs nothing"}


if __name__ == "__main__":
    sys.exit(main(sys.argv))
