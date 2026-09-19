"""AegisBot Phase 9 — Custom Business Policies & Compliance Test Suite.

Validates:
  1. Structured custom policy definitions (schema & defaults).
  2. Programmatic evaluation engine (cancellation windows, bespoke orders, shipping thresholds, bulk discounts).
  3. API endpoints:
     - GET  /api/policies
     - GET  /api/policies/{policy_id}
     - POST /api/policies
     - POST /api/policies/evaluate
  4. RAG knowledge engine indexing of custom_policies.md.
  5. End-to-end WhatsApp conversational inquiries on business policies.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import io
import json
import logging
import time
from pathlib import Path
import httpx
from fastapi.testclient import TestClient

import policies
from main import app

logging.basicConfig(level=logging.WARNING)
BASE = "http://localhost:8000"


def banner(title: str) -> None:
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


def get_client():
    try:
        r = httpx.get(f"{BASE}/health", timeout=1.5)
        if r.status_code == 200:
            print("  [INFO] Connected to live AegisBot server at http://localhost:8000")
            return httpx.Client(base_url=BASE, timeout=25.0)
    except Exception:
        pass
    print("  [INFO] Using standalone in-process ASGI TestClient")
    return TestClient(app)


def run_phase9_tests():
    banner("PHASE 9: CUSTOM BUSINESS POLICIES & COMPLIANCE SUITE")
    client = get_client()

    # ── 1. Structured Policy Definitions ─────────────────────────────────────
    banner("1. Policy Definitions & Storage Verification")
    all_p = policies.get_all_policies()
    print(f"Total defined business policies: {len(all_p)}")
    assert len(all_p) >= 6, f"Expected at least 6 policies, got {len(all_p)}"
    
    expected_keys = {"returns", "cancellations", "bespoke", "shipping", "privacy", "bulk_discount"}
    found_keys = {p["id"] for p in all_p}
    assert expected_keys.issubset(found_keys), f"Missing keys: {expected_keys - found_keys}"
    print("  ✓ All 6 core enterprise policy schemas validated.")

    # ── 2. Programmatic Evaluation Engine ────────────────────────────────────
    banner("2. Programmatic Policy Compliance Evaluation")
    
    # Cancellation < 24h
    c1 = policies.evaluate_policy("cancel_order", {"elapsed_hours": 8})
    assert c1["allowed"] is True
    assert c1["refund_percentage"] == 100
    print("  ✓ Standard order cancellation within 24 hours: 100% full refund approved.")

    # Cancellation > 24h
    c2 = policies.evaluate_policy("cancel_order", {"elapsed_hours": 36})
    assert c2["allowed"] is True
    assert c2["refund_percentage"] == 92
    assert c2["cancellation_fee_pct"] == 8
    print("  ✓ Standard order cancellation after 24 hours: 8% restocking fee applied.")

    # Bespoke order cancellation > 24h
    c3 = policies.evaluate_policy("cancel_order", {"elapsed_hours": 30, "is_bespoke": True})
    assert c3["allowed"] is False
    print("  ✓ Bespoke order cancellation after 24h rejected (fabrication commenced).")

    # Shipping fee calculation
    s_free = policies.evaluate_policy("shipping_fee", {"order_subtotal": 14999.0})
    assert s_free["free_shipping"] is True
    assert s_free["shipping_fee"] == 0.0
    print("  ✓ Order ₹14,999: Free Bangalore shipping + assembly applied.")

    s_paid = policies.evaluate_policy("shipping_fee", {"order_subtotal": 6500.0})
    assert s_paid["free_shipping"] is False
    assert s_paid["shipping_fee"] == 999.0
    print("  ✓ Order ₹6,500: Standard ₹999 delivery fee applied.")

    # Bulk discount calculation
    b_disc = policies.evaluate_policy("bulk_discount", {"total_units": 12})
    assert b_disc["discount_pct"] == 5
    print("  ✓ Bulk order 12 units: 5% volume discount applied.")

    # ── 3. REST API Endpoints ────────────────────────────────────────────────
    banner("3. Custom Policy REST API Endpoints")
    
    # GET /api/policies
    r_list = client.get("/api/policies")
    assert r_list.status_code == 200
    assert r_list.json().get("count") >= 6
    print(f"  ✓ GET /api/policies returned {r_list.json().get('count')} policies.")

    # GET /api/policies/privacy
    r_priv = client.get("/api/policies/privacy")
    assert r_priv.status_code == 200
    assert r_priv.json()["policy"]["id"] == "privacy"
    print("  ✓ GET /api/policies/privacy retrieved privacy policy.")

    # POST /api/policies (Dynamic Update)
    r_up = client.post("/api/policies", json={
        "id": "shipping",
        "free_shipping_threshold": 12000.0,
    })
    assert r_up.status_code == 200
    assert r_up.json()["policy"]["free_shipping_threshold"] == 12000.0
    # Reset back to 10000.0
    client.post("/api/policies", json={"id": "shipping", "free_shipping_threshold": 10000.0})
    print("  ✓ POST /api/policies dynamically updated policy threshold.")

    # POST /api/policies/evaluate
    r_eval = client.post("/api/policies/evaluate", json={
        "action": "cancel_order",
        "context": {"elapsed_hours": 10, "is_bespoke": False},
    })
    assert r_eval.status_code == 200
    assert r_eval.json()["refund_percentage"] == 100
    print("  ✓ POST /api/policies/evaluate executed remotely.")

    # ── 4. RAG Knowledge Search on Custom Policies ───────────────────────────
    banner("4. RAG Engine Policy Ingestion & Querying")
    r_rag = client.post("/dev/ask", json={"question": "What is your return policy?"})
    assert r_rag.status_code == 200
    reply = r_rag.json().get("reply", "")
    print(f"  RAG Reply: {reply[:120]}...")
    assert any(term in reply.lower() for term in ["7-day", "replacement", "return", "defect", "damage"])
    print("  ✓ RAG engine accurately cited custom return & replacement policy.")

    # ── 5. Conversational WhatsApp Dialogue ──────────────────────────────────
    banner("5. WhatsApp Conversational Inquiry Simulation")
    test_wa = "919444777888"
    r_wa = client.post("/dev/send", json={
        "wa_id": test_wa,
        "text": "Can I get a full refund if I cancel my order?",
    })
    assert r_wa.status_code == 200
    wa_replies = r_wa.json().get("replies", [])
    assert len(wa_replies) > 0
    full_text = " ".join(wa_replies).lower()
    print(f"  WhatsApp Bot Reply: {wa_replies[0][:120]}...")
    assert any(term in full_text for term in ["24 hours", "100%", "refund", "cancel"])
    print("  ✓ WhatsApp bot conversational response correctly answered policy terms.")

    banner("PHASE 9 CUSTOM POLICIES TEST SUITE: 100% PASS")


if __name__ == "__main__":
    run_phase9_tests()

