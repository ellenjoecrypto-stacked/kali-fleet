#!/usr/bin/env python3
"""
Heretic Brain Slot — ladder rung (d), the Empire's own-weights chair
(Kali Fleet: OMEGA).

Implements the contract recorded in the decision layer's
HERETIC-INTEGRATION.md:

  * The rung is ARMED by naming a served local model:
    DECISION_LAYER_LOCAL_MODEL (here also OMEGA_LOCAL_MODEL). Unset,
    the slot is absent and nothing anywhere changes.
  * Endpoint: Ollama, DECISION_LAYER_OLLAMA_URL
    (default http://localhost:11434).
  * A candidate model exists only when a REAL Heretic run artifact
    exists: an Optuna journal at checkpoints/<model>.jsonl, or a study
    export JSON — the shapes heretic_gate.py consumes.

HONEST STATE TODAY: **EMPTY / PREP.** The smoke config
(empire/work/heretic-smoke/config.toml) is staged — it differs from
Heretic's canonical config by exactly two lines (n_trials 100->3,
n_startup_trials 30->3) — but no Heretic run has ever executed from
this project: the VM measured out (RAM, no GPU), the Colab route is
specced, and the run waits on the Boss's "go". No run artifact exists,
no model is served, and answer() therefore RAISES SlotEmpty. This slot
never fabricates an inference, a trial record, or a metric.

Stdlib only (tomllib for the config read).
"""

import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SMOKE_CONFIG = os.path.expanduser(
    "~/workspace/empire/work/heretic-smoke/config.toml")
DEFAULT_ARTIFACT_DIR = os.path.join(HERE, "heretic_artifacts")


class SlotEmpty(Exception):
    """The slot has no served model. Callers fall through — they never
    treat this as an answer."""


def smoke_config(path=None):
    """Parse the staged smoke config with tomllib. Returns the shape
    the slot (and the trial gate) cares about. Raises SlotEmpty if the
    config is absent or unparseable — a claim we cannot read is a
    config we do not have."""
    import tomllib
    path = path or os.environ.get("OMEGA_HERETIC_CONFIG") or DEFAULT_SMOKE_CONFIG
    try:
        with open(path, "rb") as f:
            cfg = tomllib.load(f)
    except (OSError, ValueError) as e:
        raise SlotEmpty(f"heretic smoke config unreadable: {e}")
    scorers = []
    for s in cfg.get("scorers", []):
        plugin = s.get("plugin", "")
        instance = s.get("instance_name")
        table = cfg.get("scorer", {})
        cls = plugin.rsplit(".", 1)[-1]
        key = cls + (f"_{instance}" if instance else "")
        # Heretic's recorded scorer names (HERETIC-INTEGRATION.md): the
        # config's score_name where set, else the class convention.
        name = table.get(key, {}).get(
            "score_name", {"KeywordRate": "Refusals",
                           "KLDivergence": "KL divergence"}.get(cls, plugin))
        scorers.append({"plugin": plugin, "score_name": name,
                        "optimization": s.get("optimization")})
    if not scorers:
        # The corrected smoke config uses Heretic's FLAT canon schema
        # (no [[scorers]] plugin tables — that was the superseded head
        # schema). Its two objectives are flat keys: refusal counting
        # (refusal_markers) and KL divergence (kl_divergence_*). Name
        # them from the keys that are actually present.
        if "refusal_markers" in cfg:
            scorers.append({"plugin": "heretic.config:refusal_markers",
                            "score_name": "Refusals", "optimization": None})
        if "kl_divergence_target" in cfg or "kl_divergence_scale" in cfg:
            scorers.append({"plugin": "heretic.config:kl_divergence",
                            "score_name": "KL divergence",
                            "optimization": None})
    return {"path": path,
            "n_trials": cfg.get("n_trials"),
            "n_startup_trials": cfg.get("n_startup_trials"),
            "quantization": cfg.get("quantization"),
            "scorers": scorers,
            "modifiers": [m.get("plugin") for m in cfg.get("modifiers", [])],
            "study_checkpoint_dir": cfg.get("study_checkpoint_dir")}


def find_run_artifacts(artifact_dir=None):
    """Real run artifacts only: Optuna journals + study export JSONs.
    Config files, notes, and this module's own paperwork do NOT count."""
    artifact_dir = artifact_dir or os.environ.get(
        "OMEGA_HERETIC_ARTIFACTS") or DEFAULT_ARTIFACT_DIR
    found = []
    for pat in ("checkpoints/*.jsonl", "*.jsonl", "study-export*.json",
                "trials*.json"):
        for p in sorted(glob.glob(os.path.join(artifact_dir, pat))):
            found.append(p)
    return found


def status(artifact_dir=None):
    """The slot's honest state: EMPTY (no artifacts, unarmed),
    PREP (config staged, still no artifacts), or CANDIDATE (a real
    artifact exists — still not 'live' until a model is actually
    served and the trial gate has disposed)."""
    try:
        cfg = smoke_config()
        cfg_ok = True
    except SlotEmpty:
        cfg, cfg_ok = None, False
    artifacts = find_run_artifacts(artifact_dir)
    armed_model = (os.environ.get("OMEGA_LOCAL_MODEL")
                   or os.environ.get("DECISION_LAYER_LOCAL_MODEL"))
    if artifacts:
        state = "CANDIDATE"
    elif cfg_ok:
        state = "PREP"
    else:
        state = "EMPTY"
    return {"state": state,
            "armed_model": armed_model,
            "ollama_url": os.environ.get("DECISION_LAYER_OLLAMA_URL",
                                         "http://localhost:11434"),
            "config": cfg,
            "artifacts": artifacts,
            "note": ("no Heretic run has executed from this project; "
                     "the run is Boss-gated ('go') and host-gated "
                     "(this VM measured out: RAM, no GPU)")}


def answer(questions, state):
    """Decision-layer rung (d) call shape. Raises SlotEmpty unless a
    model is armed AND a real run artifact exists — and even then it
    refuses to improvise: serving is the decision layer's Ollama
    backend's job; this slot only certifies the chair is occupied."""
    st = status()
    if st["state"] != "CANDIDATE" or not st["armed_model"]:
        raise SlotEmpty(
            f"heretic slot is {st['state']} — no served local model; "
            f"never fake an inference")
    raise SlotEmpty(
        "artifact present but no serving path wired in this build — "
        "route through the decision layer's ollama-local backend")


if __name__ == "__main__":
    print(json.dumps(status(), indent=2))


# Zero-Trust Verification Layer — this module's clause.
VERIFICATION = {'clause': 'prove-the-negative', 'origin': 'empire-doctrine (EMPTY-chair honesty: refuse rather than fabricate)', 'check': 'test_omega.py: status PREP with zero artifacts; answer() raises SlotEmpty — the slot proves it is empty rather than claiming a brain'}
