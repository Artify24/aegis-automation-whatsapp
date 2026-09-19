"""AegisBot Enterprise Custom Business Policies Engine.

Provides:
  1. Structured custom policy definitions (Returns, Cancellations, Refunds, Custom Fabrication,
     Shipping & Installation, Data Privacy, Corporate Credit & Discounts).
  2. Dynamic runtime policy customization and persistence.
  3. Programmatic policy compliance evaluation (order cancellations, shipping waivers, bulk discounts).
  4. WhatsApp-ready policy summaries for instant customer inquiries.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aegisbot.policies")

POLICIES_JSON_FILE = Path(__file__).parent / "custom_policies.json"

DEFAULT_POLICIES: Dict[str, Dict[str, Any]] = {
    "returns": {
        "id": "returns",
        "title": "Return & Replacement Policy",
        "category": "logistics",
        "summary": "7-day replacement guarantee for manufacturing defects or transit damage in original packaging.",
        "return_window_days": 7,
        "requires_original_packaging": True,
        "exclusions": ["misuse", "normal wear", "unauthorized modification"],
        "active": True,
    },
    "cancellations": {
        "id": "cancellations",
        "title": "Order Cancellation & 100% Refund Policy",
        "category": "orders",
        "summary": "100% full refund if cancelled within 24 hours of placement. 8% restocking fee thereafter prior to dispatch.",
        "full_refund_window_hours": 24,
        "late_cancellation_fee_pct": 8,
        "refund_reversal_days": "3-5 business days",
        "active": True,
    },
    "bespoke": {
        "id": "bespoke",
        "title": "Bespoke & Custom Workstation Fabrication",
        "category": "manufacturing",
        "summary": "Custom orders require 50% advance deposit. Cancellable within 24 hours only; non-refundable once cutting begins.",
        "advance_deposit_pct": 50,
        "cancellation_window_hours": 24,
        "active": True,
    },
    "shipping": {
        "id": "shipping",
        "title": "Delivery & Free Onsite Installation Policy",
        "category": "logistics",
        "summary": "Free delivery in Bangalore on orders > ₹10,000. Flat ₹999 for orders < ₹10,000. Free onsite ergonomic assembly.",
        "free_shipping_threshold": 10000.0,
        "standard_shipping_fee": 999.0,
        "lead_time_catalog_days": "3-5 days",
        "free_assembly": True,
        "active": True,
    },
    "privacy": {
        "id": "privacy",
        "title": "Privacy, Data Retention & DPDP / GDPR Policy",
        "category": "compliance",
        "summary": "Zero 3rd-party data selling, PII phone masking in operational logs, and customer right-to-erasure supported.",
        "dpdp_compliant": True,
        "gdpr_compliant": True,
        "mask_pii_in_logs": True,
        "allow_data_erasure": True,
        "active": True,
    },
    "bulk_discount": {
        "id": "bulk_discount",
        "title": "Corporate Bulk Discount & Credit Terms",
        "category": "commercial",
        "summary": "5% discount for 5-15 units, 10% discount for 16-50 units. Net-30 credit terms for GSTIN-verified corporate accounts.",
        "tiers": [
            {"min_units": 5, "max_units": 15, "discount_pct": 5},
            {"min_units": 16, "max_units": 50, "discount_pct": 10},
            {"min_units": 51, "max_units": 999999, "discount_pct": 15},
        ],
        "credit_terms_available": "Net-30 with GSTIN verification",
        "active": True,
    },
}


def load_policies() -> Dict[str, Dict[str, Any]]:
    """Load policy definitions from disk or return default policies."""
    if not POLICIES_JSON_FILE.exists():
        save_policies(DEFAULT_POLICIES)
        return DEFAULT_POLICIES
    try:
        with open(POLICIES_JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to read %s: %s", POLICIES_JSON_FILE, e)
        return DEFAULT_POLICIES


def save_policies(policies: Dict[str, Dict[str, Any]]) -> None:
    """Save custom policies dictionary to disk."""
    try:
        with open(POLICIES_JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(policies, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("Failed to write %s: %s", POLICIES_JSON_FILE, e)


def get_all_policies() -> List[Dict[str, Any]]:
    """Return all configured business policies as a list."""
    policies = load_policies()
    return list(policies.values())


def get_policy(policy_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a specific policy by key identifier."""
    policies = load_policies()
    return policies.get(policy_id)


def update_policy(policy_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a policy rule dynamically."""
    policies = load_policies()
    if policy_id in policies:
        policies[policy_id].update(updates)
    else:
        updates["id"] = policy_id
        if "active" not in updates:
            updates["active"] = True
        policies[policy_id] = updates
    save_policies(policies)
    logger.info("Updated custom policy: %s", policy_id)
    return policies[policy_id]


def evaluate_policy(action: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Evaluate business policy compliance deterministically.
    
    Supported actions:
      - cancel_order: context={"elapsed_hours": float, "is_bespoke": bool}
      - return_item: context={"elapsed_days": int, "has_packaging": bool}
      - shipping_fee: context={"order_subtotal": float, "city": str}
      - bulk_discount: context={"total_units": int}
    """
    context = context or {}
    policies = load_policies()

    if action == "cancel_order":
        elapsed_hours = float(context.get("elapsed_hours", 0))
        is_bespoke = bool(context.get("is_bespoke", False))
        c_pol = policies.get("cancellations", DEFAULT_POLICIES["cancellations"])
        b_pol = policies.get("bespoke", DEFAULT_POLICIES["bespoke"])

        if is_bespoke and elapsed_hours > b_pol.get("cancellation_window_hours", 24):
            return {
                "action": action,
                "allowed": False,
                "reason": "Bespoke custom orders cannot be cancelled after 24 hours once fabrication commences.",
                "refund_percentage": 0,
                "cancellation_fee": 0,
            }

        max_window = c_pol.get("full_refund_window_hours", 24)
        if elapsed_hours <= max_window:
            return {
                "action": action,
                "allowed": True,
                "reason": f"Eligible for 100% full refund within {max_window} hours of order placement.",
                "refund_percentage": 100,
                "cancellation_fee_pct": 0,
                "reversal_timeline": c_pol.get("refund_reversal_days", "3-5 business days"),
            }
        else:
            fee_pct = c_pol.get("late_cancellation_fee_pct", 8)
            return {
                "action": action,
                "allowed": True,
                "reason": f"Cancellation permitted prior to dispatch subject to {fee_pct}% administrative restocking fee.",
                "refund_percentage": 100 - fee_pct,
                "cancellation_fee_pct": fee_pct,
                "reversal_timeline": c_pol.get("refund_reversal_days", "3-5 business days"),
            }

    elif action == "return_item":
        elapsed_days = int(context.get("elapsed_days", 0))
        has_packaging = bool(context.get("has_packaging", True))
        r_pol = policies.get("returns", DEFAULT_POLICIES["returns"])
        window = r_pol.get("return_window_days", 7)

        if elapsed_days > window:
            return {
                "action": action,
                "allowed": False,
                "reason": f"Exceeded allowable return replacement window of {window} days.",
            }
        if not has_packaging and r_pol.get("requires_original_packaging", True):
            return {
                "action": action,
                "allowed": False,
                "reason": "Return replacement requires original packaging and tags.",
            }
        return {
            "action": action,
            "allowed": True,
            "reason": f"Eligible for free replacement within {window}-day window.",
        }

    elif action == "shipping_fee":
        subtotal = float(context.get("order_subtotal", 0.0))
        city = str(context.get("city", "")).lower()
        s_pol = policies.get("shipping", DEFAULT_POLICIES["shipping"])
        threshold = float(s_pol.get("free_shipping_threshold", 10000.0))
        standard_fee = float(s_pol.get("standard_shipping_fee", 999.0))

        if subtotal >= threshold:
            return {
                "action": action,
                "free_shipping": True,
                "shipping_fee": 0.0,
                "reason": f"Order exceeds ₹{int(threshold):,} threshold. Free delivery applied.",
                "free_assembly": s_pol.get("free_assembly", True),
            }
        else:
            return {
                "action": action,
                "free_shipping": False,
                "shipping_fee": standard_fee,
                "reason": f"Order below ₹{int(threshold):,} threshold. Standard delivery fee applies.",
                "free_assembly": s_pol.get("free_assembly", True),
            }

    elif action == "bulk_discount":
        units = int(context.get("total_units", 0))
        b_pol = policies.get("bulk_discount", DEFAULT_POLICIES["bulk_discount"])
        tiers = b_pol.get("tiers", [])
        matched_pct = 0
        for tier in tiers:
            if tier["min_units"] <= units <= tier["max_units"]:
                matched_pct = tier["discount_pct"]
                break
        return {
            "action": action,
            "total_units": units,
            "discount_pct": matched_pct,
            "reason": f"{matched_pct}% volume discount applied for {units} units." if matched_pct > 0 else "No bulk discount tier met.",
            "credit_terms": b_pol.get("credit_terms_available", "Available on request"),
        }

    return {
        "action": action,
        "allowed": True,
        "message": f"Action '{action}' evaluated successfully against general operating rules.",
    }


def format_whatsapp_policy_summary(policy_id: Optional[str] = None) -> str:
    """Format a clean, readable WhatsApp message summarizing policies."""
    policies = load_policies()
    if policy_id and policy_id in policies:
        p = policies[policy_id]
        return f"📋 *{p['title']}*\n{p['summary']}"

    lines = ["📋 *Aegis Workspace Solutions — Official Policies Summary*\n"]
    for p in policies.values():
        if p.get("active"):
            lines.append(f"• *{p['title']}*: {p['summary']}")
    lines.append("\nNeed more details or custom terms? Reply anytime! 😊")
    return "\n".join(lines)

