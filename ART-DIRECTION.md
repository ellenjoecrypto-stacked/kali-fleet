# ART DIRECTION — KALI FLEET: OMEGA / Connector God System

**Status:** Enforceable spec. Every visual surface of this project — dashboard,
README art, demo, Devpost media — obeys this file. If an asset violates a rule
below, it does not ship.

Staged 2026-10-30 for the Nebius × NVIDIA hackathon final project.

---

## 1. The look in one line

Matte-black void, neon jade circuitry, ember-orange edge heat, blood red held
in reserve for danger only. Cyberpunk street-tech crossed with Guilty Gear
character-select energy: sharp angles, dramatic rim light, everything looks
like it was selected, not rendered by a template.

## 2. Palette (locked)

| Token | Hex | Role |
|---|---|---|
| `--void` | `#050607` | Base background. Matte black, near-true-black. Everything sits on this. |
| `--void-2` | `#0b0e0c` | Raised panels / cards on the void base. |
| `--jade` | `#39ff6a` | PRIMARY. Neon green: active states, primary accents, sigil, live indicators, links, key data highlights. |
| `--ember` | `#ff6a00` | SECONDARY. Ember orange: edge glow, heat, warnings-that-aren't-danger, secondary accents, hover heat. |
| `--blood` | `#e10600` | DANGER ONLY. Gates, blocks, kill-switches, denied routes, destructive actions. Never decorative. |
| `--steel` | `#9aa7a1` | Body text secondary, labels, metadata. |
| `--steel-bright` | `#e8f0ec` | Primary text on void. |
| `--steel-dim` | `#5c6862` | Disabled states, timestamps, fine print. |
| `--line` | `#1d2621` | Hairline borders, grid lines, panel separation. |

Rules:
- No other accent colors. If a state needs a color, it maps to jade (go/live),
  ember (attention/heat), or blood (danger/gated). There is no fourth state.
- Blood red appears ONLY where something is genuinely dangerous, blocked, or
  gated. A screen where red is decoration is a screen that lies.
- Ember is an edge and glow color, not a fill color. Large ember surfaces are
  forbidden.
- Jade glow is used sparingly: one glowing element per visual field draws the
  eye. Five glowing elements draw nothing.

## 3. CSS variables (paste verbatim)

```css
:root {
  /* KALI FLEET: OMEGA — Connector God System palette (locked) */
  --void: #050607;
  --void-2: #0b0e0c;
  --jade: #39ff6a;
  --jade-dim: rgba(57, 255, 106, 0.14);
  --ember: #ff6a00;
  --ember-dim: rgba(255, 106, 0, 0.14);
  --blood: #e10600;
  --blood-dim: rgba(225, 6, 0, 0.14);
  --steel: #9aa7a1;
  --steel-bright: #e8f0ec;
  --steel-dim: #5c6862;
  --line: #1d2621;

  --font-display: "JetBrains Mono", "IBM Plex Mono", ui-monospace, monospace;
  --font-header: "Archivo", "Oswald", "Arial Narrow", sans-serif;
  --font-body: "Inter", system-ui, sans-serif;

  --glow-jade: 0 0 12px rgba(57, 255, 106, 0.45);
  --glow-ember: 0 0 12px rgba(255, 106, 0, 0.4);
  --angle-cut: 10px; /* signature corner cut for panels/buttons */
}
```

## 4. Typography

- **Data is monospace.** Numbers, states, routes, logs, timestamps, connector
  names in grids: monospace display type (`--font-display`). Data that isn't
  monospace is a bug.
- **Headers are condensed uppercase.** Tracking tight or slightly wide,
  never lowercase, never sentence case. "CONNECTOR GOD SYSTEM", not
  "Connector God System".
- Body text: clean sans (`--font-body`), steel or steel-bright only.
- No script fonts, no rounded friendly fonts, no serif display faces.

## 5. Shape language

- **Sharp angles only.** Panels and buttons use the signature corner cut
  (`clip-path` notch or `--angle-cut` chamfer). Rounded corners above 4px are
  forbidden except on circular indicators/avatars.
- Diagonal energy: header bars, dividers, and sigil geometry lean on
  45°/parallelogram cuts — character-select screen language.
- Thin hairlines (`--line`) over shadows. Depth comes from layered void
  tones and rim glow, not drop shadows.

## 6. Texture & imagery

- Subtle dragon-scale texture is the house surface texture — dark-on-dark,
  felt more than seen. Never glossy, never literal dragon artwork.
- Imagery is graphic/emblematic: sigils, node graphs, circuit traces,
  fleet formations. **No stock-photo look** — no smiling teams, no
  handshake photos, no generic server-room photography.
- Backgrounds stay void. Any image placed on the page sits on `#050607`
  or is itself void-based.

## 7. Hard rules (violations do not ship)

1. **No light mode.** Not as a theme, not as a toggle, not in screenshots.
2. **No corporate pastel.** No soft blues, no friendly gradients, no
   SaaS-illustration style.
3. **No invented numbers.** Art, banners, and screenshots show no stats,
   counts, percentages, or benchmarks that are not real and sourced.
   Text in project art is limited to the project names — "KALI FLEET: OMEGA"
   and "CONNECTOR GOD SYSTEM" — unless the text is real product UI copy.
4. **Glow is rationed.** See §2. Neon is an accent, not a floodlight.
5. **Red means danger.** If it isn't a gate, a block, or a kill condition,
   it isn't red.
6. **The sigil is the sigil.** The fleet-diamond emblem — networked nodes
   forming an angular diamond/omega formation — is used unmodified in
   shape; recoloring outside the palette is forbidden.

## 8. Assets

| File | Spec |
|---|---|
| `assets/banner.png` | Wide banner (16:9 or wider). Void field, jade sigil with ember edge glow, dragon-scale texture, "KALI FLEET: OMEGA" headline + "CONNECTOR GOD SYSTEM" subline. |
| `assets/logo.png` | Square. The sigil alone, centered, no text. Must read at 32px. |

Generation prompts for both are preserved in `assets/PROMPTS.md` if the
rendered assets ever need to be regenerated identically in spirit.
