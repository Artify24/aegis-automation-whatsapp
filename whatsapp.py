"""Meta WhatsApp Cloud API sender."""
from __future__ import annotations

import logging
from typing import List, Optional

import httpx
import config

logger = logging.getLogger("aegisbot.whatsapp")

_GRAPH_URL = "https://graph.facebook.com/v19.0"


def send_text(to: str, text: str) -> bool:
    """Send a plain-text WhatsApp message. Returns True on success."""
    if not config.WA_PHONE_ID or not config.WA_ACCESS_TOKEN:
        safe = text.encode("ascii", "replace").decode("ascii")
        logger.warning("WhatsApp not configured -- [->%s] %s", to, safe)
        print(f"[MOCK -> {to}] {safe}")
        return True

    url = f"{_GRAPH_URL}/{config.WA_PHONE_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text, "preview_url": False},
    }
    headers = {
        "Authorization": f"Bearer {config.WA_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            logger.info("Sent to %s ✓", to)
            return True
        logger.error("WA send failed %s: %s", r.status_code, r.text[:200])
        return False
    except Exception as e:
        logger.error("WA send exception: %s", e)
        return False


def send_message(to: str, text: str) -> bool:
    """Convenience alias for send_text."""
    return send_text(to, text)


def send_interactive_buttons(to: str, body_text: str, buttons: List[dict]) -> bool:
    """Send up to 3 clickable quick-reply buttons on WhatsApp.

    buttons format: [{"id": "btn_1", "title": "Option Title"}]
    """
    if not config.WA_PHONE_ID or not config.WA_ACCESS_TOKEN:
        titles = ", ".join(f"[{b.get('title')}]" for b in buttons)
        logger.warning("WhatsApp mock buttons -- [->%s] %s %s", to, body_text[:60], titles)
        print(f"[MOCK BUTTONS -> {to}] {body_text} | {titles}")
        return True

    url = f"{_GRAPH_URL}/{config.WA_PHONE_ID}/messages"
    action_buttons = [
        {
            "type": "reply",
            "reply": {"id": b.get("id", f"btn_{i}"), "title": b.get("title", "")[:20]},
        }
        for i, b in enumerate(buttons[:3])
    ]

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body_text},
            "action": {"buttons": action_buttons},
        },
    }
    headers = {
        "Authorization": f"Bearer {config.WA_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=15)
        return r.status_code == 200
    except Exception as e:
        logger.error("Failed to send interactive buttons: %s", e)
        return False


def download_media(media_id: str) -> Optional[bytes]:
    """Download media bytes (e.g. voice notes, audio, images) from Meta Graph API."""
    if not config.WA_ACCESS_TOKEN:
        return None
    try:
        headers = {"Authorization": f"Bearer {config.WA_ACCESS_TOKEN}"}
        # 1. Get media URL
        r1 = httpx.get(f"{_GRAPH_URL}/{media_id}", headers=headers, timeout=15)
        if r1.status_code != 200:
            return None
        media_url = r1.json().get("url")
        if not media_url:
            return None
        # 2. Download binary content
        r2 = httpx.get(media_url, headers=headers, timeout=30)
        return r2.content if r2.status_code == 200 else None
    except Exception as e:
        logger.error("Failed to download media %s: %s", media_id, e)
        return None


def send_all(to: str, messages: List[str]) -> None:
    for m in messages:
        send_text(to, m)
