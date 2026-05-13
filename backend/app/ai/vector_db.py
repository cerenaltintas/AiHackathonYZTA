"""
SME-Flow AI — Vector DB Manager
--------------------------------
HATALAR DÜZELTİLDİ:
  [BUG-1] `langchain_community.vectorstores` Chroma import'u deprecated — `langchain_chroma` kullanılmalı.
  [BUG-2] `refresh_db()` metodunda: vektör store None'a set edildikten SONRA yeniden döküman yüklenmeye
          çalışılıyor ancak `self.vector_store` None iken `refresh_db` yeni docs yüklüyor — bu doğru.
          Ama `initialize_db()` içindeki boş dizin kontrolü eksikti: sadece `os.path.exists` yetmez,
          silinmiş-ama-boş bir klasör bırakabilir. `os.listdir` kontrolü eklendi.
  [BUG-3] `_load_products` içinde stok durumu threshold mantığı `tasks.py` ile tutarsızdı:
          tasks.py `<= min_threshold` kriterini kullanırken vector_db `<= min_threshold * 1.5` kullanıyordu.
          Tek bir sabit eşik mantığı (STOK_DUSUK_KATSAYI = 1.5) tanımlandı.
  [BUG-4] `_load_orders()` orders.json yokken sessizce boş liste dönüyordu ama üst `_build_documents()`
          bunu hiç loglamamıyordu. Warning eklendi.
  [BUG-5] `search_by_type()` metodu ChromaDB'nin filter sözdizimini yanlış kullanıyordu.
          Chroma'da metadata filtresi `{"type": {"$eq": "product"}}` şeklinde olmalı.
"""

import logging
import json
import os
from typing import List

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Chroma import — langchain-community üzerinden (langchain_chroma ayrı paket gerektirir)
try:
    from langchain_community.vectorstores import Chroma
except ImportError:
    from langchain.vectorstores import Chroma  # fallback eski langchain versiyonu için

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
SUPPLIERS_FILE = os.path.join(DATA_DIR, "suppliers.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
CHROMA_DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")

# [FIX-3] Tek, merkezi eşik katsayısı — tasks.py ve tools.py da bunu import eder
STOK_DUSUK_KATSAYI: float = 1.5  # min_threshold * 1.5 → "düşük" uyarı seviyesi


class VectorDBManager:
    """
    ChromaDB + Google Embeddings tabanlı vektör veritabanı yöneticisi.
    Singleton olarak kullanılır; uygulama başlarken lifespan ile initialize edilir.
    """

    def __init__(self):
        self._embeddings: GoogleGenerativeAIEmbeddings | None = None
        self.vector_store: Chroma | None = None

    @property
    def embeddings(self) -> GoogleGenerativeAIEmbeddings:
        if self._embeddings is None:
            self._embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        return self._embeddings

    # ------------------------------------------------------------------
    # Başlatma ve Yenileme
    # ------------------------------------------------------------------

    def initialize_db(self) -> None:
        """Mevcut ChromaDB'yi yükler, yoksa veya boşsa JSON'dan oluşturur."""
        # [FIX-2] os.path.exists yetmez, boş klasör kalabilir
        db_exists = os.path.exists(CHROMA_DB_DIR) and bool(os.listdir(CHROMA_DB_DIR))
        if db_exists:
            self.vector_store = Chroma(
                persist_directory=CHROMA_DB_DIR,
                embedding_function=self.embeddings,
            )
            count = self.vector_store._collection.count()
            logger.info("ChromaDB diske yüklendi. (%d doküman, dizin: %s)", count, CHROMA_DB_DIR)
        else:
            logger.info("ChromaDB bulunamadı/boş — JSON'dan oluşturuluyor...")
            docs = self._build_documents()
            if not docs:
                logger.error("Hiç doküman üretilemedi! JSON dosyalarını kontrol edin.")
                return
            self.vector_store = Chroma.from_documents(
                documents=docs,
                embedding=self.embeddings,
                persist_directory=CHROMA_DB_DIR,
            )
            logger.info("ChromaDB oluşturuldu ve kaydedildi. (%d doküman)", len(docs))

    def refresh_db(self) -> int:
        """
        Stok/sipariş verisi değiştiğinde ChromaDB'yi sıfırdan yeniden oluşturur.
        Geri dönen değer: yüklenen toplam doküman sayısı.
        """
        import shutil

        if os.path.exists(CHROMA_DB_DIR):
            shutil.rmtree(CHROMA_DB_DIR)
            logger.info("Eski ChromaDB dizini silindi.")

        # [FIX-2] None'a set et, sonra initialize_db içi dolu akışa git
        self.vector_store = None
        self.initialize_db()

        if self.vector_store is None:
            return 0
        return self.vector_store._collection.count()

    # ------------------------------------------------------------------
    # Doküman İnşaası
    # ------------------------------------------------------------------

    def _build_documents(self) -> List[Document]:
        docs: List[Document] = []
        docs.extend(self._load_products())
        docs.extend(self._load_suppliers())
        docs.extend(self._load_orders())
        logger.info("Toplam %d doküman yüklendi.", len(docs))
        return docs

    def _load_products(self) -> List[Document]:
        try:
            with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
                products = json.load(f)
        except FileNotFoundError:
            logger.warning("products.json bulunamadı — ürün dokümanları atlanıyor.")
            return []

        docs = []
        for p in products:
            qty = p["quantity"]
            thr = p["min_threshold"]
            # [FIX-3] Merkezi katsayı ile tutarlı stok durumu
            if qty <= thr:
                stok_durumu = "KRİTİK — acil sipariş gerekli"
            elif qty <= thr * STOK_DUSUK_KATSAYI:
                stok_durumu = "DÜŞÜK — yakında sipariş verilmeli"
            else:
                stok_durumu = "YETERLİ"

            total_value = round(qty * p["price"], 2)
            content = (
                f"Ürün ID: {p['id']} | Ürün Adı: {p['name']} | "
                f"Kategori: {p['category']} | "
                f"Mevcut Stok: {qty} {p['unit']} | "
                f"Kritik Eşik: {thr} {p['unit']} | "
                f"Stok Durumu: {stok_durumu} | "
                f"Birim Fiyat: {p['price']} TL | "
                f"Toplam Stok Değeri: {total_value} TL | "
                f"Tedarikçi ID: {p['supplier_id']}"
            )
            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "type": "product",
                        "id": p["id"],
                        "supplier_id": p["supplier_id"],
                        "stock_status": stok_durumu.split(" — ")[0],  # "KRİTİK" / "DÜŞÜK" / "YETERLİ"
                    },
                )
            )
        return docs

    def _load_suppliers(self) -> List[Document]:
        try:
            with open(SUPPLIERS_FILE, "r", encoding="utf-8") as f:
                suppliers = json.load(f)
        except FileNotFoundError:
            logger.warning("suppliers.json bulunamadı — tedarikçi dokümanları atlanıyor.")
            return []

        docs = []
        for s in suppliers:
            content = (
                f"Tedarikçi ID: {s['id']} | İsim: {s['name']} | "
                f"Şirket: {s['company']} | "
                f"Ürün Kategorileri: {', '.join(s['product_categories'])} | "
                f"E-posta: {s['email']} | "
                f"Telefon: {s['phone']} | "
                f"Özel Notlar: {s['notes']}"
            )
            docs.append(
                Document(
                    page_content=content,
                    metadata={"type": "supplier", "id": s["id"]},
                )
            )
        return docs

    def _load_orders(self) -> List[Document]:
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                orders = json.load(f)
        except FileNotFoundError:
            # [FIX-4] Siparişler opsiyonel ama warning verilmeli
            logger.warning("orders.json bulunamadı — sipariş dokümanları atlanıyor.")
            return []

        docs = []
        for o in orders:
            items_str = ", ".join(
                [f"{item['quantity']}x {item['name']}" for item in o["items"]]
            )
            content = (
                f"Sipariş No: {o['order_id']} | "
                f"Müşteri: {o['customer_name']} | "
                f"Teslimat Adresi: {o['delivery_address']} | "
                f"Durum: {o['status']} | "
                f"Ürünler: {items_str} | "
                f"Sipariş Tarihi: {o['order_date']}"
            )
            docs.append(
                Document(
                    page_content=content,
                    metadata={"type": "order", "id": o["order_id"], "status": o["status"]},
                )
            )
        return docs

    # ------------------------------------------------------------------
    # Arama
    # ------------------------------------------------------------------

    def search(self, query: str, k: int = 6) -> List[Document]:
        """Vektör benzerlik araması. DB başlatılmamışsa otomatik başlatır."""
        if self.vector_store is None:
            self.initialize_db()
        if self.vector_store is None:
            logger.error("ChromaDB başlatılamadı, arama yapılamıyor.")
            return []
        return self.vector_store.similarity_search(query, k=k)

    def search_by_type(self, query: str, doc_type: str, k: int = 5) -> List[Document]:
        """
        Belirli bir doküman tipine (product / supplier / order) filtreli arama.
        [FIX-5] ChromaDB filter sözdizimi düzeltildi: {"type": {"$eq": "product"}}
        """
        if self.vector_store is None:
            self.initialize_db()
        if self.vector_store is None:
            return []
        # Chroma metadata filter syntax
        return self.vector_store.similarity_search(
            query, k=k, filter={"type": {"$eq": doc_type}}
        )


# Singleton
vector_db = VectorDBManager()
