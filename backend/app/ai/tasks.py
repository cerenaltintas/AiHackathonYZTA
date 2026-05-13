"""
SME-Flow AI — Autonomous Background Tasks
------------------------------------------
HATALAR DÜZELTİLDİ:
  [BUG-19] `AutonomousTasks.__init__` her instance oluşturmada `ChatGoogleGenerativeAI`
           nesnesini hazırlıyor. Ancak API key yoksa uygulama başlarken crash yapar.
           Lazy init (ilk `check_and_trigger_alerts` çağrısında) kullanıldı.
  [BUG-20] `order_amount` formülü hatalıydı:
           `max(int(p["min_threshold"] * 2.5) - p["quantity"], 20)` formülü mantıklı
           ama `p["min_threshold"]` 0 olduğunda 0 * 2.5 = 0 olur ve `max(0 - qty, 20) = 20`
           döner. Ama bu durumda `quantity <= 0 == min_threshold` zaten kritik sayılmamalı.
           `inventory.py`'daki `get_stock_status` min_threshold==0 için HIGH döndürüyor,
           burası bu özel durumu handle etmeli. Guard eklendi.
  [BUG-21] `chain.invoke()` sonucu `ai_response.content` ile erişiliyor.
           Ama LangChain LCEL chain'inde PromptTemplate | LLM döndürdüğü zaman
           `.content` attribute'u AIMessage'da var. `str(ai_response.content)` gibi
           cast yapmak daha güvenli.
  [BUG-22] `refresh_vector_db()` metodunda `vector_db.refresh_db()` çağrısı yapılıyor
           ama `vector_db` bu dosyada import edilmemişti (önceki versiyonda eksikti).
           Import eklendi (şimdi zaten tasks.py başında import var — kontrol edildi).
  [BUG-23] `check_and_trigger_alerts` metodu büyük envanterlerde (50+ ürün)
           kritik her ürün için ayrı LLM çağrısı yapıyor — N+1 API call problemi.
           Demo MVP için acceptable ama log ile uyarıldı.
"""

import json
import logging
import os
from typing import Any, Optional

from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from .vector_db import vector_db

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
SUPPLIERS_FILE = os.path.join(DATA_DIR, "suppliers.json")


class AutonomousTasks:
    """
    LLM destekli otonom arka plan görevleri.
    Agent döngüsünden bağımsız, doğrudan endpoint çağrıları için kullanılır.
    """

    def __init__(self):
        # [FIX-19] LLM ve prompt lazy olarak initialize edilecek
        self._llm: Optional[ChatGoogleGenerativeAI] = None
        self._chain = None

    def _get_chain(self):
        """LLM zincirini lazy olarak oluşturur. İlk çağrıda API key kontrolü yapılır."""
        if self._chain is not None:
            return self._chain

        self._llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            temperature=0.2,
            max_output_tokens=1024,
        )
        draft_prompt = PromptTemplate.from_template(
            "Bir KOBİ işletmesi adına aşağıdaki ürün için tedarikçiye profesyonel, "
            "resmi ve kısa bir sipariş maili yaz. Konu başlığını da (Subject:) ekle.\n\n"
            "Tedarikçi: {supplier_name} ({supplier_company})\n"
            "E-posta: {supplier_email}\n"
            "Ürün: {product_name}\n"
            "Mevcut Stok: {current_stock} {unit}\n"
            "Kritik Eşik: {threshold} {unit}\n"
            "Talep Edilen Miktar: {order_amount} {unit}\n\n"
            "Kurallar:\n"
            "- Kibar ve kurumsal bir dil kullan\n"
            "- Aciliyeti belirt ama saldırgan olma\n"
            "- İmzayı 'SME-Flow Otonom Yönetim Sistemi' olarak at\n"
            "- Konu başlığı 'Subject: ...' formatında olsun"
        )
        self._chain = draft_prompt | self._llm
        return self._chain

    # ------------------------------------------------------------------
    # Kritik Stok Tarama + AI Mail Taslağı
    # ------------------------------------------------------------------

    def check_and_trigger_alerts(self) -> list[dict[str, Any]]:
        """
        Tüm ürünleri tarar. Kritik eşiğin altındaki her ürün için:
          1. Tedarikçi bilgisini bulur.
          2. Gemini ile profesyonel sipariş maili oluşturur.
          3. Sonuçları liste halinde döner.

        [BUG-23 NOTU] Kritik ürün başına 1 LLM çağrısı yapılır.
        Demo ortamında (az ürün) sorun değil; prod'da batch yapılmalı.
        """
        try:
            with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
                products = json.load(f)
            with open(SUPPLIERS_FILE, "r", encoding="utf-8") as f:
                suppliers = {s["id"]: s for s in json.load(f)}
        except FileNotFoundError as exc:
            logger.error("Veri dosyası bulunamadı: %s", exc)
            return []
        except json.JSONDecodeError as exc:
            logger.error("JSON parse hatası: %s", exc)
            return []

        try:
            with open(os.path.join(DATA_DIR, "sales_history.json"), "r", encoding="utf-8") as f:
                sales_history = json.load(f)
        except Exception:
            sales_history = []
            
        # Her ürün için geçmiş satışların aylık ortalamasını hesapla
        monthly_avg = {}
        for h in sales_history:
            for item in h.get("top_products", []):
                pid = item["product_id"]
                monthly_avg.setdefault(pid, []).append(item["sold_quantity"])
                
        for pid in monthly_avg:
            monthly_avg[pid] = int(sum(monthly_avg[pid]) / len(monthly_avg[pid]))

        chain = self._get_chain()
        alerts = []

        for p in products:
            # [FIX-20] min_threshold == 0 → stok kontrolü yapılamaz, atla
            if p["min_threshold"] == 0:
                continue
            if p["quantity"] > p["min_threshold"]:
                continue

            supplier = suppliers.get(p["supplier_id"])
            if not supplier:
                logger.warning("Tedarikçi bulunamadı: product_id=%s supplier_id=%s",
                               p["id"], p["supplier_id"])
                continue

            # Geçmiş satış verisine bakarak dinamik sipariş miktarı önerisi
            avg_sales = monthly_avg.get(p["id"], 0)
            if avg_sales > 0:
                # Gelecek 1 aylık ihtiyacı karşılayacak kadar sipariş
                order_amount = max(avg_sales - p["quantity"], 20)
            else:
                # Satış verisi yoksa fallback: eşiğin 2.5 katına tamamla
                order_amount = max(int(p["min_threshold"] * 2.5) - p["quantity"], 20)

            # [BUG-23] Her ürün için ayrı API çağrısı — MVP'de OK
            logger.info("Mail taslağı oluşturuluyor: %s", p["name"])
            try:
                ai_response = chain.invoke({
                    "supplier_name": supplier["name"],
                    "supplier_company": supplier["company"],
                    "supplier_email": supplier["email"],
                    "product_name": p["name"],
                    "current_stock": p["quantity"],
                    "threshold": p["min_threshold"],
                    "order_amount": order_amount,
                    "unit": p.get("unit", "adet"),
                })
                # [FIX-21] Güvenli content erişimi
                email_draft = str(getattr(ai_response, "content", ai_response))
            except Exception as exc:
                logger.error("Mail taslağı oluşturulamadı (product=%s): %s", p["id"], exc)
                email_draft = (
                    f"Subject: Acil Stok Sipariş Talebi — {p['name']}\n\n"
                    f"Sayın {supplier['name']} Yetkilisi,\n\n"
                    f"SME-Flow Otonom Yönetim Sistemimiz, \"{p['name']}\" ürününün "
                    f"depo stoğunun kritik seviyeye düştüğünü tespit etmiştir.\n\n"
                    f"Mevcut Stok: {p['quantity']} {p.get('unit', 'adet')}\n"
                    f"Kritik Eşik: {p['min_threshold']} {p.get('unit', 'adet')}\n"
                    f"Talep Edilen Miktar: {order_amount} {p.get('unit', 'adet')}\n\n"
                    f"Operasyonel sürekliliğimizi sağlamak adına yukarıda belirtilen "
                    f"miktarın en kısa sürede sevk edilmesini talep etmekteyiz.\n\n"
                    f"Saygılarımızla,\n"
                    f"SME-Flow Otonom İşletme Asistanı"
                )

            # Stok açığı yüzdesi (ne kadar kritik olduğu)
            gap_pct = round(
                ((p["min_threshold"] - p["quantity"]) / p["min_threshold"]) * 100, 1
            )

            alerts.append({
                "product_id": p["id"],
                "product_name": p["name"],
                "current_stock": p["quantity"],
                "min_threshold": p["min_threshold"],
                "stock_gap_percent": gap_pct,
                "suggested_order_amount": order_amount,
                "status": "kritik",
                "supplier_id": supplier["id"],
                "supplier_name": supplier["name"],
                "supplier_company": supplier["company"],
                "supplier_email": supplier["email"],
                "supplier_phone": supplier.get("phone", "-"),
                "email_draft": email_draft,
            })

        logger.info("Stok taraması tamamlandı: %d kritik ürün.", len(alerts))
        return alerts

    # ------------------------------------------------------------------
    # ChromaDB Yenileme
    # ------------------------------------------------------------------

    def refresh_vector_db(self) -> dict[str, Any]:
        """
        Stok güncellemelerinin ChromaDB'ye yansıması için vektör DB'yi yeniler.
        """
        try:
            doc_count = vector_db.refresh_db()
            logger.info("ChromaDB yenilendi: %d doküman.", doc_count)
            return {"success": True, "documents_indexed": doc_count}
        except Exception as exc:
            logger.error("ChromaDB yenileme hatası: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc)}


# Singleton
autonomous_tasks = AutonomousTasks()
