"""Central config — reads from .env automatically."""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

def _e(k: str, d: str = "") -> str:
    return os.environ.get(k, d).strip()

# ── LLM ─────────────────────────────────────────────────────────────────────
GROQ_API_KEY:        str = _e("GROQ_API_KEY")
LLM_MODEL:           str = _e("LLM_MODEL", "llama-3.3-70b-versatile")
AEGIS_PROJECT_KEY:   str = _e("AEGIS_PROJECT_KEY")
AEGIS_MODE:          str = _e("AEGIS_MODE", "enforce")   # enforce | monitoring

# ── Supabase ─────────────────────────────────────────────────────────────────
SUPABASE_URL:        str = _e("SUPABASE_URL")
SUPABASE_KEY:        str = _e("SUPABASE_KEY")

# ── WhatsApp (Meta Cloud API) ─────────────────────────────────────────────────
WA_PHONE_ID:         str = _e("WHATSAPP_PHONE_ID")
WA_ACCESS_TOKEN:     str = _e("WHATSAPP_ACCESS_TOKEN")
WA_VERIFY_TOKEN:     str = _e("WHATSAPP_VERIFY_TOKEN", "aegisbot-verify")
WA_APP_SECRET:       str = _e("WHATSAPP_APP_SECRET")

# ── Business ─────────────────────────────────────────────────────────────────
BUSINESS_NAME:       str = _e("BUSINESS_NAME", "Our Business")
BUSINESS_LOCATION:   str = _e("BUSINESS_LOCATION", "")
BUSINESS_HOURS:      str = _e("BUSINESS_HOURS", "")
BUSINESS_PHONE:      str = _e("BUSINESS_PHONE", "")

# ── Staff & CRM notifications ────────────────────────────────────────────────
STAFF_NUMBER:        str = _e("STAFF_NUMBER")       # WhatsApp number for lead alerts
CRM_WEBHOOK_URL:     str = _e("CRM_WEBHOOK_URL")    # Webhook for Google Sheets / CRM / Zapier

# ── Feature flags ────────────────────────────────────────────────────────────
DISPATCH_SYNC:       bool = _e("DISPATCH_SYNC", "true") == "true"

@property
def llm_ready() -> bool:
    return bool(GROQ_API_KEY)
