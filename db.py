"""Supabase database layer — all persistence goes through here.

Uses supabase-py v2 which supports the new sb_publishable_ key format.
Run supabase/schema.sql once in the Supabase SQL editor before first use.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from supabase import create_client, Client
import config

logger = logging.getLogger("aegisbot.db")

_client: Optional[Client] = None


def _db() -> Client:
    global _client
    if _client is None:
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env"
            )
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        logger.info("Supabase client initialised → %s", config.SUPABASE_URL)
    return _client


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ────────────────────────────────────────────────────────── customers ──────────

def upsert_customer(wa_id: str, name: str = "", phone: str = "") -> Dict[str, Any]:
    """Get-or-create a customer row. Returns the row dict."""
    db = _db()
    res = db.table("customers").select("*").eq("wa_id", wa_id).limit(1).execute()
    if res.data:
        return res.data[0]
    now = _now()
    row = {
        "wa_id": wa_id,
        "name": name,
        "phone": phone or wa_id,
        "source": "whatsapp",
        "status": "lead",
        "lead_score": 0,
        "qualified": 0,
        "created_at": now,
        "last_active_at": now,
    }
    ins = db.table("customers").insert(row).execute()
    return ins.data[0] if ins.data else row


def update_customer(wa_id: str, **fields: Any) -> None:
    if not fields:
        return
    fields["last_active_at"] = _now()
    _db().table("customers").update(fields).eq("wa_id", wa_id).execute()


def get_customer(wa_id: str) -> Optional[Dict[str, Any]]:
    res = _db().table("customers").select("*").eq("wa_id", wa_id).limit(1).execute()
    return res.data[0] if res.data else None


def list_customers(limit: int = 500) -> List[Dict[str, Any]]:
    res = _db().table("customers").select("*").order("id", desc=True).limit(limit).execute()
    return res.data or []


# ────────────────────────────────────────────────────────── conversations ──────

def get_or_create_conversation(wa_id: str, customer_id: int) -> Dict[str, Any]:
    db = _db()
    res = db.table("conversations").select("*").eq("wa_id", wa_id).limit(1).execute()
    if res.data:
        return res.data[0]
    now = _now()
    row = {
        "customer_id": customer_id,
        "wa_id": wa_id,
        "state": "{}",
        "mode": "bot",
        "created_at": now,
        "updated_at": now,
    }
    ins = db.table("conversations").insert(row).execute()
    return ins.data[0] if ins.data else row


def update_conversation(wa_id: str, state_json: str, customer_id: int = 0) -> None:
    db = _db()
    res = db.table("conversations").select("id").eq("wa_id", wa_id).limit(1).execute()
    now = _now()
    if res.data:
        db.table("conversations").update({
            "state": state_json,
            "updated_at": now,
        }).eq("wa_id", wa_id).execute()
    else:
        db.table("conversations").insert({
            "wa_id": wa_id,
            "customer_id": customer_id,
            "state": state_json,
            "mode": "bot",
            "created_at": now,
            "updated_at": now,
        }).execute()


def get_conversation_state(wa_id: str) -> Dict[str, Any]:
    """Returns parsed state dict, never raises."""
    import json
    res = _db().table("conversations").select("state").eq("wa_id", wa_id).limit(1).execute()
    if not res.data:
        return {}
    try:
        return json.loads(res.data[0].get("state") or "{}")
    except Exception:
        return {}


def get_conversation(wa_id: str) -> Optional[Dict[str, Any]]:
    """Fetch conversation row for a wa_id."""
    res = _db().table("conversations").select("*").eq("wa_id", wa_id).limit(1).execute()
    return res.data[0] if res.data else None


def set_conversation_mode(wa_id: str, mode: str) -> None:
    """Toggle between 'bot' and 'human' takeover mode."""
    _db().table("conversations").update({
        "mode": mode,
        "updated_at": _now(),
    }).eq("wa_id", wa_id).execute()


def list_conversations_with_customers() -> List[Dict[str, Any]]:
    """List recent conversations merged with customer profile and last message."""
    try:
        convs = _db().table("conversations").select("*").order("updated_at", desc=True).limit(50).execute().data or []
        custs = {c["wa_id"]: c for c in _db().table("customers").select("*").execute().data or []}
        out = []
        for cv in convs:
            wid = cv.get("wa_id")
            c = custs.get(wid, {})
            last_msg = _db().table("messages").select("text,direction,timestamp").eq("wa_id", wid).order("id", desc=True).limit(1).execute().data
            cv_item = {
                "wa_id": wid,
                "mode": cv.get("mode", "bot"),
                "updated_at": cv.get("updated_at"),
                "customer_name": c.get("name") or wid,
                "customer_status": c.get("status") or "lead",
                "lead_score": c.get("lead_score", 0),
                "last_message": last_msg[0].get("text", "") if last_msg else "",
                "last_direction": last_msg[0].get("direction", "") if last_msg else "",
                "last_timestamp": last_msg[0].get("timestamp", "") if last_msg else cv.get("updated_at"),
            }
            out.append(cv_item)
        return out
    except Exception as e:
        logger.error("Failed to list conversations: %s", e)
        return []


def get_conversation_messages(wa_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch message history in chronological order."""
    try:
        res = _db().table("messages").select("*").eq("wa_id", wa_id).order("id", desc=False).limit(limit).execute()
        return res.data or []
    except Exception as e:
        logger.error("Failed to fetch messages for %s: %s", wa_id, e)
        return []


# ────────────────────────────────────────────────────────── messages ──────────

def add_message(wa_id: str, direction: str, text: str,
                sender: str = "bot", customer_id: int = 0) -> None:
    _db().table("messages").insert({
        "customer_id": customer_id,
        "wa_id": wa_id,
        "direction": direction,
        "sender": sender,
        "text": text,
        "timestamp": _now(),
    }).execute()


def recent_messages(wa_id: str, limit: int = 8) -> List[Dict[str, Any]]:
    res = (_db().table("messages")
           .select("direction,sender,text,timestamp")
           .eq("wa_id", wa_id)
           .order("id", desc=True)
           .limit(limit)
           .execute())
    return list(reversed(res.data or []))


# ────────────────────────────────────────────────────────── leads ─────────────

def create_lead(
    customer_id: int,
    wa_id: str,
    name: str = "",
    phone: str = "",
    interest: str = "",
    budget: str = "",
    timeline: str = "",
    location: str = "",
    score: int = 0,
    qualified: int = 0,
    status: str = "new",
    notes: str = "",
) -> Dict[str, Any]:
    """Insert a lead row and return it."""
    row = {
        "customer_id": customer_id,
        "wa_id": wa_id,
        "name": name,
        "phone": phone or wa_id,
        "interest": interest,
        "budget": budget,
        "timeline": timeline,
        "location": location,
        "source": "whatsapp",
        "score": score,
        "qualified": qualified,
        "status": status,
        "notes": notes,
        "created_at": _now(),
    }
    res = _db().table("leads").insert(row).execute()
    saved = res.data[0] if res.data else row
    logger.info("✅ Lead saved to Supabase: id=%s name=%s score=%s",
                saved.get("id", "?"), name, score)
    return saved


def list_leads(limit: int = 500) -> List[Dict[str, Any]]:
    res = _db().table("leads").select("*").order("id", desc=True).limit(limit).execute()
    return res.data or []


def get_lead_by_customer(customer_id: int) -> Optional[Dict[str, Any]]:
    res = (_db().table("leads")
           .select("*")
           .eq("customer_id", customer_id)
           .order("id", desc=True)
           .limit(1)
           .execute())
    return res.data[0] if res.data else None


def update_lead(lead_id: int, **fields: Any) -> None:
    if fields:
        _db().table("leads").update(fields).eq("id", lead_id).execute()


def get_stats() -> Dict[str, Any]:
    """Calculate aggregate CRM and conversation statistics."""
    try:
        db = _db()
        leads = db.table("leads").select("id,qualified,status").execute().data or []
        customers = db.table("customers").select("id,status").execute().data or []
        messages = db.table("messages").select("id,direction").execute().data or []
        total_leads = len(leads)
        qualified = sum(1 for l in leads if l.get("qualified"))
        status_counts: Dict[str, int] = {}
        for l in leads:
            st = l.get("status") or "new"
            status_counts[st] = status_counts.get(st, 0) + 1
        return {
            "total_customers": len(customers),
            "total_messages": len(messages),
            "total_leads": total_leads,
            "qualified_leads": qualified,
            "qualification_rate": f"{(qualified / max(1, total_leads)) * 100:.1f}%",
            "status_breakdown": status_counts,
        }
    except Exception as e:
        logger.error("Failed to compute stats: %s", e)
        return {
            "total_customers": 0,
            "total_messages": 0,
            "total_leads": 0,
            "qualified_leads": 0,
            "qualification_rate": "0%",
            "status_breakdown": {},
        }


# ────────────────────────────────────────────────────────── health check ──────

def ping() -> bool:
    """Returns True if Supabase is reachable."""
    try:
        _db().table("customers").select("id").limit(1).execute()
        return True
    except Exception as e:
        logger.error("Supabase ping failed: %s", e)
        return False


# ────────────────────────────────────────────────────────── orders ─────────────

_local_orders: List[Dict[str, Any]] = []
_remote_orders_exist: Optional[bool] = None

def create_order(
    wa_id: str,
    customer_name: str,
    items: List[Dict[str, Any]],
    subtotal: float,
    tax: float,
    total: float,
    status: str = "pending",
    notes: str = "",
) -> Dict[str, Any]:
    """Insert an order record with resilient fallback."""
    global _remote_orders_exist
    row = {
        "id": len(_local_orders) + 1001,
        "wa_id": wa_id,
        "customer_name": customer_name,
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "status": status,
        "notes": notes,
        "created_at": _now(),
    }
    if _remote_orders_exist is not False:
        try:
            res = _db().table("orders").insert({
                "wa_id": wa_id,
                "customer_name": customer_name,
                "items": json.dumps(items),
                "subtotal": subtotal,
                "tax": tax,
                "total": total,
                "status": status,
                "notes": notes,
                "created_at": _now(),
            }).execute()
            if res.data:
                _remote_orders_exist = True
                saved = res.data[0]
                if isinstance(saved.get("items"), str):
                    saved["items"] = json.loads(saved["items"])
                row = saved
        except Exception as e:
            _remote_orders_exist = False
            logger.debug("Supabase orders table unavailable, using resilient memory store: %s", e)
    _local_orders.append(row)
    return row


def list_orders(limit: int = 100) -> List[Dict[str, Any]]:
    """List orders, falling back to resilient store if remote table is unavailable."""
    global _remote_orders_exist
    if _remote_orders_exist is not False:
        try:
            res = _db().table("orders").select("*").order("id", desc=True).limit(limit).execute()
            if res.data:
                _remote_orders_exist = True
                out = []
                for r in res.data:
                    if isinstance(r.get("items"), str):
                        try:
                            r["items"] = json.loads(r["items"])
                        except Exception:
                            pass
                    out.append(r)
                return out
        except Exception:
            _remote_orders_exist = False
    return list(reversed(_local_orders))[:limit]


def update_order_status(order_id: int, status: str) -> Optional[Dict[str, Any]]:
    """Update order status (e.g. pending, confirmed, cancelled)."""
    global _remote_orders_exist
    if _remote_orders_exist is not False:
        try:
            _db().table("orders").update({"status": status}).eq("id", order_id).execute()
            _remote_orders_exist = True
        except Exception:
            _remote_orders_exist = False
    for o in _local_orders:
        if o.get("id") == order_id:
            o["status"] = status
            return o
    return {"id": order_id, "status": status}


# ────────────────────────────────────────────────────────── appointments ───────

_local_appointments: List[Dict[str, Any]] = []
_remote_appointments_exist: Optional[bool] = None

def create_appointment(
    wa_id: str,
    customer_name: str,
    service: str,
    slot_start: str,
    slot_end: str,
    location: str = "",
    status: str = "confirmed",
) -> Dict[str, Any]:
    """Create an appointment booking record."""
    global _remote_appointments_exist
    row = {
        "id": len(_local_appointments) + 501,
        "wa_id": wa_id,
        "customer_name": customer_name,
        "service": service,
        "slot_start": slot_start,
        "slot_end": slot_end,
        "location": location,
        "status": status,
        "created_at": _now(),
    }
    if _remote_appointments_exist is not False:
        try:
            res = _db().table("appointments").insert(row).execute()
            if res.data:
                _remote_appointments_exist = True
                row = res.data[0]
        except Exception as e:
            _remote_appointments_exist = False
            logger.debug("Supabase appointments table unavailable, using resilient memory store: %s", e)
    _local_appointments.append(row)
    return row


def list_appointments(limit: int = 100) -> List[Dict[str, Any]]:
    """List appointment bookings."""
    global _remote_appointments_exist
    if _remote_appointments_exist is not False:
        try:
            res = _db().table("appointments").select("*").order("id", desc=True).limit(limit).execute()
            if res.data:
                _remote_appointments_exist = True
                return res.data
        except Exception:
            _remote_appointments_exist = False
    return list(reversed(_local_appointments))[:limit]


def is_slot_available(slot_start: str) -> bool:
    """Check if a time slot is already booked."""
    global _remote_appointments_exist
    if _remote_appointments_exist is not False:
        try:
            res = _db().table("appointments").select("id").eq("slot_start", slot_start).eq("status", "confirmed").execute()
            _remote_appointments_exist = True
            if res.data and len(res.data) > 0:
                return False
        except Exception:
            _remote_appointments_exist = False
    for a in _local_appointments:
        if a.get("slot_start") == slot_start and a.get("status") == "confirmed":
            return False
    return True
