# AegisBot — WhatsApp AI Business Assistant & Lead Machine

> **Handover & Full System Context**: See [CONTEXT.md](file:///d:/StandardProjects/aegis-automation-products/test/CONTEXT.md) for complete architecture, API schemas, testing steps, and troubleshooting.

Production-grade, enterprise WhatsApp AI assistant built with **FastAPI**, **Groq LLM (`qwen/qwen3.8-27b`)**, **aegis-security-sdk**, **Supabase**, and an embedded zero-latency **RAG Knowledge Engine**.

---

## 🚀 Key Capabilities

1. **⚡ Instant 24/7 Replies**
   - Responds to customer inquiries in seconds.
   - Powered by high-speed Groq inference guarded by `aegis-security-sdk`.

2. **📚 Knows Your Business (Zero-Hallucination RAG)**
   - Upload business documents (price lists, menus, policies, catalogs, FAQs) in `.md`, `.txt`, `.json`, `.csv`, or `.pdf`.
   - Pure-Python BM25 keyword search with hot-reloading — zero external embedding API costs and sub-millisecond retrieval.
   - Strict adherence to official business documents.

3. **🔄 Repetitive Questions Auto-Answered**
   - Automatically answers *"Price?"*, *"Location?"*, *"Timings?"*, *"Do you deliver?"*, *"Warranty?"*.
   - **Smart Mid-Flow Answering**: If a customer interrupts lead capture to ask an FAQ (e.g. *"Wait, do you deliver to my area?"*), AegisBot answers the question from your docs and smoothly resumes lead collection!

4. **🎯 Automated Lead Capture & Supabase Sync**
   - Conversations extract customer Name, Requirement, Budget, Location, and Timeline.
   - Calculates buy-signal score (0–100) and marks qualified hot leads (`score >= 60`).
   - Directly syncs leads, customers, and message logs to **Supabase** database tables in real time.

5. **🎙️ Voice Note Audio Transcription**
   - Inbound WhatsApp audio notes (`.ogg`, `.mp3`, `.wav`, `.m4a`) are automatically transcribed in ~200ms using Groq `whisper-large-v3-turbo` before hitting the AI engine.

6. **💬 Live Agent Takeover & Inbox**
   - Real-time chat stream in the admin dashboard.
   - Staff can toggle Human Takeover Mode with one click, pausing automated bot replies and replying directly to the customer's WhatsApp.

7. **📢 WhatsApp Outbound Campaigns & Follow-up Nudges**
   - Broadcast personalized announcements (`{{name}}`) to captured leads by status filter.
   - Automated Abandoned Lead Recovery Engine detects stalled questionnaire drop-offs and sends friendly re-engagement nudges.

8. **💻 Dark-Mode Glassmorphism Web Dashboard**
   - Accessible at `http://localhost:8000/`.
   - 7 full workspaces: Leads CRM Table, Executive Funnel Analytics, Live Agent Takeover Inbox, Broadcast & Campaigns, Live WhatsApp Phone Simulator, Knowledge Base Document Manager, and Settings.

9. **☁️ Turnkey Vercel Serverless Deployment (Zero Railway)**
   - Pre-configured for zero-maintenance Vercel hosting via `vercel.json` and `api/index.py`.
   - Ephemeral storage hardening: automatic `/tmp` fallback for PDF quotations and backup archives on read-only serverless filesystems.

10. **🚀 1-Click Launchers**
    - Windows: Double-click `run.bat` (automatically installs requirements, boots server, opens browser).
    - Linux/macOS: Run `./run.sh`.

11. **🛒 Autonomous Commerce & Order Management**
    - Natural language catalog matching, itemized line items, and statutory 18% GST calculation.
    - Instant order tracking and formatted WhatsApp delivery receipts.

12. **📅 Smart Showroom Visit & Appointment Booking**
    - Dynamic slot generator matching business hours (10 AM - 7 PM, excluding Sundays).
    - Collision prevention guaranteeing zero double-bookings.
    - WhatsApp confirmation with showroom directions and consultation expectations.

13. **⏰ Vercel Cloud Serverless Crons (4 Automated Schedules)**
    - Hourly automated stalled lead recovery (`/api/campaigns/followup`).
    - Daily morning drip sequence advancement (`/api/drip/trigger`).
    - Daily 9:00 AM upcoming appointment reminders (`/api/campaigns/reminders`).
    - Weekly Monday 11:00 AM customer win-back VIP discounts (`/api/campaigns/winback`).

14. **🔔 Proactive Appointment Reminders & Customer Win-Back**
    - Proactive WhatsApp reminders sent before booked showroom consultations (`reminders.py`).
    - Automatic dormancy scanner re-engaging inactive leads with VIP savings promotions (`winback.py`).

15. **📜 Custom Business Policies & Compliance Engine**
    - Deterministic policy enforcement for 7-day returns, 24-hr 100% refunds, bespoke fabrication rules, free Bangalore delivery over ₹10k, DPDP/GDPR phone masking, and Net-30 bulk credit terms (`policies.py`).
    - Hot-reloaded into pure-Python BM25 RAG engine (`knowledge/custom_policies.md`) for instant, zero-hallucination WhatsApp answers.

16. **🏆 Master 9-Stage Enterprise Certification**
    - Single-command automated verification certifying all 9 phases end-to-end (`test_master_suite.py`).

---

## 📂 Project Structure

```
d:\StandardProjects\aegis-automation-products\test\
├── CONTEXT.md               # Complete handover, architecture, and onboarding guide
├── vercel.json              # Vercel serverless routing, crons & function configuration
├── run.bat                  # 1-click Windows launcher (detects Python, checks deps, boots app)
├── run.sh                   # 1-click Linux/macOS launcher
├── api/
│   └── index.py             # Vercel serverless ASGI entrypoint (re-exports FastAPI app)
├── knowledge/               # Drop business documents here (auto-indexed in <1s!)
│   ├── catalog_pricing.md   # Products, workstations, packages
│   ├── company_info.json    # Business metadata, store hours, address
│   └── faq.md               # Hours, location, delivery, warranty
├── static/
│   ├── index.html           # Single-page glassmorphism dashboard (all 7 workspaces)
│   └── quotes/              # Generated executive PDF proposals (quote_{id}.pdf)
├── supabase/
│   └── schema.sql           # SQL schema for Supabase tables
├── audio.py                 # Groq Whisper voice note transcription module
├── backup.py                # Automated system snapshot & disaster recovery (/tmp fallback)
├── bookings.py              # Showroom visit & consultation appointment scheduling engine
├── reminders.py             # Automated appointment reminder scanner & WhatsApp dispatcher
├── winback.py               # Dormant customer win-back & VIP loyalty re-engagement engine
├── campaigns.py             # Outbound broadcasts & abandoned lead follow-ups
├── config.py                # Configuration loaded from .env
├── db.py                    # Supabase persistence layer (customers, convs, messages, leads, orders, apts)
├── drip.py                  # Multi-stage automated WhatsApp drip nurturing engine
├── leads.py                 # Conversational state machine & intelligent router
├── llm.py                   # Groq + Aegis security SDK client with fast fallback
├── main.py                  # FastAPI webhook server & management endpoints
├── notify.py                # WhatsApp staff alerts & CRM webhooks
├── orders.py                # Autonomous commerce, catalog matching & 18% GST order calculator
├── policies.py              # Custom business policies, cancellation windows & evaluation engine
├── quotes.py                # Executive PDF quotation generator using ReportLab (/tmp fallback)
├── rag.py                   # BM25 knowledge retrieval engine & document parsers
├── security.py              # Rate limiting, injection defense & PII masking
├── tenants.py               # Multi-tenant white-label profile manager
├── test_master_suite.py     # Master enterprise system certification suite (Phases 1-9 unified)
├── test_policies.py         # Phase 9 custom business policies test suite
├── test_phase3.py           # Phase 3 automated test suite
├── test_phase4.py           # Phase 4 automated test suite
├── test_phase5.py           # Phase 5 automated test suite
├── test_phase6.py           # Phase 6 comprehensive Vercel & serverless test suite
├── test_phase6_simple.py    # Phase 6 simplified verification suite
├── test_phase7.py           # Phase 7 commerce, appointments & Vercel crons test suite
├── test_suite.py            # Phase 1 & 2 automated test suite
├── whatsapp.py              # Meta WhatsApp Cloud API sender & media downloader
├── .env                     # Your environment secrets
└── requirements.txt         # Dependencies
```

---

## ⚡ Quick Setup & Deployment

### Local 1-Click Launch
- **Windows**: Double-click [`run.bat`](file:///d:/StandardProjects/aegis-automation-products/test/run.bat)
- **Linux/macOS**: Run [`./run.sh`](file:///d:/StandardProjects/aegis-automation-products/test/run.sh)
- Or manually:
  ```powershell
  C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe -m uvicorn main:app --port 8000 --reload
  ```
- Dashboard opens at `http://localhost:8000/`.

---

## ☁️ Production Deployment on Vercel (No Railway)

1. **Push to GitHub**:
   Commit your repository and push to GitHub.
2. **Import into Vercel**:
   - Go to [vercel.com/new](https://vercel.com/new) and select your repository.
   - Vercel automatically detects `vercel.json` and Python functions in `api/index.py`.
3. **Set Environment Variables**:
   In Vercel **Project Settings → Environment Variables**, add:
   ```ini
   BUSINESS_NAME="Aegis Workspace Solutions"
   GROQ_API_KEY=gsk_...
   LLM_MODEL=qwen/qwen3.8-27b
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=sb_publishable_...
   WHATSAPP_PHONE_ID=123456789012345
   WHATSAPP_ACCESS_TOKEN=EAAG...
   WHATSAPP_VERIFY_TOKEN=aegisbot-verify
   CRM_WEBHOOK_URL=https://hooks.zapier.com/hooks/catch/...
   STAFF_NUMBER=919876543210
   ```
4. **Deploy & Connect WhatsApp Webhook**:
   - Click **Deploy**.
   - In Meta Developer Portal, set Webhook Callback URL to:  
     `https://<your-project>.vercel.app/webhook/whatsapp`
   - Set Verify Token to match `WHATSAPP_VERIFY_TOKEN`.

---

## 🧪 Verification & Testing

All suites support dual-mode testing (works with live `:8000` server or standalone ASGI test runner):

```powershell
# 🏆 MASTER ENTERPRISE SYSTEM CERTIFICATION (PHASES 1–9 UNIFIED)
C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe test_master_suite.py

# Run Phase 9 Test Suite (Custom Business Policies & Compliance)
C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe test_policies.py

# Run Phase 7 Enterprise Test Suite (Commerce, Bookings, Vercel Crons)
C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe test_phase7.py

# Run Phase 6 Comprehensive Vercel & Serverless Test Suite
C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe test_phase6.py

# Run Phase 6 Simple Sanity Test
C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe test_phase6_simple.py

# Run Phase 5 Tests (Multi-tenant, Backup, Security, Hinglish)
C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe test_phase5.py

# Run Phase 4 Tests (PDF Quotations, Drip, Funnel Analytics)
C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe test_phase4.py

# Run Phase 3 Tests (Audio Transcription, Takeover Mode, Broadcasts)
C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe test_phase3.py

# Run Phase 1 & 2 Tests (RAG, Lead Flow, Handover)
C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe test_suite.py
```
