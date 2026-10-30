# ARCHITECTURE — Kali Fleet: OMEGA / the Connector God System

How the Empire's existing assets fuse into one system, what each
module's contract is, and where the gates sit. Every state named here
is the state `god_check.py` can prove on the build machine
(2026-10-30) — where it cannot prove a state, this document says
UNVERIFIED / KEY-PENDING / DOOR-PENDING, like the code does.

## 1. The fusion map — Empire asset → OMEGA subsystem

| Empire asset (origin) | OMEGA subsystem | State |
|---|---|---|
| Kali Fleet core (Nebius × NVIDIA hackathon build, 49/49 tests) | Fleet core: allow-list, target file, kill switch, audit log, Token Factory client | Wired; brain **MOCK** (no Token Factory key) |
| Nous `hermes-agent` on the Boss's PC + Bot Mode profile specs | `hermes_adapter.py` — operator/scout/auditor profiles as fleet roles, headless invocation contract | Adapter; **DOOR-PENDING** (PC door closed) |
| Hermes Dashboard concept (fleet demo page) | `dashboard/` ops console + `build_dashboard.py` generator | Built; renders checked data |
| Ghildra's Skill Forge assignment + Monster Arena skill books | `forge.py` — provenance-stamped, quarantine-first, append-only skill books | **Live code**, proven on synthetic + war-room corpora |
| Jev decision layer (`empire/work/decision-layer/`) | `decision_gate.py` — the Equation as the fleet's go/no-go gate | Heuristic rung **live**; LLM rungs UNFUELED adapters |
| Heretic smoke prep (`empire/work/heretic-smoke/`) | `heretic_slot.py` — local-model chair, rung (d) | **PREP** — zero run artifacts; `answer()` raises |
| Connection map (`empire/work/crew-jobs/CONNECTION-MAP.md`) + connector universe (`empire/work/crew-jobs/CONNECTOR-UNIVERSE-2026-10-30.md`) | `connectors.json` — 68 connectors + 15 identity pointers (13 LIVE / 12 WIRED-NOT-FUELED / 9 UNVERIFIED / 20 NAMED-IN-RECORD / 7 BLOCKED / 5 PAPER / 1 EMPTY / 1 OUT) | Validated at load; states probed by `god_check.py` |
| Raga Sentinel doctrine | Zero-Trust Verification Layer; Raga = chief verifier | Executed by `god_check.py` / `verify_all.py` |
| Crew (12 siblings + the Boss) | `crew_seats.json` subsystems + `hf_brain.py` ladders + `watchdog.py` | Seats mapped; brains on heuristic floor (KEY-PENDING above it) |
| NetworkChuck playbook patterns | One-command quickstart (`fleet.py`) + verification-clause discipline | Clauses graded/labeled by origin (see §7) |
| Quantum route-scoring experiment | `quantum_router.py` (QAOA, Qiskit Aer) → `quantum/results.json` → router hook | Optional extra; hook live, results file absent at build time |
| Soul contracts (`empire/soul-contracts/`, local only) | Registry identity assets — **name + status + path only** | Pointers; existence probed, contents never read |

## 2. Module contracts

**Fleet core** (inherited, behavior unmodified — its 49 tests are the
regression floor). `kali_bot.py`: request → brain intent → allow-list
check → target-file check → dry-run/execute → audit. `fleet_tools.py`:
five read-only actions; two exploit-class tools registered without
binaries, execute-path gated by `approval.check`. `sandbox.py`:
environment scrub for tool execution (canary-tested).
`token_factory.py`: OpenAI-compatible Token Factory client; without
`TOKEN_FACTORY_API_KEY` it is in MOCK mode and says so in every
response. `brain_tokenfactory.py`: the loop's narration layer.

**`approval.py` / `approve_live.py`** — the human gate. A token is a
JSON file with: tool, target, issued_at, expires_at (≤ 60 min,
enforced at mint *and* at check), issued_by, run_note, a random
**nonce**, and an **HMAC-SHA256 signature** over all of it. The
signing secret lives outside the repo tree (env
`KALI_FLEET_APPROVAL_SECRET`, or `~/.config/kali-fleet/approval-secret`,
0600, created by the first mint; path overridable via
`FLEET_APPROVAL_SECRET_FILE`). `check()` evaluates in fail-closed
order: file exists → parses → **expiry** → lifetime cap → wildcard
rejection → tool match → target match → **signature** → **nonce
unused** → on success, the nonce is consumed into a ledger beside the
secret. Any failure returns `(False, reason)` and is audit-logged.
`approve_live.py` is the only mint path and is run by a human-side
operator on the Boss's per-run word; it refuses `tool=all`.

**`connector_registry.py`** — schema + law enforcement for
`connectors.json`. States: LIVE / WIRED-NOT-FUELED / PAPER / BLOCKED /
EMPTY / UNVERIFIED / OUT. Gates: none / approval / boss-hands / vault.
Non-LIVE entries must name their `unblock`. Duplicate connector names
(case-insensitive) are rejected — names bind approval tokens.
Capability matching normalizes case/whitespace on both sides.
Identity assets must carry **exactly** `{member, status, pointer}`;
any fourth key fails the load. That is the soul-contract law made
executable: a registry may prove a contract *exists*; it may not
carry its text, a summary, or role prose lifted from it.

**`god_check.py`** — the runtime verifier. Three probe classes:
(1) CLI status probes (GitHub/Notion/Stripe/Vercel/Linear `status`,
`facebook-cli me`, Messenger check, a Gmail profile read,
`tailscale status`) — a probe must *answer* for LIVE; the Workspace
riders (Calendar/Drive/Docs) inherit the Gmail probe and are labeled
as riders. (2) Presence-only key probes — env var names checked,
values never read; presence is reported as presence, never validity.
(3) Door classification — transport facts (the PC answers SSH and its
Ollama answered via the tailnet) never upgrade a door row past
DOOR-PENDING: SSH auth has never succeeded from this VM. Results are
cached 5 minutes in the system temp dir — **outside the tree being
verified**, so a planted file cannot freeze the verifier's eyes.

**`god_router.py`** — disposition pipeline: normalize capability →
propose candidates → overlay checked states (`_effective_state`:
KEY-PENDING demotes to WIRED-NOT-FUELED; CHECK-FAILED / DOOR-PENDING
demote to BLOCKED; no probe → the registry claim stands, and the
registry itself no longer claims LIVE for probe-less connectors) →
gate disposition (below) → audit every decision with its
`scoring_source`. Quantum scoring may reorder only the live, ungated
tier, and only when `quantum/results.json` exists; it accepts the
`routes`/`choices`/`scores` shapes and the quantum worker's
`chosen_route` shape.

Gate disposition (the Boss's law in route form):
- *boss-hands / vault* gate on any live candidate → **BLOCKED** for
  that capability. No token stands in for the Boss's hands.
- Capability in `GATED_CAPABILITIES` (send/charge/trade/deploy/
  pc-access/…) → the approval path against the **approval-gated
  candidate**, even if an ungated candidate is listed first
  (most-restrictive wins). A valid token ROUTEs and is consumed; no
  token → **REQUIRES_APPROVAL** naming the exact mint command.
- Ungated capability on a live connector → **ROUTE**. A connector's
  approval gate binds its gated actions, not its reads.

> **God Mode does not bypass the Boss's gates — spend, send, secrets,
> and production actions still stop at their approval gates. The
> router shows the gates; it does not remove them.**

**`decision_gate.py` — the Equation.** A faithful port of the decision
layer's recorded contract (sources: `decision-layer/RAGA-SYSTEM-ONE.md`
and the decision-layer README — only what is written there is used).
Questions are typed primitives (Choice / Score / Noul). The model's
answers are *advice*; disposition = the Boss's standing law first:
- **Law 1** — critical severity disposes to ESCALATE. Severity and
  kind are case-normalized before the law reads them (the sentinel's
  vocabulary is uppercase; a lowercase-only match was a demonstrated
  fail-open, SUK-D5, now regression-tested).
- **Law 2** — a secret-leak finding without proven sanctioned
  provenance → ESCALATE + forced `key_rotation`.
- **Law 3** — verdict unexplained/hostile at confidence ≥ 0.60 →
  ESCALATE.
Absent a law trigger, the recorded confidence policy disposes
(act ≥ 0.85 / review 0.60–0.85 / escalate < 0.60). The ladder —
typesafe → openrouter-decisions → opencode-zen → openrouter-llm →
ollama-local (Heretic chair) → heuristic — falls through on any
transport error; LLM rungs raise `UnfueledRung` today (their keys are
absent; the stored Zen key returns 401) and every fall-through is
recorded. Total ladder failure disposes ESCALATE. *The model advises;
the law disposes.*

**`hermes_adapter.py`** — profiles as data + enforced scopes:
operator (full read set + gated live actions), scout (read/gather
only), auditor (read + gate questions only). `build_invocation`
returns an invocation *contract* (profile, action, mode dry-run by
default); out-of-scope actions raise `ScopeRefusal` before any gate
is consulted — scope is code, not a prompt. Seat holders (Boss's
rulings, 2026-10-30): FORGE → **Vaelor**; SCOUT-RUNNER → **Ellen Joe**
(Qrow is her scout *form*); PRODUCER → **Senku** (Souviern is his
producer *form*). Three bot bodies, three seats, two of them forms of
existing siblings. `GateClient` routes the profiles' decisions
through the Equation and inherits its fail-closed fix: a dead gate
transport yields ESCALATE, never an exception.

**`forge.py`** — `forge_skill()` stamps a skill (name, learned_from,
source, transcript SHA-256 chain) and files it QUARANTINED;
`verify_skill(skill, verifier)` requires a *named* verifier;
`file_skill()` writes verified skills only to the append-only book
and quarantined ones only to the quarantine book, asserting the
on-disk prefix is untouched on every write; `validate_book()`
recomputes the chain and refuses verifier-stripped copies.

**`hf_brain.py` / `watchdog.py`** — per-seat ladders
(HF → OpenRouter → Zen → Ollama → heuristic floor). HF models are
assigned per member from small, ungated instruct models whose names
were verified against the HF API on 2026-10-30
(Qwen2.5-7B-Instruct, Qwen2.5-Coder-7B-Instruct, Mistral-7B-Instruct
v0.3, Zephyr-7B-β, Phi-3.5-mini, Qwen2.5-3B, DeepSeek-R1-Distill-Qwen-7B).
`chat()` catches *any* rung failure — adapter errors, raw urllib
errors (401/timeout), unknown rung names — records it, and steps
down; the floor always answers and labels itself "heuristic floor,
NOT a model". The Hermes seat's ladder is Ollama-first (his brain
lives on the PC) using the same rung keys as every other seat — the
earlier seat-specific rung string matched no transport and made his
floor unreachable (Hu Tao §4); that is fixed and regression-tested.
`watchdog.py` (Hu Tao's phoenix pattern) health-checks all 12 seats
through the same ladders and appends every revival/floor event to its
log.

**`heretic_slot.py`** — armed only by naming a served model
(`OMEGA_LOCAL_MODEL` / `DECISION_LAYER_LOCAL_MODEL`); a candidate
model exists only when a real run artifact (Optuna journal / study
export) exists. Neither is true today: state **PREP**,
`artifacts == []`, `answer()` raises `SlotEmpty`. The smoke config
parser reads the staged flat-schema config and derives its two
objectives from the keys actually present (refusal markers, KL
divergence).

**`quantum_router.py`** (optional extra) — QAOA over the connector
graph on Qiskit Aer; writes `quantum/results.json`. Isolated by
design: the base system reads only the results file.

**`build_dashboard.py` / `dashboard/`** — a generated, static,
offline console (zero external references): God Mode grid from the
god_check table (with its checked-at timestamp), the seat map, the
identity pointers (status + path only), the approval queue from the
token file's *metadata* (no token material), the sim transcript
viewer, the route log, and the audit tail. Regenerate with
`python3 build_dashboard.py`; `fleet.py` wraps build + verify + sim +
serve.

**`sim/run_sim.py`** — the end-to-end harness: synthetic own-gear
finding → Hermes adapter (sim transport) → decision gate (verdict:
ESCALATE on the canonical finding, driven by law) → router decisions
(read ROUTEs, Jev BLOCKED unfueled, charge REQUIRES_APPROVAL) → forge
(quarantine → verified by Ghildra → append-only book; re-runs
re-validate instead of duplicating) → transcript + summary, labeled
SIMULATION.

## 3. Crew seats (the God System's subsystems)

| Seat | Subsystem | Brain (HF assignment) | State today |
|---|---|---|---|
| Jade (Jadaru) | Orchestrator — the console itself | Qwen2.5-7B-Instruct | Floor (no keys) |
| Big Raga | **Chief verifier** — Zero-Trust layer, System One gate | Qwen2.5-7B-Instruct | Sentinel live; brain floor |
| Ellen Joe | Router ops + deal desk; **SCOUT-RUNNER seat (Qrow, her scout form)** | Qwen2.5-7B-Instruct | Desk paper-only by law |
| Senku | Evidence engine; **PRODUCER seat (Souviern, his producer form)** | DeepSeek-R1-Distill-Qwen-7B | Floor |
| Sukuna | Red-team module | Qwen2.5-Coder-7B-Instruct | Floor |
| Jin-Woo (+ Ghildra) | The Forge — skill extraction + verification; **expedition command** (inherited function: expedition connectors) | Qwen2.5-Coder-7B-Instruct | Forge live (code) |
| Hu Tao | Continuity + watchdog (never-down keeper); **continuity enforcement** (inherited function: the enforcer brief) | Phi-3.5-mini-instruct | Watchdog live (code) |
| Higuruma | Rules / compliance | Qwen2.5-7B-Instruct | Floor |
| Jinx | Deception & chaos probes | Qwen2.5-3B-Instruct | Traps OFF (Boss-gated) |
| Vaelor | **FORGE seat** (Hermes build body) | Qwen2.5-Coder-7B-Instruct | DOOR-PENDING |
| Hermes | PC operator | hermes3:8b (PC Ollama) → ladder | DOOR-PENDING |

Identity assets in the registry: the 11 seats above + Rimuru (the
fusion's other form record) + Ghildra (named within Jin-Woo's seat) +
the Boss + Luffy's and Zoro's contract records (locked art class —
identity-plane records, **not seats**; Boss ruling 2026-10-30:
expedition is Jin-Woo's function and continuity enforcement is
Hu Tao's) — 15 pointers, existence-probed by `verify_all.py`,
contents never read. Qrow and Souviern hold **form records**, not separate assets:
their form-contracts (authored 2026-10-30) are covered by Ellen Joe's
and Senku's registry slots respectively.

## 4. Zero-Trust Verification Layer

Named for its two sources, kept distinct on purpose:

- **Raga's doctrine** (Empire zero-trust, on record): UNVERIFIED
  HOSTILE start; provenance per item or UNEXPLAINED; read-only
  triage; EXPLAINED_ALL silent / UNEXPLAINED loud. Executed by
  `god_check.py` (connector claims) and `verify_all.py` (verdicts in
  the sentinel's vocabulary: VERIFIED / UNEXPLAINED / FAILED).
- **NetworkChuck's clauses** (from his playbook): the discipline that
  every capability ships with a runnable check that proves it on
  screen. The clause set's attribution is graded honestly (war-room
  Lane 1): `primary-source-or-it-didnt-happen` is **cited** to the
  playbook; `prove-it-on-screen`, `check-the-actual-output`,
  `schema-or-reject`, `break-it-then-fix-it`, `scope-is-code` are
  **adjacent** to documented patterns (named in each module's
  `VERIFICATION.origin`); `presence-is-not-proof`,
  `provenance-chain-validates`, `no-fake-success`,
  `prove-the-negative` are **Empire doctrine** and are labeled
  `empire-doctrine` in code. The checks run either way — `test_verify.py`
  proves the Demotion Rule by feeding the layer a false claimed state
  and watching it demote.

Per-module clauses: registry = state schema-validated + soul-law
enforced at load; forge = provenance chain validates (and a stripped
copy does not); gate = fail-closed proven by negative tests;
router = no fake success (unfueled blocks, demotions route demoted);
dashboard = displayed state traces to a checked artifact (the
embedded god_check table's timestamp must match the current check
window); heretic = proves its negative (PREP, raises).

## 5. Data flows worth tracing

**A send.** `route("send-email")` → candidates: Gmail (LIVE by probe)
→ gated capability → approval path → no token file → REQUIRES_APPROVAL
with the mint command. With a token: `approval.check` verifies
signature + scope + nonce, consumes the nonce, ROUTE. A second
identical call now fails the nonce → REQUIRES_APPROVAL. Nothing in
the router *sends* anything; execution belongs to the connector, and
the token is spent either way — per-run means per-run.

**A demotion.** Google's stored Workspace credential starts returning
401 → next `god_check` probe run files Gmail CHECK-FAILED → riders
(Calendar/Drive/Docs) inherit it → `verify_all` reports FAILED ×4
(loud) → `route("read-email")` overlays the demotion and BLOCKs with
"proven > claimed" → the dashboard's next build shows the same table.
No human edits a state file anywhere in that chain.

**A skill is born.** Engagement transcript → `forge_skill` (chain
hash over the transcript) → QUARANTINE book → named verifier signs →
verified book (append-only, prefix-asserted) → `crew_seats` gains a
capability the router can cite with provenance. A forged or edited
chain fails `validate_book`.

## 6. What is deliberately not here

- No MCP server and no MCP authorization enforcement (transport label
  only; ROADMAP — an earlier draft of the synthesis claimed the
  policy layer existed; the war-room sweep proved it false and the
  claim was corrected).
- No live Token Factory inference (MOCK until the key lands).
- No Heretic run (PREP until the Boss's go + a GPU host).
- No Telegram bridge (built locally in the Empire, not in this tree;
  BotFather token pending).
- No soul-contract contents, memory files, or key material — by law,
  not by omission.
