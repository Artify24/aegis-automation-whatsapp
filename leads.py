"""Lead capture flow — conversational state machine.

States:
  greeting   → ask first question
  collecting → fill fields one by one
  done       → lead saved to Supabase, conversation ends

Fields collected (in order):
  name → interest → budget → location → timeline
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import config
import db
import llm
import notify
import rag

logger = logging.getLogger("aegisbot.leads")

# ── Lead qualification threshold ──────────────────────────────────────────────
_QUALIFIED_SCORE = 60

# ── Field definitions (order matters) ─────────────────────────────────────────
_FIELDS: List[Tuple[str, str]] = [
    ("name",     "What's your name? 😊"),
    ("interest", "What are you looking for? Tell me a bit about what you need."),
    ("budget",   "What's your approximate budget? (e.g. Rs 10,000 or 'flexible')"),
    ("location", "Which area / city are you in?"),
    ("timeline", "When do you need this? (today, this week, next month…)"),
]

_FIELD_KEYS = [f for f, _ in _FIELDS]

# ── Buy-signal scoring ────────────────────────────────────────────────────────
_SCORE_WEIGHTS = {
    "name": 10, "interest": 20, "budget": 25, "location": 15, "timeline": 20,
}
_BUY_SIGNALS = [
    "buy", "purchase", "order", "book", "urgent", "asap", "today", "now",
    "price", "cost", "quote", "interested", "want", "need", "require",
    "looking for", "setup", "enquiry", "inquiry",
]


# ─────────────────────────────────────────────────── deterministic extractor ──

def _extract_deterministic(text: str) -> Dict[str, str]:
    """Rule-based field extraction — always runs, never calls LLM."""
    t = text.strip()
    low = " " + t.lower() + " "
    fields: Dict[str, str] = {}

    # name
    m = re.search(
        r"(?:my name is|i am|i'm|call me|this is)\s+([a-zA-Z][a-z]{1,30}(?:\s[a-zA-Z][a-z]{1,30})?)",
        low,
    )
    if m:
        fields["name"] = m.group(1).strip().title()[:60]

    # budget
    m = re.search(
        r"(?:budget|rs\.?|inr|rupees|around|approx|under|up to)\s*[\s:=]?\s*"
        r"([0-9][0-9,]*)(?:\.?\d{0,2})?\s*(k|thousand|lakh|l|cr|crore)?",
        low,
    )
    if m:
        raw = m.group(1).replace(",", "")
        try:
            val = float(raw)
        except ValueError:
            val = 0.0
        unit = (m.group(2) or "").lower()
        if unit.startswith("k") or "thousand" in unit:
            val *= 1_000
        elif unit.startswith("l"):
            val *= 1_00_000
        elif unit.startswith("c"):
            val *= 1_00_00_000
        if val >= 1_000:
            fields["budget"] = f"Rs {val:,.0f}"

    # timeline keywords
    for kw, label in [
        ("today",    "Today"),   ("tonight", "Tonight"), ("tomorrow",  "Tomorrow"),
        ("this week","This week"),("next week","Next week"),("asap",    "ASAP"),
        ("urgent",   "ASAP"),    ("this month","This month"),("next month","Next month"),
    ]:
        if kw in low:
            fields["timeline"] = label
            break

    # location
    m = re.search(
        r"\b(?:in|from|near|at|located in|based in|area of|city of)\s+([a-zA-Z][a-zA-Z .'-]{2,30})\b",
        low,
    )
    if m:
        fields["location"] = m.group(1).strip().title()[:60]

    # interest
    m = re.search(
        r"\b(?:looking for|interested in|need|want|require|for)\s+([a-z][a-z ]{2,60})\b", low
    )
    if m:
        interest = m.group(1).strip()
        if interest not in {"a price", "an estimate", "a quote", "help", "some help"}:
            fields["interest"] = interest[:100].title()

    return fields


def _merge(*dicts: Dict[str, str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    junk = {"my","i","i'm","me","the","a","an","this","that","we","user","and","or","is"}
    for d in dicts:
        for k, v in d.items():
            if not v:
                continue
            if k == "name":
                first = v.strip().split()[0].lower().rstrip(",.")
                if first in junk:
                    continue
            out[k] = v
    return out


# ─────────────────────────────────────────────────────────── scoring ──────────

def score(fields: Dict[str, str], text: str) -> int:
    s = sum(_SCORE_WEIGHTS.get(k, 0) for k, v in fields.items() if v)
    low = text.lower()
    if any(kw in low for kw in _BUY_SIGNALS):
        s += 10
    return min(100, s)


# ─────────────────────────────────────────────────────────── state helpers ────

def _save_state(wa_id: str, state: Dict[str, Any], customer_id: int = 0) -> None:
    db.update_conversation(wa_id, json.dumps(state), customer_id=customer_id)


def _next_question(fields: Dict[str, str]) -> Optional[str]:
    for key, question in _FIELDS:
        if not fields.get(key):
            return question
    return None


# ─────────────────────────────────────────────────────── flow entry points ────

def handle(wa_id: str, text: str, customer: Dict[str, Any]) -> List[str]:
    """Main entry point — routes greetings, FAQs, lead capture, and handovers."""
    raw = (text or "").strip()
    low = raw.lower()
    customer_id = customer.get("id", 0)

    # 1. Human handover escalation
    if any(k in low for k in ("human", "agent", "executive", "person", "representative", "speak to staff", "call me", "talk to human")):
        db.update_customer(wa_id, status="human_requested")
        notify.notify_handover(customer, raw)
        return [
            f"I've alerted our senior customer support team at *{config.BUSINESS_NAME}*! 👨‍💼📞\n\n"
            "An agent will take over this chat or call you shortly.\n"
            "You can also reach our direct support line at +91 80 4123 9999."
        ]

    state = db.get_conversation_state(wa_id)
    flow = state.get("flow")

    # 2. Reset / Restart requested
    if any(k in low for k in ("restart", "start again", "new inquiry", "new lead", "clear chat", "reset")):
        _save_state(wa_id, {}, customer_id=customer_id)
        return ["I've reset our conversation! What would you like to explore today? 😊"]

    # 3. If lead was already captured (flow == 'done')
    if flow == "done":
        faq_reply, has_match = rag.answer_faq(raw)
        if has_match:
            return [faq_reply]
        return [
            "You're all set! Our team will reach out soon. "
            "Feel free to ask any question about our products, pricing, or showroom anytime! 😊"
        ]

    # 4. If currently in middle of lead capture:
    if flow == "collecting":
        # Check if customer interrupted with an FAQ question
        is_question = "?" in raw or any(low.startswith(w) for w in (
            "what", "where", "how", "when", "why", "do you", "is there", "can you", "which", "are you", "tell me"
        ))
        if is_question:
            faq_reply, has_match = rag.answer_faq(raw)
            if has_match:
                fields = dict(state.get("fields", {}))
                next_q = _next_question(fields)
                follow_up = f"\n\n---\n*By the way, to get you the right quotation:* {next_q}" if next_q else ""
                return [faq_reply + follow_up]

        return _continue(wa_id, raw, customer, state)

    # 5. Greeting / Cold start menu
    greetings = {"hi", "hello", "hey", "hola", "namaste", "good morning", "good afternoon", "good evening", "start", "menu", "help"}
    clean_words = set(re.sub(r"[^\w\s]", "", low).split())
    if clean_words.issubset(greetings) or low in greetings:
        return [
            f"Hi! 👋 Welcome to *{config.BUSINESS_NAME}*!\n\n"
            "I'm your 24/7 instant assistant. Here is how I can help:\n"
            "• 📋 *Get a Custom Quote & Layout*\n"
            "• 🪑 *Product Catalog & Pricing*\n"
            "• 📍 *Showroom Location & Timings*\n"
            "• 🚚 *Delivery & 3-Year Warranty Info*\n\n"
            "Tell me what you're looking for, or ask any question! 😊"
        ]

    # 6. Check RAG Knowledge Base
    faq_reply, has_match = rag.answer_faq(raw)
    has_buy_signals = any(sig in low for sig in _BUY_SIGNALS)

    if has_match:
        if has_buy_signals and not any(w in low for w in ("what", "where", "how", "timings", "hours", "location")):
            # Customer has clear buy intent alongside asking
            lead_replies = _start(wa_id, raw, customer)
            return [faq_reply + "\n\n" + lead_replies[0]]
        else:
            # Pure FAQ answer + warm follow-up CTA
            cta = "\n\n💡 *Need a quotation or bulk pricing?* Just tell me what you need and our team will prepare a custom offer!"
            return [faq_reply + cta]

    # 7. Start lead capture flow
    return _start(wa_id, raw, customer)


def _start(wa_id: str, text: str, customer: Dict[str, Any]) -> List[str]:
    """Initialise lead capture state and return first question."""
    det = _extract_deterministic(text)
    llm_ents = llm.extract_entities(text) if text.strip() else {}
    fields = _merge(det, llm_ents)
    fields.setdefault("interest", text[:160] if text.strip() else "")

    state: Dict[str, Any] = {
        "flow": "collecting",
        "fields": fields,
        "trigger": text[:400],
    }
    _save_state(wa_id, state, customer_id=customer.get("id", 0))

    greeting = (
        f"Hi! 👋 Welcome to *{__import__('config').BUSINESS_NAME}*! "
        "I'd love to help. Let me grab a few quick details.\n\n"
    )
    q = _next_question(fields)
    if q:
        return [greeting + q]
    # all fields already captured from first message
    return _finalise(wa_id, state, customer)


def _continue(wa_id: str, text: str,
              customer: Dict[str, Any], state: Dict[str, Any]) -> List[str]:
    """Continue collecting fields; finalise when all collected."""
    fields: Dict[str, str] = dict(state.get("fields", {}))

    # extract new info from this message
    det = _extract_deterministic(text)
    llm_ents = llm.extract_entities(text) if text.strip() else {}
    fields = _merge(fields, det, llm_ents)

    # explicit answer: fill the next empty field if no extractor caught it
    next_key = next((k for k in _FIELD_KEYS if not fields.get(k)), None)
    if next_key and text.strip() and _plausible(text, next_key):
        fields[next_key] = text.strip()[:200]

    state["fields"] = fields
    _save_state(wa_id, state, customer_id=customer.get("id", 0))

    q = _next_question(fields)
    if q:
        return [q]

    return _finalise(wa_id, state, customer)


def _plausible(text: str, field: str) -> bool:
    if len(text.strip()) < 2:
        return False
    if field == "budget" and not any(c.isdigit() for c in text):
        return False
    return True


def _finalise(wa_id: str, state: Dict[str, Any], customer: Dict[str, Any]) -> List[str]:
    """All fields collected — score, save to Supabase, notify."""
    fields = state.get("fields", {})
    trigger = state.get("trigger", "")
    s = score(fields, trigger)
    qualified = 1 if s >= _QUALIFIED_SCORE else 0

    customer_id = customer.get("id") or 0

    # ── update customer row ───────────────────────────────────────────────────
    db.update_customer(
        wa_id,
        name=fields.get("name", customer.get("name", "")),
        budget=fields.get("budget", ""),
        timeline=fields.get("timeline", ""),
        city=fields.get("location", ""),
        interest=fields.get("interest", ""),
        lead_score=s,
        qualified=qualified,
        status="qualified" if qualified else "lead",
    )

    # ── save lead to Supabase ─────────────────────────────────────────────────
    lead = db.create_lead(
        customer_id=customer_id,
        wa_id=wa_id,
        name=fields.get("name", ""),
        phone=fields.get("phone", customer.get("phone", wa_id)),
        interest=fields.get("interest", trigger[:160]),
        budget=fields.get("budget", ""),
        timeline=fields.get("timeline", ""),
        location=fields.get("location", ""),
        score=s,
        qualified=qualified,
        status="qualified" if qualified else "new",
        notes=f"trigger: {trigger[:200]}",
    )
    logger.info("Lead #%s saved — score=%s qualified=%s", lead.get("id"), s, qualified)
    notify.notify_new_lead(lead)

    # ── mark flow done ────────────────────────────────────────────────────────
    _save_state(wa_id, {"flow": "done"}, customer_id=customer_id)

    # ── compose reply ─────────────────────────────────────────────────────────
    name_parts = (fields.get("name") or "").split()
    first = name_parts[0].title() if name_parts else ""
    thanks = f"Thanks {first}! 🎉 " if first else "Thanks! 🎉 "

    if qualified:
        return [
            thanks + "We've got all your details. "
            "Our team will reach out to you very soon with the best offer. "
            "Expect a message or call within a few hours! 🚀"
        ]
    return [
        thanks + "We've noted everything down! "
        "We'll keep you updated with helpful info. "
        "Feel free to ask anything — I'm here 24/7. 😊"
    ]
