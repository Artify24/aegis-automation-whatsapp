"""Phase 6 Comprehensive Enterprise Verification Suite:
1. Vercel Serverless Configuration & Manifest Validation (vercel.json)
2. Vercel Serverless Entrypoint Integrity (api/index.py)
3. Zero Railway Artifacts & 1-Click Launcher Verification (run.bat & run.sh)
4. Production Health & Telemetry Endpoints (/health & /api/health)
5. Meta WhatsApp Cloud API Webhook Handshake Verification (/webhook/whatsapp)
6. Serverless Storage Resilience (PDF Proposal & System Backup Generation)
7. Multi-Tenant Switching & RAG Knowledge Retrieval Under Serverless Runtime
"""
from __future__ import annotations

import io
import json
import os
import sys
import zipfile
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
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
            return httpx.Client(base_url=BASE_URL, timeout=20.0)
    except Exception:
        pass
    print("  [INFO] Using in-process Starlette TestClient (serverless ASGI mode)")
    from starlette.testclient import TestClient
    import main
    return TestClient(main.app)


def test_vercel_configuration():
    banner("1. Vercel Configuration & Serverless Manifest Validation")
    vercel_path = ROOT_DIR / "vercel.json"
    assert vercel_path.exists(), "vercel.json not found in project root"

    with open(vercel_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("  ✓ vercel.json is valid JSON")
    assert "rewrites" in data, "Missing 'rewrites' section in vercel.json"
    assert any("destination" in r and "api/index" in r["destination"] for r in data["rewrites"]), (
        "vercel.json must rewrite routes to api/index entrypoint"
    )
    print("  ✓ vercel.json rewrites configured correctly for serverless routing")

    if "functions" in data:
        fn_cfg = data["functions"].get("api/index.py", {})
        assert fn_cfg.get("maxDuration", 0) >= 30, "maxDuration should be at least 30s for AI inference"
        print(f"  ✓ Function maxDuration configured to {fn_cfg.get('maxDuration')}s")

    print("  PASS: Vercel serverless manifest successfully validated.")


def test_vercel_entrypoint():
    banner("2. Vercel Serverless Entrypoint (api/index.py)")
    entry_path = ROOT_DIR / "api" / "index.py"
    assert entry_path.exists(), "api/index.py does not exist"

    # Test importing api.index directly
    try:
        import api.index as vercel_app
        assert hasattr(vercel_app, "app"), "api/index.py does not export 'app'"
        print("  ✓ api/index.py successfully loaded and exported FastAPI 'app'")
    except Exception as e:
        assert False, f"Failed to import api/index.py: {e}"

    print("  PASS: Vercel entrypoint is fully operational.")


def test_launchers_and_zero_railway():
    banner("3. 1-Click Launchers & Zero Railway Artifacts")
    # 1. Check launchers
    bat_file = ROOT_DIR / "run.bat"
    sh_file = ROOT_DIR / "run.sh"
    assert bat_file.exists(), "run.bat missing"
    assert sh_file.exists(), "run.sh missing"

    bat_text = bat_file.read_text(encoding="utf-8")
    assert "uvicorn main:app" in bat_text, "run.bat must launch uvicorn"
    assert "requirements.txt" in bat_text, "run.bat must check requirements"
    print("  ✓ run.bat validated (Windows 1-click launcher)")

    sh_text = sh_file.read_text(encoding="utf-8")
    assert "uvicorn main:app" in sh_text, "run.sh must launch uvicorn"
    print("  ✓ run.sh validated (Unix/macOS 1-click launcher)")

    # 2. Assert NO Railway files exist
    railway_files = [
        ROOT_DIR / "railway.json",
        ROOT_DIR / "Procfile",
        ROOT_DIR / "nixpacks.toml",
        ROOT_DIR / ".railwayignore",
    ]
    for rf in railway_files:
        assert not rf.exists(), f"Found Railway artifact '{rf.name}'! Deployment must be Vercel-only."
    print("  ✓ Verified: Zero Railway configuration files present in workspace.")
    print("  PASS: Launchers verified and Railway-free.")


def test_health_telemetry(client):
    banner("4. Production Health & Telemetry Endpoints")
    for path in ["/health", "/api/health"]:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} returned {resp.status_code}"
        data = resp.json()
        assert data.get("status") in ("ok", "degraded"), f"Unexpected status {data.get('status')}"
        assert data.get("business"), "Missing business name in health payload"
        assert data.get("active_tenant_id"), "Missing active_tenant_id in health payload"
        assert data.get("llm_model"), "Missing llm_model in health payload"
        assert isinstance(data.get("knowledge_docs"), list), "knowledge_docs must be a list"
        print(f"  ✓ {path} OK -> Business: '{data['business']}' | Model: {data['llm_model']} | Docs: {len(data['knowledge_docs'])}")

    print("  PASS: Health and monitoring telemetry fully operational.")


def test_meta_webhook_handshake(client):
    banner("5. Meta WhatsApp Cloud API Webhook Handshake")
    import config

    # Valid token check
    verify_token = config.WA_VERIFY_TOKEN
    challenge_val = "9988776655"
    resp = client.get(f"/webhook/whatsapp?hub.mode=subscribe&hub.verify_token={verify_token}&hub.challenge={challenge_val}")
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    assert resp.text == challenge_val, f"Expected challenge '{challenge_val}', got '{resp.text}'"
    print("  ✓ Valid verification handshake succeeded with challenge echo.")

    # Invalid token check
    bad_resp = client.get(f"/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=incorrect-token&hub.challenge={challenge_val}")
    assert bad_resp.status_code == 403, f"Expected 403 Forbidden for bad token, got {bad_resp.status_code}"
    print("  ✓ Invalid verify_token correctly rejected with HTTP 403 Forbidden.")
    print("  PASS: Meta WhatsApp Cloud API webhook handshake verified.")


def test_serverless_storage_resilience(client):
    banner("6. Serverless Storage Resilience (PDF Quotes & Backups)")
    # 1. Generate PDF Quotation
    quote_payload = {
        "lead_id": 901,
        "name": "Vikram Malhotra",
        "phone": "919876543210",
        "requirement": "4 executive boss chairs and 8 ergo pro 3d chairs",
        "location": "Whitefield, Bangalore",
        "budget": "Rs 1,80,000",
        "timeline": "Immediate",
    }
    r_quote = client.post("/api/quotes/generate", json=quote_payload)
    assert r_quote.status_code == 200, f"Quote generation failed: {r_quote.text}"
    q_data = r_quote.json()
    assert q_data.get("ok") is True
    assert "download_url" in q_data
    print(f"  ✓ Executive PDF Proposal generated: {q_data.get('filename')}")

    # Verify download
    r_dl = client.get(q_data["download_url"])
    assert r_dl.status_code == 200
    assert r_dl.content.startswith(b"%PDF"), "Downloaded quote is not a valid PDF binary"
    print(f"  ✓ Proposal PDF download verified ({len(r_dl.content)} bytes, valid PDF header)")

    # 2. Generate System Backup Snapshot
    r_backup = client.post("/api/backup/create")
    assert r_backup.status_code == 200, f"Backup creation failed: {r_backup.text}"
    b_data = r_backup.json()
    assert b_data.get("ok") is True
    print(f"  ✓ System snapshot ZIP generated: {b_data.get('filename')} ({b_data.get('size_kb')} KB)")

    # Verify backup download and ZIP content
    r_bdown = client.get(b_data["download_url"])
    assert r_bdown.status_code == 200
    with zipfile.ZipFile(io.BytesIO(r_bdown.content)) as zf:
        names = zf.namelist()
        assert "manifest.json" in names, "Backup ZIP missing manifest.json"
        assert "db/leads.json" in names, "Backup ZIP missing db/leads.json"
        print(f"  ✓ System backup archive inspected ({len(names)} archived entities)")

    print("  PASS: Serverless storage and fallback mechanisms functioning smoothly.")


def test_tenant_switching_and_rag(client):
    banner("7. Multi-Tenant Switching & RAG Knowledge Retrieval")
    # Switch to Dr. Smile Dental Clinic
    s1 = client.post("/api/tenants/switch", json={"tenant_id": "dr_smile_dental"})
    assert s1.status_code == 200
    assert s1.json().get("active_tenant", {}).get("id") == "dr_smile_dental"
    h1 = client.get("/health").json()
    assert h1.get("active_tenant_id") == "dr_smile_dental"
    print("  ✓ Switched active profile to: 'Dr. Smile Dental & Orthodontics'")

    # Switch back to Aegis Workspace Solutions
    s2 = client.post("/api/tenants/switch", json={"tenant_id": "aegis_workspace"})
    assert s2.status_code == 200
    h2 = client.get("/health").json()
    assert h2.get("active_tenant_id") == "aegis_workspace"
    print("  ✓ Restored active profile to: 'Aegis Workspace Solutions'")

    # Test direct RAG answer
    r_rag = client.post("/dev/ask", json={"question": "What is the warranty policy on chairs?"})
    assert r_rag.status_code == 200
    rag_data = r_rag.json()
    assert rag_data.get("matched") is True, "RAG failed to match official warranty documents"
    print(f"  ✓ RAG FAQ Answer resolved: {rag_data.get('reply')[:75]}...")

    print("  PASS: Multi-tenant profile switching and RAG retrieval verified.")


def run_all_phase6_tests():
    banner("AEGISBOT — PHASE 6 COMPREHENSIVE VERIFICATION SUITE")
    print("Validating Vercel Cloud Serverless Readiness & Enterprise Reliability...")

    test_vercel_configuration()
    test_vercel_entrypoint()
    test_launchers_and_zero_railway()

    client = get_client()
    test_health_telemetry(client)
    test_meta_webhook_handshake(client)
    test_serverless_storage_resilience(client)
    test_tenant_switching_and_rag(client)

    banner("ALL PHASE 6 ENTERPRISE VERIFICATIONS PASSED CLEANLY (100%)")


if __name__ == "__main__":
    run_all_phase6_tests()

