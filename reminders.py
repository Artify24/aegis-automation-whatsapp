"""AegisBot Automated Appointment Reminder Engine.

Scans upcoming confirmed appointments, formats personalized WhatsApp reminders,
and dispatches notifications to clients ahead of their scheduled visits.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Set

import db
import whatsapp

logger = logging.getLogger("aegisbot.reminders")

# Track sent reminders to prevent duplicate notifications in the same cycle
_sent_reminder_keys: Set[str] = set()


def scan_and_dispatch_reminders(hours_ahead: int = 48) -> Dict[str, Any]:
    """Find upcoming confirmed appointments within hours_ahead and dispatch WhatsApp reminders."""
    now = datetime.now()
    horizon = now + timedelta(hours=hours_ahead)
    appointments = db.list_appointments(limit=200)

    reminded: List[Dict[str, Any]] = []

    for apt in appointments:
        if apt.get("status") != "confirmed":
            continue

        slot_start_str = apt.get("slot_start", "")
        if not slot_start_str:
            continue

        try:
            slot_dt = datetime.strptime(slot_start_str, "%Y-%m-%d %H:%M")
        except Exception:
            continue

        # Check if slot falls in the upcoming window
        if now <= slot_dt <= horizon:
            apt_id = str(apt.get("id"))
            wa_id = apt.get("wa_id", "")
            reminder_key = f"{apt_id}:{slot_start_str}"

            if reminder_key in _sent_reminder_keys:
                continue

            # Format reminder
            formatted_time = slot_dt.strftime("%A, %d %B at %I:%M %p")
            cust_name = apt.get("customer_name", "Valued Client")
            service = apt.get("service", "Showroom Visit")
            location = apt.get("location", "Indiranagar Showroom")

            msg = (
                f"🔔 *Upcoming Appointment Reminder*\n\n"
                f"Hi {cust_name}! This is a friendly reminder for your upcoming *{service}*.\n\n"
                f"🕒 *Scheduled Time:* {formatted_time}\n"
                f"📍 *Location:* {location}\n\n"
                f"Please reply *CONFIRM* to lock in your slot, or *RESCHEDULE* if you need to adjust your visit. See you soon! 😊"
            )

            # Send via WhatsApp
            whatsapp.send_message(wa_id, msg)
            _sent_reminder_keys.add(reminder_key)

            reminded.append({
                "appointment_id": apt.get("id"),
                "wa_id": wa_id,
                "customer_name": cust_name,
                "slot_start": slot_start_str,
            })
            logger.info("Dispatched appointment reminder #%s to %s", apt_id, wa_id)

    return {
        "ok": True,
        "scanned_total": len(appointments),
        "reminders_sent": len(reminded),
        "reminded_clients": reminded,
    }

