"""AegisBot Multi-Stage Automated Drip Campaign & Nurturing Engine.

Orchestrates time-delayed, multi-touch follow-up sequences to convert warm leads
into closed deals without human micromanagement.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import config
import db
import whatsapp

logger = logging.getLogger("aegisbot.drip")

# Nurture sequence definitions
DRIP_STAGES = [
    {
        "stage": 1,
        "name": "Site Inspection & Space Planning Offer",
        "delay_hours": 2,
        "template": (
            "Hi {{name}}! 👋 Following up on your requirement for *{{interest}}* at *{{business}}*. "
            "Did you know we offer complimentary 3D space planning and site measurement across {{location}}? "
            "Would you like our design engineer to visit your office this week?"
        ),
    },
    {
        "stage": 2,
        "name": "Executive PDF Quotation Follow-up",
        "delay_hours": 24,
        "template": (
            "Hi {{name}}! 😊 Hope your week is going well. "
            "Our corporate desk has prepared a customized quotation for your requirement (Budget: {{budget}}). "
            "Feel free to reply here if you'd like any adjustments to specifications or quantities!"
        ),
    },
    {
        "stage": 3,
        "name": "Limited-Time Commercial Discount",
        "delay_hours": 72,
        "template": (
            "Hi {{name}}! 🎁 Great news from *{{business}}*: "
            "Our management has approved an additional 10% corporate rebate on all ergonomic workstation orders placed before month-end. "
            "Would you like us to reserve your batch?"
        ),
    },
]


def run_drip_sequence(force_stage: Optional[int] = None) -> Dict[str, Any]:
    """Scan leads in Supabase and advance eligible leads along the drip funnel."""
    try:
        leads = db.list_leads(limit=500)
        client = db._db()
        dispatched = 0
        logs = []

        for l in leads:
            wa_id = l.get("wa_id") or l.get("phone")
            lead_id = l.get("id")
            if not wa_id:
                continue

            status = l.get("status", "new")
            if status in ("won", "lost"):
                continue  # Skip closed deals

            # Read conversation state
            conv_state = db.get_conversation_state(wa_id)
            current_stage = conv_state.get("drip_stage", 0)
            next_stage_num = force_stage if force_stage is not None else current_stage + 1

            # Check if there is a stage definition
            stage_def = next((s for s in DRIP_STAGES if s["stage"] == next_stage_num), None)
            if not stage_def:
                continue

            name = (l.get("name") or "Valued Customer").split()[0].title()
            interest = l.get("interest") or "office furniture"
            location = l.get("location") or "Bangalore"
            budget = l.get("budget") or "specified"

            msg = (
                stage_def["template"]
                .replace("{{name}}", name)
                .replace("{{interest}}", interest)
                .replace("{{location}}", location)
                .replace("{{budget}}", budget)
                .replace("{{business}}", config.BUSINESS_NAME)
            )

            success = whatsapp.send_message(wa_id, msg)
            if success:
                db.add_message(wa_id, "out", msg, sender="drip", customer_id=l.get("customer_id", 0))
                conv_state["drip_stage"] = next_stage_num
                conv_state["last_drip_at"] = datetime.now(timezone.utc).isoformat()
                db.update_conversation(wa_id, json.dumps(conv_state), customer_id=l.get("customer_id", 0))

                dispatched += 1
                logs.append({
                    "lead_id": lead_id,
                    "wa_id": wa_id,
                    "name": name,
                    "stage": next_stage_num,
                    "stage_name": stage_def["name"],
                })

        logger.info("Drip engine triggered: %d messages dispatched", dispatched)
        return {
            "ok": True,
            "total_dispatched": dispatched,
            "logs": logs,
        }
    except Exception as e:
        logger.error("Drip campaign failed: %s", e)
        return {"error": str(e)}
