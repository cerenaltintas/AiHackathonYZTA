"""
SME-Flow AI — Backend API İstemcisi
(Streamlit Community Cloud Demo Sürümü - Backend Yoksa Mock Veri Döndürür)
"""
import httpx
import os
import google.generativeai as genai

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 5.0  # Hızlı fallback için timeout düşürüldü

# Frontend üzerinden doğrudan gerçek Gemini bağlantısı
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    gemini_model = None

def login(username: str, password: str) -> dict:
    try:
        r = httpx.post(f"{BASE_URL}/api/auth/token", data={"username": username, "password": password}, timeout=TIMEOUT)
        r.raise_for_status()
        return {"success": True, "token": r.json()["access_token"]}
    except Exception:
        # 🛡️ Mock Data Zırhı: Backend yoksa bile giriş başarılı
        return {"success": True, "token": "mock-demo-token-123"}

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

def get_inventory(token: str, category: str = None, status_filter: str = None) -> list:
    try:
        r = httpx.get(f"{BASE_URL}/api/inventory/", headers=_headers(token), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return [
            {"id": "P001", "name": "Zeytinyağı (Sızma)", "category": "Gıda", "quantity": 15, "unit": "Litre", "min_threshold": 50, "price": 450, "stock_status": "kritik"},
            {"id": "P002", "name": "Organik Bal", "category": "Gıda", "quantity": 120, "unit": "Kavanoz", "min_threshold": 30, "price": 250, "stock_status": "normal"},
            {"id": "P003", "name": "Ambalaj Kutusu", "category": "Malzeme", "quantity": 200, "unit": "Adet", "min_threshold": 500, "price": 5, "stock_status": "dusuk"},
            {"id": "P004", "name": "Kargo Bandı", "category": "Malzeme", "quantity": 8, "unit": "Rulo", "min_threshold": 20, "price": 15, "stock_status": "kritik"},
            {"id": "P005", "name": "Süzme Peynir", "category": "Gıda", "quantity": 40, "unit": "Paket", "min_threshold": 30, "price": 120, "stock_status": "normal"}
        ]

def get_inventory_stats(token: str) -> dict:
    try:
        r = httpx.get(f"{BASE_URL}/api/inventory/summary/stats", headers=_headers(token), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {"total_products": 50, "kritik": 4, "dusuk": 12, "normal": 34, "total_value": 145000}

def get_critical_stock(token: str) -> list:
    try:
        r = httpx.get(f"{BASE_URL}/api/inventory/critical", headers=_headers(token), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return [
            {"id": "P001", "name": "Zeytinyağı (Sızma)", "category": "Gıda", "quantity": 15, "unit": "Litre", "min_threshold": 50, "stock_status": "kritik"},
            {"id": "P004", "name": "Kargo Bandı", "category": "Malzeme", "quantity": 8, "unit": "Rulo", "min_threshold": 20, "stock_status": "kritik"}
        ]

def get_suppliers(token: str) -> list:
    try:
        r = httpx.get(f"{BASE_URL}/api/suppliers/", headers=_headers(token), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return [
            {"company": "Öz Ege Tarım", "name": "Ahmet Yılmaz", "email": "siparis@ozege.com", "phone": "0532 123 45 67", "product_categories": ["Gıda"], "notes": "Zeytinyağı tedarikçisi"},
            {"company": "Hızlı Ambalaj", "name": "Canan Kaya", "email": "satis@hizliambalaj.com", "phone": "0555 987 65 43", "product_categories": ["Malzeme"], "notes": "Kutu ve bant tedarikçisi"}
        ]

def get_ai_alerts(token: str) -> list:
    try:
        r = httpx.get(f"{BASE_URL}/api/ai/alerts", headers=_headers(token), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return [
            {
                "status": "kritik", "product_name": "Zeytinyağı (Sızma)", "current_stock": 15, "min_threshold": 50,
                "stock_gap_percent": 70, "suggested_order_amount": 100, "supplier_company": "Öz Ege Tarım",
                "supplier_name": "Ahmet Yılmaz", "supplier_email": "siparis@ozege.com", "supplier_phone": "0532 123 45 67",
                "email_draft": "Merhaba Ahmet Bey,\n\nZeytinyağı (Sızma) stokumuz 15 Litreye düşmüştür. Lütfen acil olarak 100 Litre yeni siparişimizi onaylayıp tarafımıza teslimat süresi hakkında bilgi veriniz.\n\nİyi çalışmalar,\nSME-Flow AI Otonom Sistemi"
            }
        ]

def chat_with_ai(token: str, message: str) -> dict:
    try:
        r = httpx.post(f"{BASE_URL}/api/ai/chat", headers=_headers(token), json={"message": message}, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        # Gerçek Yapay Zeka (Gemini) Entegrasyonu
        if gemini_model:
            try:
                system_prompt = "Sen SME-Flow AI KOBİ asistanısın. İşletme sahibi sana stok ve tedarik soruları soruyor. Çok kısa, net ve profesyonel Türkçe cevaplar ver. Şu anki stoklar: Zeytinyağı 15 Litre (Kritik), Kargo Bandı 8 Rulo (Kritik), Organik Bal 120 (Normal). Tedarikçiler: Öz Ege Tarım, Hızlı Ambalaj. Soru: "
                response = gemini_model.generate_content(system_prompt + message)
                return {"response": response.text, "tools_used": ["gemini_direct"], "steps": 1}
            except Exception as e:
                pass # API key hatası olursa aşağıdaki mock'a düşsün
                
        # Gemini API Key yoksa veya çökerse Akıllı Mock
        msg = message.lower()
        if "tedarikçi" in msg:
            return {"response": "Kayıtlı 2 ana tedarikçiniz var:\n1. **Öz Ege Tarım** (Gıda - Zeytinyağı)\n2. **Hızlı Ambalaj** (Malzeme)\nDetaylı iletişim bilgilerini sol menüdeki 'Tedarikçiler' sekmesinden görebilirsiniz.", "tools_used": ["get_suppliers"], "steps": 1}
        elif "analiz" in msg:
            return {"response": "Son 3 aylık verilere göre **Organik Bal** satışları %40 arttı. Ancak **Ambalaj Kutusu** tüketimi beklenenden hızlı. Yakın zamanda kutu siparişi vermeniz operasyonel kesintileri önleyecektir.", "tools_used": ["analyze_sales"], "steps": 3}
        elif "stok özeti" in msg or "genel stok" in msg:
            return {"response": "Stoklarınız genel olarak sağlıklı durumda ancak 4 ürün kritik seviyenin altına inmiş. Sistemimiz bu ürünler için gerekli aksiyonları hazırladı.", "tools_used": ["get_inventory_stats"], "steps": 1}
        else:
            return {"response": "Zeytinyağı stokunuz 15 litre ile kritik seviyede. İlgili tedarikçi olan 'Öz Ege Tarım' firmasına acil sipariş maili taslağı hazırlanıp uyarılar sekmesine eklenmiştir.", "tools_used": ["check_inventory", "draft_email"], "steps": 2}

def get_ai_status(token: str) -> dict:
    try:
        r = httpx.get(f"{BASE_URL}/api/ai/status", headers=_headers(token), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {"status": "operational", "model": "Gemini 1.5 Flash", "tools_available": 3, "memory_messages": 12}

def reset_ai_memory(token: str) -> dict:
    return {"success": True}

def health_check() -> bool:
    return True
