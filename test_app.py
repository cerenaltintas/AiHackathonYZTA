import os
import sys

os.environ["GEMINI_API_KEY"] = "AIzaSyMockKeyForTestPurposeOnlyDoNotUse"
os.environ["GOOGLE_API_KEY"] = "AIzaSyMockKeyForTestPurposeOnlyDoNotUse"

from fastapi.testclient import TestClient
from app.main import app
from app.core.deps import get_current_user

async def mock_get_current_user():
    return {"sub": "admin"}

app.dependency_overrides[get_current_user] = mock_get_current_user

try:
    with TestClient(app) as client:
        print("\n--- Testing Health Check ---")
        resp = client.get("/")
        print("Status:", resp.status_code)
        print("Body:", resp.json())

        print("\n--- Testing AI Status ---")
        resp = client.get("/api/ai/status")
        print("Status:", resp.status_code)
        print("Body:", resp.json())
        
        print("\n--- Testing AI Agent Chat (Soru: Hangi üründen kaç adet var?) ---")
        chat_data = {"message": "Zeytinyağı stoklarımızda kaç adet kaldı? Acil bilgi verir misin?"}
        resp = client.post("/api/ai/chat", json=chat_data)
        print("Status:", resp.status_code)
        print("Body:", resp.json())

        print("\n--- Testing AI Alerts (Proaktif Stok Uyarıları) ---")
        resp = client.get("/api/ai/alerts")
        print("Status:", resp.status_code)
        if resp.status_code == 200:
            alerts = resp.json()
            print(f"Found Alerts: {len(alerts)}")
            if alerts:
                print(f"Example Alert: {alerts[0]['product_name']} -> {alerts[0]['email_draft'][:50]}...")
        else:
            print("Body:", resp.json())
except Exception as e:
    import traceback
    traceback.print_exc()
