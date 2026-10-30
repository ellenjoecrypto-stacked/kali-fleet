# DEVPOST SUBMISSION — KALI FLEET: OMEGA (v2 draft)

**Track:** Best Apps & Agents — Nebius × NVIDIA Global AI Hackathon 2026
**Repo:** [[REPO_URL]]
**Video:** https://www.youtube.com/watch?v=43hBiIRfjFM (Kali Fleet core;
recorded in labeled MOCK / DRY-RUN mode, disclosed on screen)

---

## The problem

Agent demos will run whatever a language model dreams up, on whatever
target it names, through whatever tools happen to be connected. For a
working operator — a repair-shop owner with a bench PC, a Kali box,
and customer-adjacent gear — that's not a copilot, it's a liability
with a chat box.

Kali Fleet inverted it: the model only *proposes*; a hard allow-list,
an owner-controlled target file, and a signed human approval gate
decide. OMEGA generalizes that discipline from one bot to the whole
connector estate: 68 connectors, brains, and crew seats behind one
registry, one router, and one verification layer that proves every
claimed state or demotes it in public.

## What we built

**Kali Fleet (core).** A plain-English security copilot for your own
machines: five read-only checks (sysinfo, listening ports, interfaces,
log triage, nmap service scan), targets restricted to an owner-edited
allow-list file, dry-run by default, a kill switch, and a JSONL audit
trail for every attempt. The intent brain is wired to **Nebius Token
Factory** with a three-tier Nemotron routing scheme (Nano-class parses,
Super-class plans/narrates, Ultra-class reserved for deep log
correlation).

**The Connector God System (OMEGA layer).**
- **Registry** — every connector/integration/brain the Empire runs,
  with capabilities, fuel state, gate, and the exact unblocking step
  for anything not live. Validated at load; duplicate names and
  schema breaks fail closed.
- **God Router** — capability routing disposed by *the Equation*: the
  Boss's standing law ported from our decision layer (three laws +
  a confidence policy over a typed question model). Unfueled routes
  BLOCK with the reason and the fix; gated actions stop at
  **HMAC-signed, single-use, 60-minute-capped approval tokens**; the
  most restrictive gate always wins, so an ungated duplicate can't
  shadow a gated route.
- **Zero-Trust Verification Layer** — `god_check` re-proves connector
  states at runtime with real CLI status probes (presence-only for
  keys; values never read) and the router *consumes* those checked
  states: a demoted connector routes demoted. `verify_all` emits
  per-item verdicts (VERIFIED / UNEXPLAINED / FAILED). Current run on
  the build machine: 28 / 34 / 4 — the 4 FAILED are the Google
  Workspace connectors, whose stored credential Google currently
  answers with 401. The system reports that itself.
- **Hermes seats + Skill Forge** — three scope-enforced bot profiles
  (build / gather / assemble, held by named crew seats) and a forge
  that turns engagement transcripts into provenance-stamped skills,
  quarantined until a named verifier signs them into an append-only
  book.
- **Crew brains** — twelve named subsystems, each with a degradation
  ladder (HF Inference → OpenRouter → Zen → local Ollama → a labeled
  heuristic floor) and a watchdog that logs revivals. A member
  degrades; it never dies and never pretends a floor answer is a
  model answer.
- **Console** — a generated, fully static ops dashboard (works
  offline): connector grid with checked states and timestamps, gate
  queue, seat map, router decision log, simulation replay.

## What's real, what's stubbed — and why

| Piece | State | Why |
|---|---|---|
| Fleet core + gates + audit | **Real, tested** (49/49 inherited suite green) | — |
| Registry / router / decision gate / forge | **Real code**, 144 checks + 3 unittests green | — |
| Connector probes (GitHub, Notion, Stripe, Vercel, Linear, Facebook, Messenger, Tailscale) | **Real** — live status probes ran on the build machine | — |
| Token Factory / Nemotron inference | **MOCK — labeled everywhere** | No Token Factory key provisioned yet. The client is the real code path; in mock mode it makes no network call and marks every response. We do not claim live inference. Model IDs are placeholders pending catalog verification when a key lands. |
| Jev LLM rungs, HF brains, crew fleet | **Adapters, KEY-PENDING** | API keys not yet deposited (Secure Vault). Heuristic floor is real and labeled. |
| Hermes PC profiles | **Adapter, DOOR-PENDING** | The PC door (SSH key install) is the owner's pending step; sim transport exercises the real code paths. |
| Heretic local-model slot | **PREP** | Smoke config staged; no run executed (no GPU on the build VM; run awaits a go decision). The slot raises rather than fake an answer. |
| Quantum route scoring (QAOA/Aer) | **Optional hook** | Simulator experiment; router cites it when its results file exists, falls back to classical scoring otherwise. No speedup claimed. |
| Google Workspace connectors | **CHECK-FAILED (401)** | Stored credential currently rejected by Google; the system demotes and reports it. Re-authorization is a human step. |

## Run it

```bash
python3 fleet.py up       # build console + verify + simulated engagement
python3 fleet.py serve    # http://127.0.0.1:8765/dashboard/
python3 god_check.py      # the checked state table
```

Python 3.12, standard library only for the base system
(`requirements.txt` is an explicit lock; the quantum extra is pinned
in `requirements-quantum.txt`). Tests: seven suites, all green —
including a gate-integrity suite that feeds the approval gate forged,
tampered, replayed, expired, over-cap, and wildcard tokens and
requires every one to fail.

## How Token Factory + Nemotron are used

Every turn of the fleet loop is designed as a runtime call to Nebius
Token Factory: Nano-class Nemotron parses intent to a JSON action,
Super-class coordinates multi-step checks and narrates results,
Ultra-class is reserved for long-log correlation. Tier model IDs are
environment-configured (`TF_MODEL_FAST/PLAN/DEEP`). **Disclosure:**
at submission time the key had not been provisioned, so the submitted
build runs this path in labeled MOCK mode (see the table above and
the feedback field). The architecture, gates, and verification layer
around that call are fully implemented and tested; the live call is
one vault deposit away, and we would rather show the honest seam than
a staged screenshot.

## Art direction (thumbnail + repo visuals)

Matte black / void field (#050607). Jade neon green (#39ff6a) primary
— the OMEGA sigil and live-route accents. Ember orange (#ff6a00)
secondary. Blood red (#e10600) reserved for gates and danger states.
Steel-grey data text, monospace for data, big condensed headers.
Cyberpunk × fighting-game character-select energy; no pastel, no
SaaS stock look, no light mode. Assets in `assets/` (banner + logo)
with the prompts that generated them in `assets/PROMPTS.md`.

## Built with

Python 3.12 (stdlib) · Nebius Token Factory + NVIDIA Nemotron (wired;
mock-labeled at submission) · Hugging Face Inference API (adapter,
key-pending) · Qiskit Aer (optional quantum extra) · the Empire's
decision layer, sentinel doctrine, and crew-seat system — fused
during the hackathon's final day from the team's existing, tested
components. Solo builder + an AI crew, disclosed as such.
