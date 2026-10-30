![Kali Fleet: OMEGA](assets/banner.png)

# KALI FLEET: OMEGA — the Connector God System

[![tests](https://img.shields.io/badge/tests-144%20checks%20%2B%203%20quantum%20unittests-39ff6a?style=flat-square&labelColor=050607)](https://img.shields.io)
[![base](https://img.shields.io/badge/base-Kali%20Fleet%2049%2F49%20green-39ff6a?style=flat-square&labelColor=050607)](https://img.shields.io)
[![brain](https://img.shields.io/badge/brain-MOCK%20(labeled)-ff6a00?style=flat-square&labelColor=050607)](https://img.shields.io)
[![gates](https://img.shields.io/badge/approval%20gates-signed%20%C2%B7%20single--use-e10600?style=flat-square&labelColor=050607)](https://img.shields.io)

**One-liner:** Kali Fleet — a Nemotron-wired security copilot that can
only touch your own gear — grown into the Empire's connector operating
system: a validated registry of every connector, brain, and crew seat;
a fail-closed router disposed by the Boss's standing law; and a
zero-trust verification layer that proves every claimed state by probe
or demotes it in public.

Built for the **Nebius × NVIDIA Global AI Hackathon 2026**, track:
**Best Apps & Agents**.

## Run it (3 commands)

```bash
python3 fleet.py up        # build the console, run verification, run the sim
python3 fleet.py serve     # console at http://127.0.0.1:8765/dashboard/
python3 god_check.py       # the checked state table, from live probes
```

No packages to install for the base system: Python 3.12 standard
library only (`requirements.txt` is an explicit zero-dependency lock;
the optional quantum extra is pinned separately in
`requirements-quantum.txt`).

## The honest state of the brain

The fleet's intent brain calls **Nebius Token Factory** (Nemotron
tiers below) through `token_factory.py`. **No Token Factory key is set
in this environment, so the client runs in labeled MOCK mode**: no
network call is made, responses are canned and marked `"mock": true`,
and a keyword rule engine stands in for the Nano-class parser. Wired
code is not a runtime call, and this README does not pretend
otherwise. The moment a key is provisioned (Secure Vault), the same
code path runs live — model identifiers must then be verified against
the Token Factory catalog (the defaults are labeled placeholders in
`token_factory.py`).

| Tier | Model class | Job in the loop |
|------|-------------|-----------------|
| Fast | **Nemotron 3 Nano** (30B) | Parse plain English into one allow-listed intent (JSON) |
| Plan | **Nemotron 3 Super** (120B) | Multi-step coordination + narrate raw results back in plain English |
| Deep | **Nemotron 3 Ultra** (500B) | Reserved — correlating long audit logs / triage summaries |

## Architecture in one screen

```
        plain-English request / capability call
                        │
   ┌────────────────────▼─────────────────────┐
   │  GOD ROUTER (god_router.py)              │  propose → check → dispose
   │  · capability match (case-normalized)    │
   │  · god_check overlay: proven > claimed   │
   │  · most-restrictive gate wins            │
   │  · the EQUATION disposes (decision_gate) │
   └───────┬──────────────┬──────────────┬────┘
           │              │              │
   ┌───────▼──────┐ ┌─────▼───────┐ ┌────▼─────────────┐
   │ REGISTRY     │ │ APPROVAL    │ │ FLEET CORE       │
   │ connectors.  │ │ signed,     │ │ allow-list, own- │
   │ json (68 +   │ │ single-use  │ │ gear targets,    │
   │ 15 identity  │ │ tokens      │ │ kill switch,     │
   │ pointers)    │ │ (approval)  │ │ audit log        │
   └──────────────┘ └─────────────┘ └────┬─────────────┘
                                          │
   ┌──────────────────────────────────────▼──────────────┐
   │  FORGE (forge.py) — engagements become provenance-  │
   │  stamped skills, quarantined until a named verifier │
   │  signs them. HERMES seats (hermes_adapter.py) run   │
   │  the PC-side bot profiles inside the same scope law.│
   └─────────────────────────────────────────────────────┘
   ZERO-TRUST VERIFICATION LAYER over all of it: god_check.py
   probes, verify_all.py verdicts (VERIFIED / UNEXPLAINED /
   FAILED), Raga's doctrine — see ARCHITECTURE.md.
```

Full diagram, module map, and data flows: **ARCHITECTURE.md**.

## What the OMEGA layer adds to Kali Fleet

**Connector registry (`connector_registry.py` + `connectors.json`).**
68 connectors/integrations/brains plus 15 identity assets — 13 LIVE,
12 WIRED-NOT-FUELED, 9 UNVERIFIED, 20 NAMED-IN-RECORD (services named
in Marke's Perplexity record by the 2026-10-30 connector-universe
merge: never attempted, nothing probed or built — map pins, not
connections), 7 BLOCKED, 5 PAPER, 1 EMPTY, 1 OUT — hand-authored
from the Empire's verified connection map (2026-10-30), each with
capabilities, transport, fuel state, gate, the exact unblocking step
when it isn't LIVE, and a verification clause. The loader validates
everything: unknown states/gates, duplicate names, and — by law —
identity entries carrying anything beyond **name + status + path**
are rejected at load. Soul-contract *contents* never enter this tree.

**God router (`god_router.py`).** Given a capability, it proposes
candidates from the registry, overlays **god_check's probed states**
(a connector demoted to KEY-PENDING routes as WIRED-NOT-FUELED;
CHECK-FAILED routes as BLOCKED — claimed state alone never routes),
applies the **most restrictive gate** across all live candidates (an
ungated duplicate cannot shadow a gated route), and disposes through
the Equation. Fail-closed everywhere: unfueled → BLOCKED with the
exact unblocking step, never a fake success.

> **God Mode does not bypass the Boss's gates — spend, send, secrets,
> and production actions still stop at their approval gates. The
> console shows the gates; it does not remove them.**

**The Equation (`decision_gate.py`).** The fleet's go/no-go gate: the
Jev decision model as recorded in the Empire's decision layer
(`empire/work/decision-layer/` — RAGA-SYSTEM-ONE.md is its home).
Routes are *proposed* by capability matching; they are *disposed* by
the Equation plus the Boss's standing law — three recorded laws
(critical severity escalates; an unproven secret-leak escalates and
forces key rotation; an unexplained/hostile verdict at confidence
escalates), a recorded confidence policy (act ≥ 0.85, review
0.60–0.85, escalate < 0.60), and a rung ladder whose LLM rungs are
adapters honestly labeled UNFUELED until their keys exist. The
heuristic floor always answers; a dead or malformed transport fails
closed to ESCALATE. *The model advises; the law disposes.*

**Approval tokens (`approval.py`, `approve_live.py`).** Exploit-class
execution and gated routes require a token minted only on the Boss's
per-run word. Tokens are **HMAC-signed** (secret outside the repo
tree), **single-use** (nonce consumed on the first successful check),
**hard-capped at 60 minutes — enforced at check time** — and scoped to
exactly one tool + one target. The `tool:"all"` wildcard is refused
at mint and never honored. Forged, tampered, replayed, expired, and
over-cap tokens all fail closed; `test_approval_tokens.py` proves
each one.

**Hermes seats (`hermes_adapter.py`).** Three bot-mode profiles on the
Empire's PC-side Hermes host, held by siblings under the Boss's
rulings: **FORGE → Vaelor** (build), **SCOUT-RUNNER → Ellen Joe** in
her scout form **Qrow** (gather), **PRODUCER → Senku** in his producer
form **Souviern** (assemble/ship). Profiles are scope-checked in code
(a scout requesting an operator-only tool is refused before any gate),
and live actions additionally require the approval gate. The PC door
is currently closed (DOOR-PENDING), so the adapter's live transport is
unavailable and says so; its simulation transport runs the real code
paths against synthetic targets.

**Skill Forge (`forge.py`).** A completed engagement's transcript
becomes a skill file with a SHA-256 provenance chain (name,
learned_from, source, transcript hash), born **QUARANTINED**. Only a
named verifier (Ghildra, the Forge's keeper) can move it to VERIFIED,
and only into the append-only book; a tampered chain fails validation.
This is Ghildra's standing assignment, implemented.

**Crew brains (`hf_brain.py`, `crew_seats.json`, `watchdog.py`).**
Every sibling is a named God System subsystem — Raga: chief verifier;
Ellen Joe: router ops + deal desk (+ the SCOUT-RUNNER seat); Senku:
evidence engine (+ the PRODUCER seat); Sukuna: red team; Jin-Woo +
Ghildra: the Forge + expedition command (inherited function —
expedition connectors, run as shadow-army tasking); Hu Tao:
continuity + watchdog + continuity enforcement (inherited function —
the enforcer brief, exercised as revival and sealing); Higuruma:
rules/compliance; Jinx: deception probes; Vaelor: the FORGE seat;
Hermes: PC operator. Luffy and Zoro hold no seat (Boss rulings
2026-10-30): their contract records remain in the identity plane as
locked art — pointers only — and their functions were inherited,
expedition by Jin-Woo and enforcement by Hu Tao. Each seat has a brain
ladder — Hugging Face Inference (one assigned small ungated instruct
model per member; model names verified against the HF API on
2026-10-30) → OpenRouter → Zen → local Ollama → a heuristic floor that
labels itself NOT a model. A member degrades, never dies: the floor is
guaranteed reachable (unknown rung names and raw transport errors
step down like any other failure), and `watchdog.py` health-checks
every seat and logs every revival. The HF rung is **KEY-PENDING**
(`HF_TOKEN` via Secure Vault) — wired, tested with fake transports,
honest.

**Heretic slot (`heretic_slot.py`).** The local-model chair, per the
decision layer's HERETIC-INTEGRATION contract. State: **PREP** — the
smoke config is staged (3 trials, refusal + KL-divergence objectives)
but no run has executed (this VM has no GPU; the Colab route is
specced; the run waits on the Boss's "go"). `answer()` raises rather
than fabricate an inference. EMPTY means empty.

**Quantum hook (`quantum_router.py`, optional).** A QAOA route-scoring
experiment on Qiskit Aer. When its results file exists, the router may
let it reorder *live, ungated* candidates and cites the decision
"quantum-simulator scored (Aer)"; classical scoring is the fallback
and every decision logs its scoring source. It cannot promote an
unfueled connector or touch a gate. Simulator only — no speedup is
claimed. Requires `requirements-quantum.txt`; the base system never
imports it.

**Simulation harness (`sim/`).** `sim/run_sim.py` runs a full
engagement through the real code paths — Hermes adapter (sim
transport) → decision gate → router → forge → console data — against a
synthetic own-gear target, and writes a replayable transcript. It is
labeled **SIMULATION** everywhere it surfaces: a real run of real code
on synthetic targets.

## Zero-Trust Verification Layer — Raga's doctrine × NetworkChuck's clauses

Doctrine (Raga Sentinel, on record): every claim starts **UNVERIFIED
HOSTILE**; provenance is proven per item or named **UNEXPLAINED**;
triage is read-only; EXPLAINED_ALL → silent, UNEXPLAINED/CRITICAL →
loud. Big Raga is the God System's chief verifier: proven state or
demoted — his call, executed by `god_check.py` (live CLI status
probes + presence-only key checks; credential *values* are never
read) and `verify_all.py` (per-item verdicts: VERIFIED / UNEXPLAINED
/ FAILED; **the Demotion Rule: proven outranks claimed**, wired into
the router, not just the report).

Every module and connector carries a **verification clause** — a
runnable check that proves the claim. Attribution, stated plainly
(the war-room audit graded them): of the clause names, one is
NetworkChuck's as documented in his playbook
(`primary-source-or-it-didnt-happen`); five are adjacent to documented
patterns of his (monitor-the-watchers → `prove-it-on-screen`;
named-resources-only → `scope-is-code`; structured output →
`schema-or-reject`; fix-a-class-and-verify → `break-it-then-fix-it`;
Terry's content checks → `check-the-actual-output`); the rest —
`presence-is-not-proof`, `provenance-chain-validates`,
`no-fake-success`, `prove-the-negative` — are **Empire zero-trust
doctrine**, ours, and are labeled `empire-doctrine` in code. The
checks are real either way; the names now tell the truth about whose
habit each one is.

**Current verdict run (2026-10-30, this machine, after the 68-connector
merge):** 29 VERIFIED / 56 UNEXPLAINED / 4 FAILED over 89 rows. The 4 FAILED are Gmail + Calendar + Drive +
Docs: Google's API currently answers the stored Workspace credential
with **401** — probe-proven, demoted everywhere including the router,
and loud by doctrine until the credential is re-authorized (the
Boss's hands). The UNEXPLAINED rows are the key-pending and
door-pending systems, each naming its exact missing input.

## Live state, checked — not asserted

`god_check.py` re-verifies the registry at runtime. On 2026-10-30:
**probe-verified LIVE** — GitHub, Notion, Stripe, Vercel, Linear,
Facebook, Messenger, Tailscale (plus the heuristic gate rung, proven
in-tree). **KEY-PENDING** (credential physically absent; exact input
named per row) — Supabase (service_role key), OpenRouter, Nebius Token
Factory, Hugging Face, Hostinger API, Manus, Telegram (BotFather
token), the Jev LLM rungs, the crew-brain fleet. **DOOR-PENDING** —
the PC door (the Boss's elevated key-install paste), Hermes, Ollama.
**UNVERIFIED** (no probe exists on this VM; the registry refuses to
call them LIVE) — Instagram, Polsia, Replit, Gumroad, Raga Sentinel,
Monster Arena. Anything else is labeled PAPER / BLOCKED / EMPTY / OUT
in `connectors.json` with its reason.

## Safety law (unchanged from Kali Fleet, enforced in code)

- **Own gear only.** Scan targets come from `fleet_targets.txt`
  (default: localhost). Anything else is refused and logged.
- **Allow-list only.** Five read-only fleet actions; two exploit-class
  recon tools are registered without binaries and cannot execute
  without a signed single-use approval token.
- **Dry-run by default; kill switch** (`FLEET_STOP=1` / `STOP.txt`).
- **Every attempt is audit-logged** (allowed, refused, dry-run,
  executed) to `audit_log.jsonl`.
- **No secrets in the tree.** Keys live in the Secure Vault / env;
  probes check presence only.

## Tests

```bash
for t in test_smoke test_live_gate test_dayofexploits test_omega \
         test_verify test_crew test_approval_tokens; do
  python3 $t.py; done
python3 test_quantum_router.py   # needs requirements-quantum.txt
```

144 checks + 3 quantum unittests, all green on 2026-10-30 — including
the inherited Kali Fleet base (49/49, unmodified behavior), the
war-room gate-integrity suite (forged / tampered / replayed / expired
/ over-cap / wildcard tokens; duplicate-route shadowing;
capitalization bypass; checked-state demotion; SUK-D5 uppercase
severity regression), and the forge/gate/router contract tests.

## Layout

```
kali core      kali_bot.py fleet_tools.py sandbox.py approval.py
               approve_live.py token_factory.py brain_tokenfactory.py
god system     connector_registry.py connectors.json god_router.py
               god_check.py verify_all.py decision_gate.py
empire seats   hermes_adapter.py forge.py hf_brain.py crew_seats.json
               watchdog.py heretic_slot.py quantum_router.py
console        build_dashboard.py dashboard/ demo/ fleet.py
simulation     sim/run_sim.py (+ generated transcript, gitignored)
tests          test_smoke.py test_live_gate.py test_dayofexploits.py
               test_omega.py test_verify.py test_crew.py
               test_approval_tokens.py test_quantum_router.py
docs           ARCHITECTURE.md DEVPOST-V2-DRAFT.md FIX-REPORT.md
               DEPENDENCIES.md requirements.txt requirements-quantum.txt
```

## License

MIT (see `LICENSE`).
