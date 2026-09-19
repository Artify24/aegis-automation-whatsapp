"""AegisBot Autonomous Commerce & Order Management Engine.

Handles product catalog lookup, cart item matching, 18% GST tax calculation,
order creation, status updates, and WhatsApp confirmation messaging.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import config
import db
import whatsapp

logger = logging.getLogger("aegisbot.orders")

# Official catalog products & standard pricing
CATALOG: List[Dict[str, Any]] = [
    {
        "id": "ergo_pro_3d",
        "name": "Aegis Ergo Pro 3D Ergonomic Chair",
        "price": 14999.00,
        "keywords": ["ergo pro", "ergo 3d", "pro 3d", "ergonomic chair"],
    },
    {
        "id": "executive_boss",
        "name": "Aegis Executive Boss High-Back Chair",
        "price": 28500.00,
        "keywords": ["boss chair", "executive chair", "nappa leather", "high back"],
    },
    {
        "id": "smart_desk",
        "name": "Aegis SmartDesk Motorized Standing Desk",
        "price": 24999.00,
        "keywords": ["smartdesk", "standing desk", "height adjustable", "motorized desk"],
    },
    {
        "id": "modular_workstation_4",
        "name": "Aegis 4-Cluster Modular Workstation",
        "price": 48000.00,
        "keywords": ["modular workstation", "4-cluster", "cluster desk", "4 workstation"],
    },
    {
        "id": "turnkey_startup_hub",
        "name": "Aegis Turnkey Startup Hub (10 Desks + 10 Chairs)",
        "price": 185000.00,
        "keywords": ["startup hub", "turnkey package", "office package", "10 desks"],
    },
]

GST_RATE = 0.18  # 18% commercial furniture GST in India


def match_catalog_items(text: str) -> List[Dict[str, Any]]:
    """Deterministically match catalog products and quantities from customer text."""
    lower = text.lower()
    matched: List[Dict[str, Any]] = []

    for product in CATALOG:
        for kw in product["keywords"]:
            if kw in lower:
                # Look for quantity pattern (e.g. "2 x ergo" or "5 ergo" or "ergo x 3")
                qty = 1
                qty_match = re.search(rf"(\d+)\s*(?:x\s*)?{re.escape(kw)}", lower)
                if not qty_match:
                    qty_match = re.search(rf"{re.escape(kw)}\s*(?:x\s*)?(\d+)", lower)
                if qty_match:
                    try:
                        qty = max(1, int(qty_match.group(1)))
                    except ValueError:
                        qty = 1

                matched.append({
                    "product_id": product["id"],
                    "name": product["name"],
                    "unit_price": product["price"],
                    "qty": qty,
                    "total": round(qty * product["price"], 2),
                })
                break  # Don't match multiple keywords for the same product

    return matched


def calculate_order_totals(items: List[Dict[str, Any]]) -> Tuple[float, float, float]:
    """Calculate subtotal, 18% GST tax, and grand total."""
    subtotal = round(sum(i["total"] for i in items), 2)
    tax = round(subtotal * GST_RATE, 2)
    total = round(subtotal + tax, 2)
    return subtotal, tax, total


def create_customer_order(
    wa_id: str,
    customer_name: str,
    items: List[Dict[str, Any]],
    notes: str = "",
) -> Dict[str, Any]:
    """Create order in system and format confirmation details."""
    subtotal, tax, total = calculate_order_totals(items)
    order = db.create_order(
        wa_id=wa_id,
        customer_name=customer_name or "Valued Client",
        items=items,
        subtotal=subtotal,
        tax=tax,
        total=total,
        status="confirmed",
        notes=notes,
    )
    logger.info("Order created #%s for %s (%s items, Rs %s)", order.get("id"), wa_id, len(items), total)
    return order


def format_order_receipt(order: Dict[str, Any]) -> str:
    """Format WhatsApp-friendly order invoice receipt."""
    order_id = order.get("id", "ORD")
    items = order.get("items", [])
    subtotal = order.get("subtotal", 0.0)
    tax = order.get("tax", 0.0)
    total = order.get("total", 0.0)

    lines = [
        f"🧾 *Order Confirmed!* #ORD-2026-{order_id}",
        "Thank you for choosing Aegis Workspace Solutions!",
        "",
        "*Itemized Details:*",
    ]
    for it in items:
        lines.append(f"• {it.get('qty')}x {it.get('name')} — Rs {it.get('total', 0):,.2f}")

    lines.extend([
        "",
        f"Subtotal: Rs {subtotal:,.2f}",
        f"GST (18%): Rs {tax:,.2f}",
        f"*Grand Total: Rs {total:,.2f}*",
        "",
        "🚚 *Delivery Timeline:* 2–3 business days with free onsite assembly.",
        "A dispatch coordinator will contact you shortly.",
    ])
    return "\n".join(lines)

