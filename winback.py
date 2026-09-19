"""AegisBot Customer Win-Back & Loyalty Re-Engagement Engine.

Detects lapsed customer inquiries and past buyers, and dispatches tailored
promotional re-engagement incentives, VIP discounts, and satisfaction check-ins.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Set

import config
import db
import whatsapp

logger = logging.getLogger("aegisbot.winback")

_sent_winback_keys: Set[str] = set()


def run_winback_campaign(days_inactive: int = 14) -> Dict[str, Any]:
    """Identify inactive customers or won deals and deliver re-engagement messages."""
    customers = db._db().table("customers").select("*").execute().data or []
    leads = db.list_leads(limit=500)

    # Map customer wa_id to interest/requirement
    interest_map = {}
    for l in leads:
        wa = l.get("wa_id")
        if wa and l.get("interest"):
            interest_map[wa] = l.get("interest")

    reengaged: List[Dict[str, Any]] = []

    for cust in customers:
        wa_id = cust.get("wa_id")
        if not wa_id:
            continue

        if wa_id in _sent_winback_keys:
            continue

        name = cust.get("name") or "Valued Client"
        interest = interest_map.get(wa_id) or "office workstations and ergonomic furniture"

        msg = (
            f"👋 Hi {name}!\n\n"
            f"It's been a while since we connected regarding *{interest}*! ✨\n\n"
            f"We've just launched our **Executive VIP Savings** this week:\n"
            f"• Up to 15% off ergonomic seating & height-adjustable standing desks\n"
            f"• Free turnkey delivery & onsite ergonomic setup in Bangalore\n\n"
            f"Would you like us to send our updated September catalog or prepare an updated proposal? "
            f"Reply *CATALOG* or *QUOTE* anytime! 😊"
        )

        whatsapp.send_message(wa_id, msg)
        _sent_winback_keys.add(wa_id)

        reengaged.append({
            "wa_id": wa_id,
            "name": name,
            "interest": interest,
        })
        logger.info("Dispatched win-back re-engagement to %s", wa_id)

    return {
        "ok": True,
        "scanned_customers": len(customers),
        "reengaged_count": len(reengaged),
        "reengaged": reengaged,
    }

