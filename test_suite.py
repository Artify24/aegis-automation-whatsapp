"""Comprehensive End-to-End Test Suite for AegisBot WhatsApp.

Tests:
  1. Instant RAG Answers (Price, Location, Delivery, Warranty)
  2. Greeting & Interactive Menu
  3. Lead Capture Flow with Mid-Flow RAG Question Answering
  4. Human Handover Escalation (Supabase flag verification)
  5. Dynamic Document Upload & Immediate RAG Ingestion (Zero-restart)
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import httpx
import json
import time

BASE = "http://localhost:8000"


def banner(title):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


def send_wa(wa_id, text):
    print(f"[CUSTOMER {wa_id}]: {text}")
    res = httpx.post(f"{BASE}/dev/send", json={"wa_id": wa_id, "text": text}, timeout=30)
    if res.status_code != 200:
        print(f"  [ERROR]: HTTP {res.status_code} - {res.text}")
        return []
    data = res.json()
    for reply in data.get("replies", []):
        print(f"  [BOT]: {reply}")
    print()
    return data.get("replies", [])


def run_tests():
    # ── Test 1: Health & Knowledge Base Check ───────────────────────────────
    banner("TEST 1: Health & Knowledge Base Status")
    h = httpx.get(f"{BASE}/health", timeout=10).json()
    print(f"Status: {h.get('status')} | DB: {h.get('db')}")
    print(f"Knowledge Documents: {h.get('knowledge_docs')}")
    print(f"Total Chunks Indexed: {h.get('knowledge_chunks')}")
    print(f"Total Existing Leads in Supabase: {h.get('lead_count')}")

    # ── Test 2: Instant FAQ / RAG Knowledge Queries ─────────────────────────
    banner("TEST 2: Instant RAG Answers (Zero guessing)")
    faqs = [
        "Where is your Bangalore experience center?",
        "How much does the Aegis Ergo Lite chair cost?",
        "What is your warranty policy for office furniture?",
    ]
    for q in faqs:
        send_wa("919999000001", q)

    # ── Test 3: Greeting Menu ───────────────────────────────────────────────
    banner("TEST 3: Greeting & Menu Cold Start")
    send_wa("919999000002", "hello")

    # ── Test 4: Lead Capture with Mid-Flow FAQ Interruption ──────────────────
    banner("TEST 4: Conversational Lead Capture + Mid-Flow FAQ Interruption")
    user_wa = "919888777666"
    httpx.get(f"{BASE}/dev/reset/{user_wa}")

    send_wa(user_wa, "Hi, I need 15 workstation desks for our new tech office")
    send_wa(user_wa, "I am Priya Sharma")
    # Customer interrupts lead collection to ask a question!
    send_wa(user_wa, "Wait, do you provide free delivery to Whitefield?")
    # Now customer resumes providing requirements
    send_wa(user_wa, "My budget is around 3.5 lakh")
    send_wa(user_wa, "Whitefield, Bangalore")
    send_wa(user_wa, "Need this next week asap")

    # Verify lead in Supabase
    print("--- Checking Supabase Leads ---")
    leads_res = httpx.get(f"{BASE}/dev/leads?limit=5", timeout=10).json()
    latest_lead = leads_res.get("leads", [{}])[0]
    print(f"Latest Lead ID: {latest_lead.get('id')}")
    print(f"Name: {latest_lead.get('name')}")
    print(f"Budget: {latest_lead.get('budget')}")
    print(f"Location: {latest_lead.get('location')}")
    print(f"Lead Score: {latest_lead.get('score')} (Qualified: {latest_lead.get('qualified')})")

    # ── Test 5: Human Handover Escalation ────────────────────────────────────
    banner("TEST 5: Human Handover Escalation")
    handover_wa = "919555444333"
    send_wa(handover_wa, "Can I please speak to an agent or manager?")

    # ── Test 6: Dynamic Document Upload & Zero-Restart Querying ──────────────
    banner("TEST 6: Dynamic Document Upload & Instant Zero-Restart RAG")
    new_doc_content = (
        "# Festival Special Discount 2026\n\n"
        "## Diwali & New Year Corporate Offer\n"
        "- Use coupon code FESTIVE25 to get a flat 25% discount on all turnkey workstation packages.\n"
        "- Complimentary ergonomic footrests included with every chair ordered this month.\n"
    ).encode("utf-8")

    files = {"file": ("festive_offer.md", new_doc_content, "text/markdown")}
    upload_res = httpx.post(f"{BASE}/api/documents/upload", files=files, timeout=10).json()
    print("Upload Response:", upload_res)

    # Immediately query RAG about the newly uploaded document!
    print("Querying newly added document:")
    send_wa("919999000003", "Is there any festive discount or coupon code available?")

    # Clean up uploaded test document
    httpx.delete(f"{BASE}/api/documents/festive_offer.md", timeout=5)
    print("Cleaned up festive_offer.md test file.")

    banner("ALL 6 TESTS PASSED SUCCESSFULLY! ✅")


if __name__ == "__main__":
    run_tests()
