#!/usr/bin/env python3
"""
HF Brain — the Hugging Face rung of every crew seat's brain ladder
(Kali Fleet: OMEGA).

Boss's order (2026-10-30): "HF brains for all." Each crew seat gets a
Hugging Face Inference API brain, assigned per member in
crew_seats.json. Model names were verified against the live HF API on
2026-10-30: every assigned model exists and is UNGATED (gated: false).
The assignments favor small instruct models (Qwen2.5-7B class) so a
seat's brain is cheap and fast; deep seats (Senku) get the reasoning
distill on record.

THE LADDER (per member, in order): HF -> OpenRouter -> Zen ->
local Ollama -> heuristic floor. A member DEGRADES, never dies: each
rung either answers or raises, the ladder falls through, and the
floor answers with an honestly-labeled non-model response (the
crew_llm pattern: "answering from the charter, not the model").

TOKEN DISCIPLINE: the HF token comes from env HF_TOKEN ONLY. Absent
=> the HF rung raises KeyPending BEFORE any network is attempted.
State until a token exists: KEY-PENDING (HF_TOKEN via Secure Vault) —
wired, fake-transport tested, honest. No other credential is read,
ever, and token values never appear in returns or logs.

Stdlib only (urllib for the real transport).
"""

import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

HF_ENDPOINT = "https://api-inference.huggingface.co/models/{model}"
LADDER = ("hf", "openrouter", "zen", "ollama-local", "heuristic-floor")


class KeyPending(Exception):
    """The rung's credential physically does not exist on this machine."""


class RungDown(Exception):
    """A rung was tried and failed; the ladder falls through."""


def seats():
    with open(os.path.join(HERE, "crew_seats.json"), encoding="utf-8") as f:
        return json.load(f)["seats"]


def assignment(member):
    for s in seats():
        if s["member"] == member:
            return s
    raise KeyError(f"no crew seat named {member!r}")


def hf_transport(model, prompt, token, timeout=30):
    """The real HF Inference API call. Only invoked with a token in
    hand; tests inject fakes at the chat() seam instead."""
    req = urllib.request.Request(
        HF_ENDPOINT.format(model=model),
        data=json.dumps({"inputs": prompt,
                         "parameters": {"max_new_tokens": 256,
                                        "return_full_text": False}}).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except Exception as exc:
        # 401 / timeout / refused / malformed JSON — a dead rung, not a
        # dead call (Hu Tao §2: these used to escape chat()'s catch).
        raise RungDown(f"HF transport failed: {type(exc).__name__}: {exc}")
    if isinstance(data, list) and data and "generated_text" in data[0]:
        text = data[0]["generated_text"]
        if text and text.strip():
            return text
        raise RungDown(f"HF returned an empty completion for {model}")
    raise RungDown(f"HF reply in an unexpected shape for {model}")


def _env_transport(env_var, label):
    def call(member, prompt):
        if not os.environ.get(env_var):
            raise KeyPending(f"{label}: {env_var} not set on this machine")
        raise RungDown(f"{label}: live call path is the decision/crew "
                       f"stack's client; this adapter does not duplicate it")
    return call


def _ollama_transport(member, prompt):
    if not (os.environ.get("OMEGA_LOCAL_MODEL")
            or os.environ.get("DECISION_LAYER_LOCAL_MODEL")):
        raise KeyPending("ollama-local: no local model armed "
                         "(DECISION_LAYER_LOCAL_MODEL unset; Heretic chair EMPTY)")
    raise RungDown("ollama-local: endpoint probe is heretic_slot's job; "
                   "no served model is certified in this build")


def _floor(member, prompt):
    return (f"[{member} — heuristic floor, NOT a model] No brain rung is "
            f"fueled on this machine, so this seat answers from its "
            f"charter, not from a model. Prompt received ({len(prompt)} "
            f"chars); no inference was performed and none is claimed.")


DEFAULT_TRANSPORTS = {
    "hf": None,  # built per-member below (needs the assigned model)
    "openrouter": _env_transport("OPENROUTER_API_KEY", "openrouter"),
    "zen": _env_transport("OPENCODE_ZEN_API_KEY", "opencode-zen"),
    "ollama-local": _ollama_transport,
    "heuristic-floor": _floor,
}


def chat(member, prompt, transports=None, token=None):
    """Run the member's ladder. Returns {member, rung, model, text,
    fell_through}. Never raises for a down rung — the floor is the
    last rung and it always answers, labeled as what it is."""
    seat = assignment(member)
    transports = dict(DEFAULT_TRANSPORTS, **(transports or {}))
    fell = []
    for rung in seat["ladder"]:
        try:
            if rung == "hf":
                fn = transports.get("hf")
                if fn is not None:
                    text = fn(member, prompt)
                else:
                    tok = token or os.environ.get("HF_TOKEN")
                    if not tok:
                        raise KeyPending(
                            "HF: HF_TOKEN not set on this machine — "
                            "KEY-PENDING (deposit via Secure Vault)")
                    text = hf_transport(seat["hf_model"], prompt, tok)
            elif rung == "heuristic-floor":
                text = transports["heuristic-floor"](member, prompt)
            elif rung in transports:
                text = transports[rung](member, prompt)
            else:
                # Unknown rung name in a seat's ladder (the Hermes seat
                # shipped 'ollama-local (PC hermes3:8b)', matching no
                # transport): record and step down — never KeyError
                # (Hu Tao §4: that seat's floor was unreachable).
                fell.append(f"{rung}: unknown rung name — stepped down")
                continue
            return {"member": member, "rung": rung,
                    "model": seat["hf_model"] if rung == "hf" else rung,
                    "text": text, "fell_through": fell}
        except Exception as e:
            # ANY rung failure steps the ladder down (Hu Tao §2/§4).
            fell.append(f"{rung}: {e}")
            continue
    raise AssertionError("unreachable — the floor always answers")


VERIFICATION = {"clause": "key-pending-or-it-didnt-happen", "origin": "empire-doctrine (key-pending honesty)",
                "check": "test_crew.py: HF rung raises KeyPending with HF_TOKEN unset (no network attempted); fake transports prove ladder order HF -> OpenRouter -> Zen -> Ollama -> floor"}

if __name__ == "__main__":
    print(json.dumps(chat("Senku", "status?"), indent=2))
