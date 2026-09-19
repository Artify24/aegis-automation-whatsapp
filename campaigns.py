"""Broadcast campaigns and automated follow-up re-engagement engine."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import config
import db
import whatsapp

logger = logging.getLogger("aegisbot.campaigns")


def send_broadcast(text: str, filter_status: Optional[str] = None) -> Dict[str, Any]:
    """Send a promotional broadcast or announcement to captured leads."""
    leads = db.list_leads(limit=1000)
    recipients = []
    seen_numbers = set()

    for l in leads:
        wa_id = l.get("wa_id") or l.get("phone")
        if not wa_id or wa_id in seen_numbers:
            continue
        if filter_status and l.get("status") != filter_status:
            continue
        seen_numbers.add(wa_id)
        recipients.append({
            "wa_id": wa_id,
            "name": l.get("name") or "Valued Customer",
            "customer_id": l.get("customer_id", 0),
        })

    sent_count = 0
    for r in recipients:
        personalized = text.replace("{{name}}", r["name"].split()[0])
        success = whatsapp.send_message(r["wa_id"], personalized)
        if success:
            db.add_message(r["wa_id"], "out", personalized, sender="broadcast", customer_id=r["customer_id"])
            sent_count += 1

    logger.info("Broadcast dispatched to %d / %d recipients", sent_count, len(recipients))
    return {
        "ok": True,
        "total_targets": len(recipients),
        "sent_count": sent_count,
        "message_preview": text[:100],
    }


def trigger_abandoned_followups() -> Dict[str, Any]:
    """Check for stalled lead collection flows and send automated follow-up nudges."""
    try:
        client = db._db()
        # Find conversations with state containing flow: collecting
        res = client.table("conversations").select("*").execute()
        rows = res.data or []
        nudged = 0

        for row in rows:
            wa_id = row.get("wa_id")
            if not wa_id:
                continue
            try:
                state = json.loads(row.get("state") or "{}")
            except Exception:
                continue

            if state.get("flow") == "collecting" and not state.get("followup_sent"):
                fields = state.get("fields", {})
                name = (fields.get("name") or "").split()[0].title()
                interest = fields.get("interest") or "your requirement"

                greeting = f"Hi {name}! 👋 " if name else "Hi there! 👋 "
                nudge_msg = (
                    f"{greeting}Just checking in from *{config.BUSINESS_NAME}*! "
                    f"We're ready to prepare your custom quotation for {interest}. "
                    "Would you like to finish the quick details or connect with our sales team? 😊"
                )

                whatsapp.send_message(wa_id, nudge_msg)
                db.add_message(wa_id, "out", nudge_msg, sender="followup", customer_id=row.get("customer_id", 0))

                # Mark follow-up as sent
                state["followup_sent"] = True
                db.update_conversation(wa_id, json.dumps(state), customer_id=row.get("customer_id", 0))
                nudged += 1

        return {"ok": True, "followups_sent": nudged}
    except Exception as e:
        logger.error("Follow-up execution failed: %s", e)
        return {"error": str(e)}
