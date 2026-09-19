"""Phase 7 Enterprise Verification Suite:
1. Product Catalog Matching & 18% GST Tax Math (orders.py)
2. Order Creation & Itemized Receipt Formatting (/api/orders/create)
3. Order Management & Status Transition (/api/orders & PATCH)
4. Showroom Appointment Slot Generation (/api/bookings/slots)
5. Appointment Booking & WhatsApp Confirmation (/api/bookings/create)
6. Double-Booking Collision Prevention
7. Vercel Serverless Crons Manifest Validation (vercel.json)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import httpx

ROOT_DIR = Path(__file__).resolve().parent
BASE_URL = "http://localhost:8000"


def banner(title: str) -> None:
    print("\n" + "=" * 68)
    print(f"  {title}")
    print("=" * 68)


def get_client():
    """Return live HTTP client if server is up, else in-process ASGI TestClient."""
    try:
        resp = httpx.get(f"{BASE_URL}/health", timeout=1.0)
        if resp.status_code in (200, 500):
            print("  [INFO] Connected to LIVE server on http://localhost:8000")
            return httpx.Client(base_url=BASE_URL, timeout=15.0)
    except Exception:
        pass
    print("  [INFO] Using in-process Starlette TestClient (serverless ASGI mode)")
    from starlette.testclient import TestClient
    import main
    return TestClient(main.app)


def test_catalog_matching_and_tax_math():
    banner("1. Product Catalog Matching & 18% GST Calculation")
    import orders

    sample_text = "I need 2 ergo pro 3d chairs and 1 smartdesk for our Bangalore office"
    items = orders.match_catalog_items(sample_text)
    print(f"  Matched {len(items)} product line items from text:")
    for it in items:
        print(f"    • {it['qty']}x {it['name']} @ Rs {it['unit_price']} = Rs {it['total']}")

    assert len(items) == 2, f"Expected 2 items, matched {len(items)}"
    ergo_chair = next((i for i in items if i["product_id"] == "ergo_pro_3d"), None)
    desk = next((i for i in items if i["product_id"] == "smart_desk"), None)

    assert ergo_chair is not None, "Failed to match ergo pro 3d chair"
    assert ergo_chair["qty"] == 2
    assert desk is not None, "Failed to match smartdesk"
    assert desk["qty"] == 1

    subtotal, tax, total = orders.calculate_order_totals(items)
    expected_subtotal = (2 * 14999.00) + (1 * 24999.00)  # 29998 + 24999 = 54997.00
    expected_tax = round(expected_subtotal * 0.18, 2)     # 9899.46
    expected_total = round(expected_subtotal + expected_tax, 2)  # 64896.46

    print(f"  Subtotal: Rs {subtotal:,.2f} | 18% GST: Rs {tax:,.2f} | Grand Total: Rs {total:,.2f}")
    assert subtotal == expected_subtotal
    assert tax == expected_tax
    assert total == expected_total
    print("  PASS: Catalog matching and tax mathematics verified.")


def test_order_creation_and_receipt(client):
    banner("2. Order Creation & WhatsApp Receipt Delivery (/api/orders/create)")
    order_payload = {
        "wa_id": "919876543210",
        "customer_name": "Rohan Deshmukh",
        "text": "Please place an order for 4 ergo pro 3d chairs",
        "notes": "Express delivery to Koramangala",
    }
    resp = client.post("/api/orders/create", json=order_payload)
    assert resp.status_code == 200, f"Order creation failed: {resp.text}"
    data = resp.json()
    assert data.get("ok") is True
    order = data.get("order", {})
    assert order.get("wa_id") == "919876543210"
    assert order.get("total", 0) > 0
    receipt = data.get("receipt", "")
    assert "Order Confirmed!" in receipt
    assert "Aegis Ergo Pro 3D" in receipt
    assert "Grand Total:" in receipt
    print(f"  ✓ Order created successfully: #{order.get('id')} (Total: Rs {order.get('total'):,.2f})")
    print("  ✓ WhatsApp receipt formatted:")
    for line in receipt.splitlines()[:5]:
        print(f"    {line}")
    print("  PASS: Order creation and invoice receipt verified.")


def test_order_management(client):
    banner("3. Order Listing & Status Update (/api/orders & PATCH)")
    # 1. List orders
    r_list = client.get("/api/orders")
    assert r_list.status_code == 200
    orders_data = r_list.json()
    assert orders_data.get("count", 0) >= 1
    recent_order = orders_data["orders"][0]
    order_id = recent_order["id"]
    print(f"  ✓ Retrieved {orders_data['count']} active orders in system")

    # 2. Update status to fulfilled
    r_patch = client.patch(f"/api/orders/{order_id}", json={"status": "fulfilled"})
    assert r_patch.status_code == 200
    p_data = r_patch.json()
    assert p_data.get("ok") is True
    assert p_data.get("order", {}).get("status") == "fulfilled"
    print(f"  ✓ Order #{order_id} status updated to 'fulfilled'")
    print("  PASS: Order lifecycle transitions verified.")


def test_booking_slots(client):
    banner("4. Showroom Booking Slot Generation (/api/bookings/slots)")
    resp = client.get("/api/bookings/slots?days_ahead=5")
    assert resp.status_code == 200
    data = resp.json()
    slots = data.get("slots", [])
    print(f"  ✓ Generated {len(slots)} available slots across next 5 days")
    assert len(slots) > 0, "No booking slots generated"
    first_slot = slots[0]
    assert "slot_start" in first_slot
    assert "label" in first_slot
    print(f"  Sample available slot: {first_slot['label']} ({first_slot['slot_start']})")
    print("  PASS: Slot availability engine verified.")


def test_appointment_booking(client):
    banner("5. Appointment Booking & Collision Prevention (/api/bookings/create)")
    # Get available slots
    slots = client.get("/api/bookings/slots?days_ahead=3").json().get("slots", [])
    assert len(slots) > 0, "Need at least 1 slot for testing"
    target_slot = slots[0]

    booking_payload = {
        "wa_id": "919988776655",
        "customer_name": "Meera Nambiar",
        "service": "Executive Showroom Tour & Chair Fitting",
        "slot_start": target_slot["slot_start"],
        "slot_end": target_slot["slot_end"],
        "location": "100 Feet Road, Indiranagar, Bangalore",
    }

    # 1. Book appointment
    r_book = client.post("/api/bookings/create", json=booking_payload)
    assert r_book.status_code == 200, f"Booking failed: {r_book.text}"
    b_data = r_book.json()
    assert b_data.get("ok") is True
    apt = b_data.get("appointment", {})
    assert apt.get("slot_start") == target_slot["slot_start"]
    print(f"  ✓ Appointment scheduled: #{apt.get('id')} for {apt.get('customer_name')}")
    print(f"  ✓ Confirmation summary: {b_data.get('confirmation', '').splitlines()[0]}")

    # 2. Collision test: attempt to book the exact same slot
    collision_payload = {
        "wa_id": "919123456789",
        "customer_name": "Another Client",
        "slot_start": target_slot["slot_start"],
    }
    r_collision = client.post("/api/bookings/create", json=collision_payload)
    assert r_collision.status_code == 400, "Collision prevention failed: duplicate slot was booked!"
    print(f"  ✓ Double-booking rejected with 400: '{r_collision.json().get('error')}'")

    # 3. List bookings
    r_apts = client.get("/api/bookings")
    assert r_apts.status_code == 200
    assert r_apts.json().get("count", 0) >= 1
    print(f"  ✓ Verified appointment persisted in database")
    print("  PASS: Appointment booking and collision prevention verified.")


def test_vercel_crons_manifest():
    banner("6. Vercel Serverless Crons Manifest Validation (vercel.json)")
    vercel_path = ROOT_DIR / "vercel.json"
    assert vercel_path.exists(), "vercel.json missing"
    with open(vercel_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "crons" in data, "vercel.json must declare 'crons' for automated scheduling"
    crons = data["crons"]
    print(f"  ✓ vercel.json contains {len(crons)} serverless cron jobs:")
    paths = [c["path"] for c in crons]
    for c in crons:
        print(f"    • {c['path']} (schedule: '{c['schedule']}')")

    assert "/api/campaigns/followup" in paths, "Missing automated abandoned lead follow-up cron"
    assert "/api/drip/trigger" in paths, "Missing automated daily drip sequence cron"
    print("  PASS: Serverless cron jobs correctly configured.")


def run_all_phase7_tests():
    banner("AEGISBOT — PHASE 7 COMPREHENSIVE VERIFICATION SUITE")
    print("Validating Autonomous Commerce, Appointment Booking & Cloud Crons...")

    test_catalog_matching_and_tax_math()

    client = get_client()
    test_order_creation_and_receipt(client)
    test_order_management(client)
    test_booking_slots(client)
    test_appointment_booking(client)
    test_vercel_crons_manifest()

    banner("ALL PHASE 7 ENTERPRISE VERIFICATIONS PASSED CLEANLY (100%)")


if __name__ == "__main__":
    run_all_phase7_tests()

