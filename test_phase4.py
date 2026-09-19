"""Phase 4 Automated Verification Suite:
1. PDF Quotation Generation & Download
2. Multi-Stage Automated WhatsApp Drip Nurture Engine
3. Executive Sales Funnel & Category Analytics
4. End-to-End System Health & Performance
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import httpx
import json

BASE = "http://localhost:8000"


def banner(title):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


def run_phase4_tests():
    banner("PHASE 4 TEST SUITE: ENTERPRISE QUOTES, DRIP & ANALYTICS")

    # ── 1. System Health Check ──────────────────────────────────────────────
    banner("1. Server & Engine Health")
    r_health = httpx.get(f"{BASE}/health", timeout=10)
    assert r_health.status_code == 200
    h_data = r_health.json()
    print("Health Status:", h_data.get("status"))
    print("Database:", h_data.get("db"))
    print("Active LLM:", h_data.get("llm_model"))
    print("RAG Chunks:", h_data.get("knowledge_chunks"))
    print("PASS: Core server is running cleanly.")

    # ── 2. PDF Quotation Generation ─────────────────────────────────────────
    banner("2. PDF Quotation Generation & Download")
    quote_payload = {
        "lead_id": 888,
        "name": "Ananya Roy",
        "phone": "919123456789",
        "requirement": "12 workstation desks and 8 ergo lite chairs",
        "location": "Koramangala, Bangalore",
        "budget": "Rs 2,50,000",
        "timeline": "Within 2 weeks",
    }
    r_gen = httpx.post(f"{BASE}/api/quotes/generate", json=quote_payload, timeout=15)
    print("Generate Quote Status:", r_gen.status_code)
    gen_data = r_gen.json()
    print("Generate Quote Response:", gen_data)
    assert r_gen.status_code == 200
    assert gen_data.get("ok") is True
    assert "download_url" in gen_data
    print("PASS: Quotation generated successfully with download URL.")

    # Test downloading the PDF
    download_url = gen_data["download_url"]
    r_dl = httpx.get(f"{BASE}{download_url}", timeout=15)
    print("Download Status:", r_dl.status_code)
    print("Content-Type:", r_dl.headers.get("content-type"))
    print("Downloaded Bytes:", len(r_dl.content))
    assert r_dl.status_code == 200
    assert "application/pdf" in r_dl.headers.get("content-type", "")
    assert r_dl.content.startswith(b"%PDF"), "Response MUST be a valid PDF binary file!"
    print("PASS: Downloaded PDF verified with valid %PDF magic bytes.")

    # ── 3. Multi-Stage Drip Nurture Engine ───────────────────────────────────
    banner("3. Multi-Stage WhatsApp Drip Engine")
    # Trigger Drip Stage 1 (Site inspection offer)
    r_drip1 = httpx.post(f"{BASE}/api/drip/trigger", json={"stage": 1}, timeout=20)
    print("Drip Stage 1 Response:", r_drip1.json())
    assert r_drip1.status_code == 200
    assert r_drip1.json().get("ok") is True

    # Trigger Drip Stage 2 (Quotation follow-up)
    r_drip2 = httpx.post(f"{BASE}/api/drip/trigger", json={"stage": 2}, timeout=20)
    print("Drip Stage 2 Response:", r_drip2.json())
    assert r_drip2.status_code == 200
    assert r_drip2.json().get("ok") is True

    print("PASS: Automated drip sequence executed cleanly across multiple touchpoints.")

    # ── 4. Executive Analytics & Funnel Telemetry ───────────────────────────
    banner("4. Executive Conversion Funnel & Telemetry")
    r_ana = httpx.get(f"{BASE}/api/analytics", timeout=10)
    print("Analytics Status:", r_ana.status_code)
    ana_data = r_ana.json()
    assert r_ana.status_code == 200

    funnel = ana_data.get("funnel", {})
    print("Funnel Metrics:")
    print(f"  • Top of Funnel Inquiries: {funnel.get('inquiries')}")
    print(f"  • Requirements Captured: {funnel.get('captured_leads')}")
    print(f"  • Qualified Hot Leads: {funnel.get('qualified_leads')}")
    print(f"  • Deals Won: {funnel.get('won_deals')}")
    print(f"  • Deal Conversion Rate: {funnel.get('conversion_rate')}")

    demand = ana_data.get("demand_by_category", {})
    print("\nProduct Category Demand:")
    for cat, count in demand.items():
        print(f"  • {cat}: {count} inquiry(ies)")

    tel = ana_data.get("telemetry", {})
    print("\nAI Engine Telemetry:")
    print(f"  • Groq Inference Latency: {tel.get('avg_groq_latency_ms')} ms")
    print(f"  • Whisper Audio Transcription: {tel.get('avg_transcription_ms')} ms")
    print(f"  • Security Guardrails: {tel.get('guardrail_compliance')}")

    assert "funnel" in ana_data
    assert "demand_by_category" in ana_data
    assert "telemetry" in ana_data
    print("\nPASS: Executive analytics returned full conversion funnel and telemetry.")

    banner("ALL PHASE 4 ENTERPRISE CAPABILITIES VERIFIED 100% SUCCESSFULLY!")


if __name__ == "__main__":
    run_phase4_tests()
