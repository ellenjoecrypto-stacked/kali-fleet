#!/usr/bin/env python3
"""
Nebius Token Factory client — Kali Fleet / Empire PC Agent.

OpenAI-compatible chat completions over stdlib urllib. No third-party deps.

Configuration comes from the environment ONLY — no key is ever hardcoded:
    TOKEN_FACTORY_API_KEY   the key (supplied by the owner via Secure Vault)
    TOKEN_FACTORY_BASE_URL  default: https://api.tokenfactory.nebius.com/v1
    TF_MODEL_FAST           intent parsing tier   (Nemotron 3 Nano class)
    TF_MODEL_PLAN           coordination/narration tier (Nemotron 3 Super class)
    TF_MODEL_DEEP           deep-reasoning tier   (Nemotron 3 Ultra class)

MODEL ID NOTICE: the hackathon research (RESEARCH.md) confirms the Nemotron 3
family (Nano 30B / Super 120B / Ultra 500B) is served on Token Factory, but
does not publish exact API model identifiers. The defaults below are
PLACEHOLDERS in the vendor/model style Token Factory uses — verify them
against the Token Factory model catalog the moment a real key lands, and
override via the TF_MODEL_* env vars above. No code change is needed.

MOCK MODE: when TOKEN_FACTORY_API_KEY is unset, the client never touches the
network. It returns clearly-labeled canned responses (every payload carries
"mock": true and model names prefixed "mock/"), including a small keyword
rule engine for intent parsing, so the full demo loop runs offline.
"""

import json
import os
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1"

# PLACEHOLDER model IDs — verify against the Token Factory catalog, override
# with the TF_MODEL_* environment variables. See the notice in the docstring.
MODEL_DEFAULTS = {
    "fast": "nvidia/nemotron-3-nano-30b",    # PLACEHOLDER — Nemotron 3 Nano class
    "plan": "nvidia/nemotron-3-super-120b",  # PLACEHOLDER — Nemotron 3 Super class
    "deep": "nvidia/nemotron-3-ultra-500b",  # PLACEHOLDER — Nemotron 3 Ultra class
}
TIER_ENV = {"fast": "TF_MODEL_FAST", "plan": "TF_MODEL_PLAN", "deep": "TF_MODEL_DEEP"}
TIER_LABEL = {"fast": "Nemotron 3 Nano class (fast parse)",
              "plan": "Nemotron 3 Super class (coordination / narration)",
              "deep": "Nemotron 3 Ultra class (deep reasoning)"}


class TokenFactoryError(RuntimeError):
    pass


class TokenFactoryClient:
    """Thin chat-completions client with an offline mock mode."""

    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key if api_key is not None else os.environ.get("TOKEN_FACTORY_API_KEY", "")
        self.base_url = (base_url or os.environ.get("TOKEN_FACTORY_BASE_URL")
                         or DEFAULT_BASE_URL).rstrip("/")
        self.models = {tier: os.environ.get(env, MODEL_DEFAULTS[tier])
                       for tier, env in TIER_ENV.items()}

    @property
    def mock_mode(self):
        return not self.api_key

    def model_for(self, tier):
        if tier not in self.models:
            raise TokenFactoryError(f"unknown tier '{tier}' (use fast|plan|deep)")
        return self.models[tier]

    # ------------------------------------------------------------------ API

    def chat(self, messages, tier="fast", temperature=0.2, max_tokens=800, timeout=60):
        """One chat completion. Returns a dict:
        {content, model, tier, mock, usage?}. Raises TokenFactoryError on
        transport/API failure in live mode."""
        model = self.model_for(tier)
        if self.mock_mode:
            return {"content": _mock_reply(messages, tier), "model": "mock/" + model,
                    "tier": tier, "mock": True}
        payload = {"model": model, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens}
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Authorization": "Bearer " + self.api_key,
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            raise TokenFactoryError(f"Token Factory HTTP {e.code}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TokenFactoryError(f"Token Factory unreachable: {e}") from e
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise TokenFactoryError("Token Factory returned an unexpected payload shape") from e
        return {"content": content, "model": body.get("model", model),
                "tier": tier, "mock": False, "usage": body.get("usage")}


# ---------------------------------------------------------------- mock brain
# Clearly-labeled canned intelligence so the demo runs with zero keys.
# The intent rules are deliberately simple keyword matching — a stand-in for
# the Nano-class model, NOT a claim of real inference.

_MOCK_INTENTS = (
    (("listening", "listen", "ports", "port"), {"action": "listening_ports", "args": {}}),
    (("interface", "network card", "ip address", "addresses"), {"action": "interfaces", "args": {}}),
    (("scan", "services running on", "service detection"), {"action": "nmap_scan", "args": {"target": "127.0.0.1"}}),
    (("log", "errors in", "triage"), {"action": "log_triage", "args": {"path": "sample.log"}}),
    (("system", "sysinfo", "about this machine", "hostname", "kernel", "os"), {"action": "sysinfo", "args": {}}),
)


def _mock_reply(messages, tier):
    user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user = m.get("content", "")
            break
    low = user.lower()
    if tier == "fast":
        for keywords, intent in _MOCK_INTENTS:
            hay = low
            # The parse call wraps the raw request text; match on keywords
            # that appear in the request portion of the prompt.
            if any(k in hay for k in keywords):
                out = dict(intent)
                if intent["action"] == "nmap_scan" and "127.0.0.1" not in low:
                    # Pull an explicit target out of the request if present.
                    for tok in low.replace(",", " ").split():
                        if tok.replace(".", "").isdigit() and tok.count(".") == 3:
                            out = {"action": "nmap_scan", "args": {"target": tok}}
                return json.dumps(out)
        return json.dumps({"action": "sysinfo", "args": {}})
    # Narration / planning tiers: deterministic, honest canned text.
    return ("[MOCK Nemotron — no Token Factory key configured] "
            "I routed the request through the Kali Fleet allow-list, ran the "
            "action in dry-run mode, and logged it to the audit trail. "
            "Result summary follows from the recorded action output.")


if __name__ == "__main__":
    c = TokenFactoryClient()
    print("mock_mode:", c.mock_mode)
    print("models:", json.dumps(c.models, indent=2))
    r = c.chat([{"role": "user", "content": "parse intent: what ports are listening?"}], tier="fast")
    print("sample fast-tier reply:", r["content"], f"(model={r['model']}, mock={r['mock']})")
