#!/usr/bin/env python3
"""
Build dashboard/index.html — the OMEGA ops console (God Mode).

The dashboard is a static file (works from file:// and GitHub Pages,
zero external references). Its data is NOT hand-typed: this generator
embeds, at build time —
  * connectors.json          (the registry),
  * god_check.check()        (states CHECKED on this machine at the
                              embedded checked_at; god_check.py
                              re-checks live any time),
  * sim/transcript.jsonl     (the SIMULATION replay),
  * audit entries            (project audit_log.jsonl tail + the sim's
                              GOD_ROUTE / DECISION_GATE records),
  * heretic_slot.status()    (the Heretic chair, honestly EMPTY/PREP),
  * decision_gate.RUNGS      (the ladder, with fuel states).

Rebuild after any of those change:  python3 build_dashboard.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import god_check
import heretic_slot

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KALI FLEET: OMEGA — God Mode Console</title>
<style>
  :root { color-scheme: dark; --void:#050607; --panel:#0b0e0c; --line:#1d2b21;
          --jade:#39ff6a; --ember:#ff6a00; --blood:#e10600; --steel:#9aa3ad;
          --bone:#e8ece9; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--void); color:var(--bone);
         font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
         line-height:1.5;
         background-image: repeating-linear-gradient(0deg, rgba(57,255,106,.018) 0 1px, transparent 1px 3px); }
  main { max-width:1180px; margin:0 auto; padding:28px 18px 64px; }
  .banner { width:100%; border:1px solid var(--line); display:block; }
  .brandfall { display:none; padding:34px 10px 6px; text-align:center; }
  .brandfall .sig { font-size:3.2rem; color:var(--jade); text-shadow:0 0 18px rgba(57,255,106,.55); }
  h1 { font-family:"Arial Narrow", Impact, sans-serif; letter-spacing:.14em;
       font-size:2.6rem; margin:18px 0 2px; color:var(--bone); text-transform:uppercase; }
  h1 .om { color:var(--jade); text-shadow:0 0 14px rgba(57,255,106,.6); }
  h2 { font-family:"Arial Narrow", Impact, sans-serif; letter-spacing:.18em;
       font-size:1.25rem; margin:38px 0 12px; color:var(--jade); text-transform:uppercase;
       border-bottom:1px solid var(--line); padding-bottom:6px; }
  h2 .sub { color:var(--steel); font-size:.72rem; letter-spacing:.05em; float:right; }
  .tag { color:var(--steel); margin:0 0 8px; }
  .law { border:1px solid var(--blood); border-left:6px solid var(--blood);
         background:#140505; padding:10px 14px; margin:16px 0; }
  .law b { color:#ff5a4d; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(215px,1fr)); gap:10px; }
  .node { background:var(--panel); border:1px solid var(--line); padding:10px 12px;
          clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 14px 100%, 0 calc(100% - 14px)); }
  .node .nm { font-weight:bold; font-size:.86rem; }
  .node .dt { color:var(--steel); font-size:.7rem; margin-top:4px; }
  .chip { display:inline-block; font-size:.66rem; padding:1px 7px; margin-top:6px;
          border:1px solid; letter-spacing:.08em; }
  .LIVE { color:var(--jade); border-color:var(--jade); box-shadow:0 0 8px rgba(57,255,106,.35); }
  .KEY-PENDING,.REGISTRY,.WIRED-NOT-FUELED,.PAPER,.EMPTY,.UNVERIFIED,.NAMED-IN-RECORD { color:var(--ember); border-color:var(--ember); }
  .DOOR-PENDING,.BLOCKED,.CHECK-FAILED,.OUT { color:#ff5a4d; border-color:var(--blood); }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:10px; }
  .card { background:var(--panel); border:1px solid var(--line); padding:12px 14px; }
  .card b { color:var(--ember); display:block; font-size:.74rem; letter-spacing:.1em; text-transform:uppercase; }
  .card .big { font-size:1.3rem; color:var(--bone); }
  pre, .stream { background:#070908; border:1px solid var(--line); padding:12px 14px;
                 overflow-x:auto; font-size:.78rem; white-space:pre-wrap; }
  .stream div { padding:2px 0; border-bottom:1px dashed #14201a; }
  .gate { color:#ff5a4d; } .route { color:var(--jade); } .hold { color:var(--ember); }
  button { background:#0d130e; color:var(--jade); border:1px solid var(--jade);
           font:inherit; padding:7px 18px; cursor:pointer; letter-spacing:.1em; }
  button:hover { box-shadow:0 0 12px rgba(57,255,106,.45); }
  .warn { border-left:4px solid var(--ember); background:#140d05; padding:8px 12px; }
  footer { margin-top:48px; color:var(--steel); font-size:.8rem; border-top:1px solid var(--line); padding-top:12px; }
  a { color:var(--jade); }
</style>
</head>
<body>
<main>
  <img class="banner" src="../assets/banner.png" alt="Kali Fleet: OMEGA"
       onerror="this.style.display='none';document.getElementById('bf').style.display='block'">
  <div class="brandfall" id="bf"><div class="sig">Ω</div></div>
  <h1>Kali Fleet: <span class="om">Omega</span></h1>
  <p class="tag">Ops console + God Mode — every Empire connector, checked live;
  every gate visible; nothing routed around the Boss's law.</p>

  <div class="law"><b>GOD MODE LAW:</b> God Mode does NOT bypass the Boss's gates.
  Spend, send, secrets, and production actions still stop at their approval gates.
  This console shows the gates — it does not remove them.</div>

  <h2>Fleet status <span class="sub">core loop — kali_bot, dry-run by default</span></h2>
  <div class="cards" id="fleet"></div>

  <h2>⚠ God Mode — connector grid <span class="sub" id="checked-at"></span></h2>
  <div class="grid" id="godgrid"></div>
  <p class="tag">States are CHECKED by god_check.py against the connectors' own
  status probes on the build machine — not asserted. Re-run
  <i>python3 god_check.py</i> for a fresh table. KEY-PENDING names the exact
  missing input; DOOR-PENDING names the exact missing act.</p>

  <h2>Router decision log <span class="sub">GOD_ROUTE / DECISION_GATE — from the simulation run's audit + project audit tail</span></h2>
  <div class="stream" id="routelog"></div>

  <h2>Approval queue <span class="sub">approval.py — fail-closed tokens, minted only on the Boss's per-run word</span></h2>
  <div class="card" id="appr"></div>

  <h2>Model routing — the Equation's ladder <span class="sub">the model advises · the law disposes</span></h2>
  <div class="stream" id="ladder"></div>

  <h2>SIMULATION replay <span class="sub">real code paths · synthetic target · dry-run actions</span></h2>
  <div class="warn"><b>SIMULATION</b> — a real run of this project's real code
  (Hermes adapter → decision gate → God Router → Ghildra Forge) against a
  synthetic own-gear scenario. No real target, network, or connector was touched.</div>
  <p><button id="play">▶ REPLAY TRANSCRIPT</button></p>
  <div class="stream" id="simlog"></div>

  <h2>Crew seats <span class="sub">every sibling is a named subsystem — Raga verifies, Hu Tao keeps them up</span></h2>
  <div class="grid" id="seats"></div>

  <h2>Identity assets — soul contracts <span class="sub">metadata + pointers only; contents never enter this project (Boss law, 2026-10-29)</span></h2>
  <div class="grid" id="souls"></div>

  <h2>Audit stream <span class="sub">audit_log.jsonl tail — every attempt: allowed, refused, dry-run, executed</span></h2>
  <div class="stream" id="audit"></div>

  <footer>KALI FLEET: OMEGA · Nebius × NVIDIA Hackathon 2026 · MIT ·
  Scope: owner's own machines and authorized labs only ·
  <span id="heretic-note"></span></footer>
</main>
<script>
const GOD = __GODCHECK__;
const REG = __REGISTRY__;
const SIM = __SIM__;
const AUDIT = __AUDIT__;
const ROUTELOG = __ROUTELOG__;
const HERETIC = __HERETIC__;
const RUNGS = __RUNGS__;
const TOKEN = __TOKEN__;
const SEATS = __SEATS__;

const chip = s => `<span class="chip ${s}">${s}</span>`;
document.getElementById('checked-at').textContent =
  'checked at ' + GOD.checked_at + ' by god_check.py';
document.getElementById('godgrid').innerHTML = GOD.rows.map(r =>
  `<div class="node"><div class="nm">${r.name}</div>${chip(r.checked_state)}
   <div class="dt">registry: ${r.registry_state}${r.missing_input ? '<br>missing: ' + r.missing_input : ''}</div></div>`).join('');

document.getElementById('fleet').innerHTML = [
  ['Allow-listed actions', '5 — read-only'],
  ['Targets', 'fleet_targets.txt only'],
  ['Default mode', 'DRY-RUN'],
  ['Kill switch', 'FLEET_STOP=1 / STOP.txt'],
  ['Live approval token', TOKEN.present ? 'ON FILE' : 'none on file'],
  ['Brain (Nemotron)', 'MOCK — key pending'],
].map(([k,v]) => `<div class="card"><b>${k}</b><span class="big">${v}</span></div>`).join('');

document.getElementById('routelog').innerHTML = ROUTELOG.map(e => {
  const cls = e.decision === 'ROUTE' || e.disposition === 'ALLOW' ? 'route'
            : e.decision === 'BLOCKED' || e.disposition === 'ESCALATE' ? 'gate' : 'hold';
  const head = e.action === 'GOD_ROUTE'
    ? `ROUTE ${e.capability} → ${e.connector || '—'} [${e.decision}] (${e.scoring_source || 'classical'})`
    : `GATE [${e.disposition}] driver=${e.driver} backend=${e.backend || '—'}`;
  return `<div><span class="${cls}">${head}</span> — ${e.reason || (e.reasons || []).join('; ')}</div>`;
}).join('') || '<div>no route records yet</div>';

document.getElementById('appr').innerHTML = TOKEN.present
  ? `<b>Live-approval token ON FILE</b><br>tool=${TOKEN.tool} target=${TOKEN.target} expires=${TOKEN.expires_at}`
  : `<b>No live-approval token on file.</b><br>Nothing runs live. A token is minted
     only by approve_live.py on the Boss's explicit per-run word, is scoped to one
     tool + one target, and expires within 60 minutes. Fail-closed: missing,
     malformed, or expired all mean NOT approved.`;

document.getElementById('ladder').textContent = RUNGS.map(r =>
  `  rung  ${r[0].padEnd(22)} ${r[1]}`).join('\n') +
  `\n\n  Heretic chair (rung d): ${HERETIC.state} — ${HERETIC.note}` +
  (HERETIC.config ? `\n  smoke config: n_trials=${HERETIC.config.n_trials}, scorers=${HERETIC.config.scorers.map(s=>s.score_name).join(' + ')}` : '');

document.getElementById('seats').innerHTML = SEATS.map(s =>
  `<div class="node"><div class="nm">${s.member}</div>${chip(s.state.startsWith('LIVE') ? 'LIVE' : 'KEY-PENDING')}
   <div class="dt">${s.subsystem}<br>HF brain: ${s.hf_model}<br>ladder: ${s.ladder.join(' → ')}</div></div>`).join('');

document.getElementById('souls').innerHTML = REG.identity_assets.map(a =>
  `<div class="node"><div class="nm">${a.member}</div>${chip(a.status.startsWith('MISSING') ? 'BLOCKED' : 'LIVE')}
   <div class="dt">${a.status}${a.pointer ? '<br>↳ ' + a.pointer + ' (local only)' : ''}</div></div>`).join('');

document.getElementById('audit').innerHTML = AUDIT.map(e =>
  `<div>${e.ts || ''} · ${e.action} · ${e.mode || ''} ${e.ok === false ? '<span class="gate">REFUSED</span>' : ''} ${e.reason ? '— ' + e.reason : ''}</div>`).join('');

document.getElementById('heretic-note').textContent =
  `Heretic slot: ${HERETIC.state} (no run artifacts; Boss-gated).`;

let i = 0, timer = null;
const simlog = document.getElementById('simlog');
function step() {
  if (i >= SIM.length) { clearInterval(timer); return; }
  const ev = SIM[i++];
  const d = document.createElement('div');
  d.textContent = `[SIM ${ev.kind}] ` + JSON.stringify(ev).slice(0, 300);
  simlog.appendChild(d);
}
document.getElementById('play').onclick = () => {
  simlog.innerHTML = ''; i = 0; clearInterval(timer);
  timer = setInterval(step, 650);
};
</script>
</body>
</html>
"""


def _tail(path, n):
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-n:]
        return [json.loads(l) for l in lines if l.strip()]
    except (OSError, ValueError):
        return []


def main():
    report = god_check.check(use_cache=True)
    registry = json.load(open(os.path.join(HERE, "connectors.json"),
                              encoding="utf-8"))
    sim = _tail(os.path.join(HERE, "sim", "transcript.jsonl"), 500)
    sim_audit = _tail(os.path.join(HERE, "sim", "sim-audit.jsonl"), 500)
    routelog = [e for e in sim_audit
                if e.get("action") in ("GOD_ROUTE", "DECISION_GATE")]
    audit = _tail(os.path.join(HERE, "audit_log.jsonl"), 12)
    token_path = os.path.join(HERE, "approvals", "live-approval.json")
    token = {"present": os.path.exists(token_path)}
    if token["present"]:
        token.update(json.load(open(token_path, encoding="utf-8")))
    import decision_gate
    html = (TEMPLATE
            .replace("__GODCHECK__", json.dumps(report))
            .replace("__REGISTRY__", json.dumps(registry))
            .replace("__SIM__", json.dumps(sim))
            .replace("__AUDIT__", json.dumps(audit))
            .replace("__ROUTELOG__", json.dumps(routelog))
            .replace("__HERETIC__", json.dumps(heretic_slot.status()))
            .replace("__RUNGS__", json.dumps([(n, s) for n, s, _ in decision_gate.RUNGS]))
            .replace("__TOKEN__", json.dumps(token))
            .replace("__SEATS__", json.dumps(json.load(
                open(os.path.join(HERE, "crew_seats.json"), encoding="utf-8"))["seats"])))
    out = os.path.join(HERE, "dashboard", "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"dashboard written: {out} ({len(html)} bytes, "
          f"checked_at={report['checked_at']}, sim events={len(sim)}, "
          f"route records={len(routelog)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
