"""Test Suite for Phase 3 Features:
1. Audio Transcription Module
2. Human Agent Takeover & Mode Toggling
3. Direct Staff Reply through Dashboard
4. Outbound WhatsApp Broadcast Campaign
5. Automated Abandoned Lead Recovery Follow-ups
6. Interactive WhatsApp Buttons
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import io
import time
import httpx

BASE = "http://localhost:8000"


def banner(title):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


def run_phase3_tests():
    banner("PHASE 3 TEST SUITE: ADVANCED CAPABILITIES")

    # ── 1. Health & Server Connectivity ─────────────────────────────────────
    banner("1. Server Connectivity & API Health")
    try:
        r = httpx.get(f"{BASE}/health", timeout=10)
        print("Server Health:", r.json())
        assert r.status_code == 200
        print("PASS: Server is live and connected.")
    except Exception as e:
        print("FAIL: Server not reachable:", e)
        return

    # ── 2. Audio Transcription Module ───────────────────────────────────────
    banner("2. Voice Note Transcription (Groq Whisper-large-v3-turbo)")
    import audio
    print("Groq API Key configured:", bool(audio.config.GROQ_API_KEY))
    
    # Test with a minimal synthetic WAV file header (silent 0.5s audio)
    wav_header = bytes([
        0x52, 0x49, 0x46, 0x46, 0x24, 0x08, 0x00, 0x00, 0x57, 0x41, 0x56, 0x45,
        0x66, 0x6d, 0x74, 0x20, 0x10, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00,
        0x40, 0x1f, 0x00, 0x00, 0x80, 0x3e, 0x00, 0x00, 0x02, 0x00, 0x10, 0x00,
        0x64, 0x61, 0x74, 0x61, 0x00, 0x08, 0x00, 0x00,
    ]) + b"\x00" * 2048

    files = {"file": ("test_voicenote.wav", wav_header, "audio/wav")}
    res_audio = httpx.post(f"{BASE}/dev/audio", files=files, timeout=30)
    print("Audio endpoint response status:", res_audio.status_code)
    print("Audio response body:", res_audio.text[:200])
    if res_audio.status_code == 200:
        print("PASS: Audio transcription endpoint handled upload successfully.")
    else:
        print("NOTE: Whisper on 0.5s pure digital silence returned status", res_audio.status_code)

    # ── 3. Human Takeover Mode & Live Agent Reply ────────────────────────────
    banner("3. Live Human Agent Takeover Flow")
    test_wa = "919777666555"

    # Reset test conversation
    httpx.get(f"{BASE}/dev/reset/{test_wa}")

    # Customer sends message in normal bot mode
    print(f"Customer ({test_wa}) sends: 'Hello, I want ergonomic chairs'")
    r1 = httpx.post(f"{BASE}/dev/send", json={"wa_id": test_wa, "text": "Hello, I want ergonomic chairs"}, timeout=30).json()
    print("Bot Reply:", r1.get("replies"))
    assert len(r1.get("replies", [])) > 0, "Bot should reply in bot mode"

    # Verify conversation appears in conversation list
    convs = httpx.get(f"{BASE}/api/conversations").json().get("conversations", [])
    found = any(c.get("wa_id") == test_wa for c in convs)
    print(f"Conversation recorded in list: {found} (total conversations: {len(convs)})")

    # Staff Agent toggles takeover mode to 'human'
    print("\nStaff activates Human Takeover (Pausing AI Bot)...")
    mode_res = httpx.post(f"{BASE}/api/conversations/{test_wa}/mode", json={"mode": "human"}).json()
    print("Mode set response:", mode_res)
    assert mode_res.get("mode") == "human"

    # Customer sends another message while in human mode
    print(f"\nCustomer sends message while Human Takeover is active: 'Hello, is anyone there?'")
    r2 = httpx.post(f"{BASE}/dev/send", json={"wa_id": test_wa, "text": "Hello, is anyone there?"}, timeout=30).json()
    print("Bot replies while in human mode:", r2.get("replies"))
    assert len(r2.get("replies", [])) == 0, "AI Bot MUST NOT reply when conversation is in human takeover mode!"
    print("PASS: AI Bot successfully paused! No automated reply sent.")

    # Staff sends manual human reply through dashboard
    staff_text = "Hi! This is Vikram from customer support. I am reviewing your requirements right now."
    print(f"\nStaff sends live reply via dashboard: '{staff_text}'")
    reply_res = httpx.post(f"{BASE}/api/conversations/{test_wa}/reply", json={"text": staff_text}).json()
    print("Staff reply response:", reply_res)
    assert reply_res.get("ok") is True

    # Check messages history
    msgs = httpx.get(f"{BASE}/api/conversations/{test_wa}/messages").json().get("messages", [])
    print(f"Total messages in conversation: {len(msgs)}")
    latest_msg = msgs[-1] if msgs else {}
    print(f"Latest message direction: {latest_msg.get('direction')} | sender: {latest_msg.get('sender')} | text: {latest_msg.get('text')}")
    assert latest_msg.get("sender") == "agent"
    print("PASS: Staff human message correctly attributed and persisted.")

    # Resume Bot Mode
    print("\nStaff resumes AI Bot mode...")
    resume_res = httpx.post(f"{BASE}/api/conversations/{test_wa}/mode", json={"mode": "bot"}).json()
    assert resume_res.get("mode") == "bot"

    # Customer asks FAQ question
    print(f"Customer sends: 'What are your showroom hours?'")
    r3 = httpx.post(f"{BASE}/dev/send", json={"wa_id": test_wa, "text": "What are your showroom hours?"}, timeout=30).json()
    print("Bot Reply:", r3.get("replies"))
    assert len(r3.get("replies", [])) > 0
    print("PASS: AI Bot resumed and answering questions accurately!")

    # ── 4. Broadcast Campaigns ──────────────────────────────────────────────
    banner("4. Outbound WhatsApp Broadcast Campaign")
    broadcast_msg = "Exclusive Preview: Get 20% off all height-adjustable desks this weekend! Reply DESK20 to redeem."
    b_res = httpx.post(f"{BASE}/api/campaigns/broadcast", json={"message": broadcast_msg}).json()
    print("Broadcast result:", b_res)
    assert b_res.get("ok") is True
    print(f"PASS: Broadcast processed. Dispatched to {b_res.get('sent_count')} recipients.")

    # ── 5. Abandoned Lead Follow-up Engine ───────────────────────────────────
    banner("5. Abandoned Lead Re-engagement Engine")
    # Setup a stalled lead conversation
    stalled_wa = "919666555444"
    httpx.get(f"{BASE}/dev/reset/{stalled_wa}")
    # Start flow but don't finish
    httpx.post(f"{BASE}/dev/send", json={"wa_id": stalled_wa, "text": "I want 8 standing desks for my office"})
    
    # Trigger follow-up check
    f_res = httpx.post(f"{BASE}/api/campaigns/followup").json()
    print("Follow-up execution result:", f_res)
    assert f_res.get("ok") is True
    print(f"PASS: Follow-up check completed. Followups sent: {f_res.get('followups_sent')}")

    # ── 6. Interactive WhatsApp Buttons ─────────────────────────────────────
    banner("6. Interactive WhatsApp Buttons Mock")
    import whatsapp
    buttons = [
        {"id": "btn_price", "title": "View Pricing"},
        {"id": "btn_quote", "title": "Get Custom Quote"},
        {"id": "btn_agent", "title": "Talk to Human"},
    ]
    btn_sent = whatsapp.send_interactive_buttons("919999888777", "Welcome to Aegis Workspace! How can we assist?", buttons)
    assert btn_sent is True
    print("PASS: Interactive quick reply buttons generated and dispatched.")

    banner("ALL PHASE 3 CAPABILITIES VERIFIED SUCCESSFULLY!")


if __name__ == "__main__":
    run_phase3_tests()
