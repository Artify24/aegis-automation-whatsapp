"""AegisBot Smart Appointment & Showroom Visit Scheduling Engine.

Generates available consultation/visit slots based on business hours,
validates slot collisions, books appointments, and dispatches confirmations.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import config
import db

logger = logging.getLogger("aegisbot.bookings")

# Default operating window: 10:00 to 19:00 (10 AM - 7 PM)
DEFAULT_START_HOUR = 10
DEFAULT_END_HOUR = 19
SLOT_DURATION_HOURS = 1


def get_available_slots(days_ahead: int = 5) -> List[Dict[str, str]]:
    """Generate available 1-hour appointment slots for upcoming business days."""
    now = datetime.now()
    slots: List[Dict[str, str]] = []

    for d in range(1, days_ahead + 1):
        day_date = now.date() + timedelta(days=d)
        # Skip Sundays (or allow limited slots)
        if day_date.weekday() == 6:  # Sunday
            continue

        for hour in range(DEFAULT_START_HOUR, DEFAULT_END_HOUR):
            start_dt = datetime.combine(day_date, datetime.min.time()).replace(hour=hour, minute=0)
            end_dt = start_dt + timedelta(hours=SLOT_DURATION_HOURS)

            slot_start_str = start_dt.strftime("%Y-%m-%d %H:%M")
            slot_end_str = end_dt.strftime("%Y-%m-%d %H:%M")

            # Check if slot is available
            if db.is_slot_available(slot_start_str):
                label = start_dt.strftime("%A, %d %b at %I:%M %p")
                slots.append({
                    "slot_start": slot_start_str,
                    "slot_end": slot_end_str,
                    "label": label,
                    "date": day_date.isoformat(),
                })

    return slots


def book_appointment(
    wa_id: str,
    customer_name: str,
    service: str = "Showroom Visit & Ergonomic Consultation",
    slot_start: Optional[str] = None,
    slot_end: Optional[str] = None,
    location: str = "100 Feet Road, Indiranagar, Bangalore",
) -> Dict[str, Any]:
    """Book an appointment for a customer."""
    # If slot_start not specified, take next available slot
    if not slot_start:
        available = get_available_slots(days_ahead=3)
        if not available:
            raise ValueError("No available appointment slots found.")
        chosen = available[0]
        slot_start = chosen["slot_start"]
        slot_end = chosen["slot_end"]

    if not db.is_slot_available(slot_start):
        raise ValueError(f"Requested slot '{slot_start}' is already booked.")

    if not slot_end:
        start_dt = datetime.strptime(slot_start, "%Y-%m-%d %H:%M")
        slot_end = (start_dt + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")

    appointment = db.create_appointment(
        wa_id=wa_id,
        customer_name=customer_name or "Valued Client",
        service=service,
        slot_start=slot_start,
        slot_end=slot_end,
        location=location or config.BUSINESS_LOCATION or "Indiranagar Showroom",
        status="confirmed",
    )
    logger.info("Appointment booked #%s for %s at %s", appointment.get("id"), wa_id, slot_start)
    return appointment


def format_booking_confirmation(appointment: Dict[str, Any]) -> str:
    """Format WhatsApp-friendly appointment booking confirmation."""
    apt_id = appointment.get("id", "APT")
    service = appointment.get("service", "Showroom Visit")
    slot_start = appointment.get("slot_start", "")
    location = appointment.get("location", "Indiranagar Showroom")

    try:
        dt = datetime.strptime(slot_start, "%Y-%m-%d %H:%M")
        formatted_time = dt.strftime("%A, %d %B %Y at %I:%M %p")
    except Exception:
        formatted_time = slot_start

    return "\n".join([
        f"📅 *Appointment Confirmed!* #APT-2026-{apt_id}",
        f"We have scheduled your *{service}*.",
        "",
        f"🕒 *Time:* {formatted_time}",
        f"📍 *Location:* {location}",
        "",
        "✨ *What to expect:*",
        "• Dedicated ergonomic consultant.",
        "• Hands-on testing of all task chairs and motorized standing desks.",
        "• Instant 3D office layout proposal.",
        "",
        "Need to reschedule? Just reply to this chat anytime!",
    ])

