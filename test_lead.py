import sys
sys.stdout.reconfigure(encoding="utf-8")
import httpx, json, time

BASE = "http://localhost:8000"
WA = "919111222333"

def get_client():
    try:
        resp = httpx.get(f"{BASE}/health", timeout=1.0)
        if resp.status_code in (200, 500):
            return httpx.Client(base_url=BASE, timeout=60.0)
    except Exception:
        pass
    from starlette.testclient import TestClient
    import main
    return TestClient(main.app)

client = get_client()

def send(text):
    print("USER:", text)
    r = client.post("/dev/send", json={"wa_id": WA, "text": text})
    if r.status_code == 200:
        for reply in r.json().get("replies", []):
            print("  BOT:", reply[:140])
    else:
        print("  ERROR", r.status_code, r.text[:200])
    print()

h = client.get("/health").json()
db_status = (h.get("db") or "").encode("ascii","replace").decode("ascii")
print("HEALTH:", h.get("status"), "| db:", db_status, "| leads:", h.get("lead_count"))
print()

send("hi I want to buy office furniture, budget around 2 lakh")
send("My name is Arjun Mehta")
send("Bangalore, Koramangala")
send("Next week, urgent")

print("=== SUPABASE LEADS ===")
leads = client.get("/dev/leads").json()
count = leads.get("count", 0)
print("Total leads:", count)
for lead in leads.get("leads", []):
    print("  id=%s name=%s budget=%s location=%s score=%s qualified=%s" % (
        lead.get("id"), lead.get("name"), lead.get("budget"),
        lead.get("location"), lead.get("score"), lead.get("qualified")
    ))
