"""LLM client — Groq via aegis-security-sdk with direct Groq fallback.

Flow:
  message → aegis.run(prompt) → Groq reply  [primary]
  if aegis fails → direct Groq REST         [fallback]
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
from typing import Any, Dict, Optional

import config

logger = logging.getLogger("aegisbot.llm")

# ── Aegis lazy singleton ──────────────────────────────────────────────────────

_aegis_mod: Any = None


def _get_aegis_mod():
    global _aegis_mod
    if _aegis_mod is None:
        try:
            import aegis as _m
            _aegis_mod = _m
            logger.info("aegis-security-sdk loaded")
        except Exception as e:
            logger.warning("aegis-security-sdk unavailable (%s) -- using direct Groq", e)
            _aegis_mod = False
    return _aegis_mod if _aegis_mod else None


# ── Async event loop (background thread) ────────────────────────────────────

_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_lock = threading.Lock()


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is None:
        with _loop_lock:
            if _loop is None:
                loop = asyncio.new_event_loop()
                t = threading.Thread(target=loop.run_forever, daemon=True, name="aegis-loop")
                t.start()
                _loop = loop
    return _loop


def _run_async(coro_fn, timeout: float = 60.0) -> Any:
    future = asyncio.run_coroutine_threadsafe(coro_fn(), _get_loop())
    return future.result(timeout=timeout)


# ── Aegis agent (one per model, cached) ──────────────────────────────────────

_agents: Dict[str, Any] = {}
_agent_lock = asyncio.Lock()


async def _ensure_agent(model: str) -> Any:
    a = _get_aegis_mod()
    if a is None:
        raise RuntimeError("aegis unavailable")
    key = model
    agent = _agents.get(key)
    if agent and getattr(agent, "is_running", False):
        return agent
    async with _agent_lock:
        agent = _agents.get(key)
        if agent and getattr(agent, "is_running", False):
            return agent
        provider = a.GroqProvider(model_id=model, api_key=config.GROQ_API_KEY)
        agent = (
            a.Aegis(name="aegisbot-wa")
            .with_provider(provider)
            .with_system_prompt(
                f"You are {config.BUSINESS_NAME}, a friendly WhatsApp sales assistant. "
                "Keep replies to 2-4 lines max. "
                "Never invent prices, policies or facts not given to you."
            )
        )
        await agent.initialize()
        await agent.start()
        _agents[key] = agent
        logger.info("Aegis agent ready (model=%s)", model)
        return agent


async def _aegis_run(prompt: str, model: str) -> str:
    agent = await _ensure_agent(model)
    result = await agent.run(prompt)
    return str(getattr(result, "output", result) or "").strip()


# ── Public generate() ─────────────────────────────────────────────────────────

def generate(prompt: str) -> Optional[str]:
    """Run prompt → return text. Never raises. Returns None on failure/block."""
    if not config.GROQ_API_KEY:
        logger.warning("No GROQ_API_KEY set")
        return None

    model = config.LLM_MODEL

    # Try aegis SDK first
    a = _get_aegis_mod()
    if a:
        try:
            text = _run_async(lambda: _aegis_run(prompt, model), timeout=3.0)
            if text:
                return text
        except Exception as e:
            err = str(e)
            if any(w in err for w in ("Blocked", "Policy", "Validation", "Approval", "BLOCKED")):
                logger.warning("Aegis BLOCKED prompt")
                return None
            logger.warning("Aegis error, using Groq direct: %s", err[:120])

    # Fallback: direct Groq
    return _groq_direct(prompt, model)


def _groq_direct(prompt: str, model: str) -> Optional[str]:
    try:
        from groq import Groq
        client = Groq(api_key=config.GROQ_API_KEY)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are {config.BUSINESS_NAME}, a friendly WhatsApp business and sales assistant. "
                        "Keep replies concise (2-4 lines). Never invent facts. "
                        "Language Rule: Automatically respond in the SAME language, script, or dialect the customer uses "
                        "(e.g., English, Hindi, Hinglish, Spanish, Arabic, etc.). "
                        "Always keep product names, prices, and numbers strictly accurate from official documents."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text or None
    except Exception as e:
        logger.error("Groq direct failed: %s", e)
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_json(text: Optional[str]) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    # strip <think>...</think> blocks (Qwen3 reasoning)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    try:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass
    return None


# ── Intent classification ─────────────────────────────────────────────────────

_LABELS = ["lead_info", "price_faq", "business_info", "order", "booking", "human", "greeting", "other"]

_INTENT_PROMPT = (
    "Classify the customer message into EXACTLY ONE intent. "
    f"Labels: {', '.join(_LABELS)}. "
    'Return ONLY JSON: {"intent": "<label>"}. '
    "lead_info=sharing name/budget/location/requirement; "
    "price_faq=asking price/rates; "
    "business_info=address/hours/contact; "
    "order=wants to buy; booking=wants appointment; "
    "human=wants staff; greeting=hi/hello/help; other=anything else."
)


def classify_intent(text: str) -> str:
    out = _groq_direct(f"{_INTENT_PROMPT}\n\nCustomer: {text[:600]}", config.LLM_MODEL)
    parsed = _parse_json(out)
    intent = (parsed or {}).get("intent", "")
    return intent if intent in _LABELS else "other"


# ── Entity extraction ─────────────────────────────────────────────────────────

_ENTITY_PROMPT = (
    "Extract buying facts the customer explicitly mentioned. "
    'Return ONLY JSON: {"name":"","budget":"","timeline":"","location":"","interest":""}. '
    "Use empty string if not mentioned. No guessing."
)


def extract_entities(text: str) -> Dict[str, str]:
    out = _groq_direct(f"{_ENTITY_PROMPT}\n\nCustomer: {text[:600]}", config.LLM_MODEL)
    parsed = _parse_json(out) or {}
    return {k: str(parsed.get(k, "")).strip()[:160] for k in ("name", "budget", "timeline", "location", "interest")}


# ── Answer generation ─────────────────────────────────────────────────────────

def answer(question: str, context: str = "") -> str:
    ctx = context.strip() or "No business documents loaded."
    prompt = (
        f"BUSINESS INFO:\n{ctx}\n\n"
        f"Customer question: {question}\n\n"
        "Answer in 2-4 short WhatsApp lines. "
        "If info is not in BUSINESS INFO, say so and offer to connect a human."
    )
    return generate(prompt) or "Let me connect you with our team for that. Type *human* and someone will help! "
