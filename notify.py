"""Lead and handover alert dispatcher.

Supports:
  1. Instant WhatsApp alert to business owner / sales team (STAFF_NUMBER)
  2. Webhook trigger to CRM / Google Sheets / Zapier / Make (CRM_WEBHOOK_URL)
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Dict

import httpx
import config
import whatsapp

logger = logging.getLogger("aegisbot.notify")


def notify_new_lead(lead: Dict[str, Any]) -> None:
    """Send notifications asynchronously when a new lead is captured."""
    threading.Thread(target=_dispatch_lead_alert, args=(lead,), daemon=True).start()


def notify_handover(customer: Dict[str, Any], message: str = "") -> None:
    """Send notification when a customer requests human staff."""
    threading.Thread(target=_dispatch_handover_alert, args=(customer, message), daemon=True).start()


def _dispatch_lead_alert(lead: Dict[str, Any]) -> None:
    name = lead.get("name") or "Unnamed Lead"
    phone = lead.get("phone") or lead.get("wa_id") or "Unknown"
    budget = lead.get("budget") or "Flexible / Not specified"
    interest = lead.get("interest") or "General Inquiry"
    location = lead.get("location") or "Not specified"
    timeline = lead.get("timeline") or "Not specified"
    score = lead.get("score", 0)
    qualified = "🔥 HOT LEAD" if lead.get("qualified") else "📋 New Lead"

    # 1. Staff WhatsApp Notification
    if config.STAFF_NUMBER:
        alert_msg = (
            f"🚨 *{qualified} CAPTURED!* 🚨\n\n"
            f"👤 *Name:* {name}\n"
            f"📞 *Phone:* +{phone}\n"
            f"📦 *Interest:* {interest}\n"
            f"💰 *Budget:* {budget}\n"
            f"📍 *Location:* {location}\n"
            f"⏱️ *Timeline:* {timeline}\n"
            f"⭐ *Score:* {score}/100\n\n"
            f"⚡ *Quick Action:* Open WhatsApp chat: https://wa.me/{phone}"
        )
        try:
            whatsapp.send_message(config.STAFF_NUMBER, alert_msg)
            logger.info("Sent WhatsApp lead alert to staff %s", config.STAFF_NUMBER)
        except Exception as e:
            logger.error("Failed to send staff WhatsApp alert: %s", e)

    # 2. CRM / Webhook notification (Zapier, Google Sheets, Make, HubSpot)
    crm_webhook = getattr(config, "CRM_WEBHOOK_URL", "")
    if crm_webhook:
        payload = {
            "event": "new_lead",
            "business": config.BUSINESS_NAME,
            "lead": lead,
        }
        try:
            r = httpx.post(crm_webhook, json=payload, timeout=10)
            logger.info("Dispatched lead webhook to %s (HTTP %s)", crm_webhook, r.status_code)
        except Exception as e:
            logger.error("CRM webhook dispatch failed: %s", e)


def _dispatch_handover_alert(customer: Dict[str, Any], message: str) -> None:
    wa_id = customer.get("wa_id", "")
    name = customer.get("name") or wa_id
    if config.STAFF_NUMBER:
        alert_msg = (
            f"👨‍💼 *HUMAN AGENT REQUESTED!* 👨‍💼\n\n"
            f"Customer: *{name}* (+{wa_id})\n"
            f"Last message: \"{message}\"\n\n"
            f"👉 Join chat: https://wa.me/{wa_id}"
        )
        try:
            whatsapp.send_message(config.STAFF_NUMBER, alert_msg)
            logger.info("Sent human handover alert to staff %s", config.STAFF_NUMBER)
        except Exception as e:
            logger.error("Failed to send staff handover alert: %s", e)
