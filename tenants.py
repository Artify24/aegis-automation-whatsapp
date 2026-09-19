"""AegisBot Multi-Tenant White-Labeling & Business Profile Switcher.

Allows a single AegisBot server instance to support multiple business tenants or clients
(e.g., Office Furniture, Healthcare/Dental Clinic, Real Estate, Fine Dining/Catering),
each with their own brand persona, address, pricing, and operating rules.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import config

logger = logging.getLogger("aegisbot.tenants")

TENANTS_FILE = Path(__file__).parent / "tenants.json"

# Default turnkey client profiles
DEFAULT_PROFILES: Dict[str, Dict[str, Any]] = {
    "aegis_workspace": {
        "id": "aegis_workspace",
        "name": "Aegis Workspace Solutions",
        "industry": "Commercial Furniture & Ergonomics",
        "currency": "INR",
        "currency_symbol": "Rs",
        "phone": "+91 80 4123 9900",
        "address": "100 Feet Road, Indiranagar, Bangalore (Opp. Metro Pillar 84)",
        "hours": "Mon-Sat: 9:30 AM - 8:00 PM | Sun: 10:30 AM - 6:00 PM",
        "greeting": "Hi! 👋 Welcome to *Aegis Workspace Solutions*! I'm your 24/7 instant assistant. Ask me about products, pricing, store hours, or get a custom corporate quote! 😊",
        "catalog_doc": "catalog_pricing.md",
        "active": True,
    },
    "apex_realestate": {
        "id": "apex_realestate",
        "name": "Apex Prime Properties",
        "industry": "Real Estate & Commercial Leasing",
        "currency": "INR",
        "currency_symbol": "Rs",
        "phone": "+91 80 5566 7788",
        "address": "MG Road, Bangalore",
        "hours": "Daily: 9:00 AM - 7:00 PM",
        "greeting": "Welcome to *Apex Prime Properties*! 🏢 Explore luxury 2/3 BHK apartments, commercial tech parks, and prime plots in Bangalore. How can I help you find your dream space today?",
        "catalog_doc": "company_info.json",
        "active": False,
    },
    "dr_smile_dental": {
        "id": "dr_smile_dental",
        "name": "Dr. Smile Dental & Orthodontics",
        "industry": "Healthcare & Dental Care",
        "currency": "INR",
        "currency_symbol": "Rs",
        "phone": "+91 80 3344 1122",
        "address": "Koramangala 4th Block, Bangalore",
        "hours": "Mon-Sat: 10:00 AM - 8:30 PM | Sun: By appointment",
        "greeting": "Hello! 👋 Welcome to *Dr. Smile Dental Clinic*. How can we help you today? Inquire about dental implants, aligners, root canals, or book an instant consultation! 🦷",
        "catalog_doc": "faq.md",
        "active": False,
    },
}


def load_profiles() -> Dict[str, Dict[str, Any]]:
    """Load profiles from disk, or initialize with default profiles."""
    if not TENANTS_FILE.exists():
        save_profiles(DEFAULT_PROFILES)
        return DEFAULT_PROFILES
    try:
        with open(TENANTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to read tenants.json: %s", e)
        return DEFAULT_PROFILES


def save_profiles(profiles: Dict[str, Dict[str, Any]]) -> None:
    """Save tenant profiles to disk."""
    try:
        with open(TENANTS_FILE, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("Failed to write tenants.json: %s", e)


def get_active_tenant() -> Dict[str, Any]:
    """Get the currently active tenant profile."""
    profiles = load_profiles()
    for profile in profiles.values():
        if profile.get("active"):
            return profile
    # Default fallback
    return list(profiles.values())[0] if profiles else DEFAULT_PROFILES["aegis_workspace"]


def switch_tenant(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Switch the active tenant profile."""
    profiles = load_profiles()
    if tenant_id not in profiles:
        return None

    for tid, p in profiles.items():
        p["active"] = (tid == tenant_id)

    save_profiles(profiles)
    active = profiles[tenant_id]

    # Update runtime config
    config.BUSINESS_NAME = active.get("name", config.BUSINESS_NAME)
    logger.info("Switched active tenant to: %s (%s)", active.get("name"), tenant_id)
    return active
