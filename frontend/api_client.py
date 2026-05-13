"""
SME-Flow AI — Backend API İstemcisi
"""
import httpx

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 30.0


def login(username: str, password: str) -> dict:
    try:
        r = httpx.post(
            f"{BASE_URL}/api/auth/token",
            data={"username": username, "password": password},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return {"success": True, "token": r.json()["access_token"]}
    except httpx.HTTPStatusError as e:
        return {"success": False, "error": f"Giriş hatası: {e.response.status_code}"}
    except Exception as e:
        return {"success": False, "error": f"Bağlantı hatası: {e}"}


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def get_inventory(token: str, category: str = None, status_filter: str = None) -> list:
    try:
        params = {}
        if category:
            params["category"] = category
        if status_filter:
            params["status_filter"] = status_filter
        r = httpx.get(f"{BASE_URL}/api/inventory/", headers=_headers(token), params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def get_inventory_stats(token: str) -> dict:
    try:
        r = httpx.get(f"{BASE_URL}/api/inventory/summary/stats", headers=_headers(token), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def get_critical_stock(token: str) -> list:
    try:
        r = httpx.get(f"{BASE_URL}/api/inventory/critical", headers=_headers(token), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def get_suppliers(token: str) -> list:
    try:
        r = httpx.get(f"{BASE_URL}/api/suppliers/", headers=_headers(token), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def get_ai_alerts(token: str) -> list:
    try:
        r = httpx.get(f"{BASE_URL}/api/ai/alerts", headers=_headers(token), timeout=120.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def chat_with_ai(token: str, message: str) -> dict:
    try:
        r = httpx.post(
            f"{BASE_URL}/api/ai/chat",
            headers=_headers(token),
            json={"message": message},
            timeout=60.0,
        )
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        return {"response": f"⚠️ Sunucu hatası ({e.response.status_code}). Lütfen tekrar deneyin.", "tools_used": [], "steps": 0}
    except Exception as e:
        return {"response": f"⚠️ Bağlantı hatası: {e}", "tools_used": [], "steps": 0}


def get_ai_status(token: str) -> dict:
    try:
        r = httpx.get(f"{BASE_URL}/api/ai/status", headers=_headers(token), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {"status": "offline", "model": "N/A", "tools_available": 0, "memory_messages": 0}


def reset_ai_memory(token: str) -> dict:
    try:
        r = httpx.post(f"{BASE_URL}/api/ai/reset-memory", headers=_headers(token), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {"success": False}


def health_check() -> bool:
    try:
        r = httpx.get(f"{BASE_URL}/", timeout=5.0)
        return r.status_code == 200
    except Exception:
        return False
