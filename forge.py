#!/usr/bin/env python3
"""
Ghildra Skill Forge — engagements become permanent, provenance-stamped
skills (Kali Fleet: OMEGA).

Pattern sources:
  * The Monster Arena skill books (empire/work/monster-arena/skills/):
    append-only Markdown books; every entry carries its Source and its
    Provenance; "everything learned is attached forever — never
    revoked, never silently dropped" (Boss's standing order,
    2026-10-21).
  * Ghildra's Grant (empire/work/jinwoo-shadow-army/): the storm
    dragon oversees the Skill Forge — she VERIFIES and QUARANTINES.
    A forged skill enters the book only through her keeping.

Enforced in code, not in prose:
  * Every skill is born QUARANTINED. It cannot enter a skill book
    until verify() moves it, and verify() requires a named verifier.
  * There is no un-verify and no delete: states move
    quarantined -> verified, one direction, and both files are
    append-only (existing bytes are never rewritten — write paths
    assert the old content is a strict prefix of the new).
  * Provenance is structural: name, learned_from (the engagement id),
    source (tool transcript reference), a SHA-256 of the transcript,
    forged_at, verified_by. A skill without complete provenance is
    rejected at forge time.
  * Duplicate names in the same book are rejected — the registry of
    what exists is the book itself.

A transcript is a list of step dicts (tool/action/result summaries) —
the forge records the transcript's hash and the tool sequence, not a
raw dump, so a skill book never becomes a leak surface.

Stdlib only.
"""

import hashlib
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BOOK_DIR = os.path.join(HERE, "skills")

STATES = ("quarantined", "verified")


class ForgeError(ValueError):
    pass


def _slug(name):
    return "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")


def transcript_facts(transcript):
    if not isinstance(transcript, list) or not transcript:
        raise ForgeError("transcript must be a non-empty list of steps")
    blob = json.dumps(transcript, sort_keys=True).encode("utf-8")
    tools = []
    for step in transcript:
        t = step.get("tool") or step.get("action")
        if not t:
            raise ForgeError("every transcript step needs a tool/action")
        if t not in tools:
            tools.append(t)
    return {"sha256": hashlib.sha256(blob).hexdigest(),
            "steps": len(transcript), "tools": tools}


def forge_skill(name, transcript, learned_from, source):
    """Create a skill in its birth state: QUARANTINED, unverified.
    Provenance is mandatory and complete, or this raises."""
    if not name or not learned_from or not source:
        raise ForgeError("name, learned_from and source are all required "
                         "— provenance is not optional")
    facts = transcript_facts(transcript)
    return {"name": name, "slug": _slug(name),
            "learned_from": learned_from, "source": source,
            "transcript_sha256": facts["sha256"],
            "transcript_steps": facts["steps"], "tools": facts["tools"],
            "forged_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "verified_by": None, "verified_at": None,
            "state": "quarantined"}


def verify(skill, verified_by):
    """Ghildra's keeping: quarantined -> verified, by a named verifier.
    One direction only; re-verifying or verifying a verified skill
    raises — the record does not get rewritten."""
    if not verified_by:
        raise ForgeError("verify() requires a named verifier")
    if skill["state"] != "quarantined":
        raise ForgeError(f"skill '{skill['name']}' is {skill['state']} — "
                         f"only a quarantined skill can be verified")
    out = dict(skill, state="verified", verified_by=verified_by,
               verified_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
    return out


def _entry_md(skill):
    lines = [f"### {skill['name']}",
             f"- _State:_ {skill['state']}",
             f"- _Learned from:_ {skill['learned_from']}",
             f"- _Source:_ {skill['source']}",
             f"- _Tools:_ {', '.join(skill['tools'])}",
             f"- _Transcript:_ {skill['transcript_steps']} steps, "
             f"sha256 {skill['transcript_sha256'][:16]}…",
             f"- _Forged:_ {skill['forged_at']}"]
    if skill["state"] == "verified":
        lines.append(f"- _Verified by:_ {skill['verified_by']} "
                     f"({skill['verified_at']}) — Ghildra's keeping")
    lines.append(f"- _Provenance:_ Forged by the Ghildra Skill Forge from "
                 f"{skill['learned_from']}; append-only, never revoked.")
    return "\n".join(lines) + "\n\n"


def _append(path, text):
    old = ""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            old = f.read()
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)
    with open(path, "r", encoding="utf-8") as f:
        new = f.read()
    if not new.startswith(old):
        raise ForgeError(f"append-only violated for {path}")


def file_skill(skill, book_dir=None):
    """File a skill where its state says it belongs: verified skills
    into skills/<owner-book>.md, quarantined skills into
    skills/QUARANTINE.md. A quarantined skill can NEVER be filed into
    a book — that is the forge's whole law. Returns the path written."""
    book_dir = book_dir or os.environ.get("OMEGA_SKILL_DIR") or DEFAULT_BOOK_DIR
    os.makedirs(book_dir, exist_ok=True)
    if skill["state"] == "verified":
        path = os.path.join(book_dir, "fleet-skills.md")
    elif skill["state"] == "quarantined":
        path = os.path.join(book_dir, "QUARANTINE.md")
    else:
        raise ForgeError(f"unknown skill state {skill['state']!r}")
    existing = ""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()
    if f"### {skill['name']}\n" in existing:
        raise ForgeError(f"skill '{skill['name']}' already filed in {path} "
                         f"— append-only books take no duplicates")
    header = ""
    if not existing:
        header = ("# Fleet Skill Book — Ghildra Skill Forge\n\n"
                  "_Append-only. Everything learned is attached forever._\n\n"
                  if skill["state"] == "verified" else
                  "# QUARANTINE — unverified forged skills\n\n"
                  "_Nothing here is a skill yet. Verification moves a skill "
                  "to the book; nothing leaves quarantine any other way._\n\n")
    _append(path, header + _entry_md(skill))
    return path


if __name__ == "__main__":
    demo = forge_skill(
        "Loopback Listener Census",
        [{"tool": "listening_ports", "result": "dry-run plan recorded"},
         {"tool": "log_triage", "result": "0 critical lines"}],
        learned_from="sim-engagement-0001",
        source="sim/transcript.jsonl (SIMULATION)")
    print(json.dumps(demo, indent=2))


# Zero-Trust Verification Layer — this module's clause.
VERIFICATION = {'clause': 'provenance-chain-validates', 'origin': 'empire-doctrine (zero-trust law 2: provenance or it did not happen)', 'check': 'verify_all.py forge clause + test_omega.py: born quarantined, named verifier required, append-only prefix proof, duplicate rejected'}
