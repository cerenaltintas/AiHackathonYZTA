"""
SME-Flow AI — FastAPI Uygulama Giriş Noktası
----------------------------------------------
Lifespan event ile başlangıçta ChromaDB otomatik başlatılır.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, inventory, suppliers, ai, orders

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama başladığında env değişkenlerini ayarla ve ChromaDB'yi hazırla."""
    import os
    from app.core.config import settings

    # [FIX-29] langchain-google-genai GOOGLE_API_KEY arar, config'de GEMINI_API_KEY var.
    # İkisi de .env'den okunabilsin diye her ikisini de set et.
    if settings.GEMINI_API_KEY and not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY
        logger.info("GOOGLE_API_KEY ortam değişkeni GEMINI_API_KEY'den ayarlandı.")

    logger.info("SME-Flow AI başlatılıyor — ChromaDB initialize ediliyor...")
    try:
        from app.ai.vector_db import vector_db
        vector_db.initialize_db()
        logger.info("ChromaDB başarıyla hazırlandı.")
    except Exception as exc:
        logger.error("ChromaDB başlatılamadı: %s", exc)
    yield
    logger.info("SME-Flow AI kapatılıyor.")



app = FastAPI(
    title="SME-Flow AI",
    description=(
        "Otonom KOBİ İşletme Asistanı API — Gemini 1.5 Flash + LangChain AgentExecutor + ChromaDB RAG. "
        "Stok takibi, tedarikçi yönetimi, kurye rota optimizasyonu ve satış analitiği."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,      prefix="/api/auth",      tags=["Kimlik Doğrulama"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Envanter"])
app.include_router(suppliers.router, prefix="/api/suppliers", tags=["Tedarikçiler"])
app.include_router(orders.router,    prefix="/api/orders",    tags=["Siparişler"])
app.include_router(ai.router,        prefix="/api/ai",        tags=["Yapay Zeka (Otonom Ajan)"])


@app.get("/", tags=["Sistem"])
def health_check():
    return {
        "status": "ok",
        "message": "SME-Flow AI API çalışıyor",
        "version": "1.0.0",
        "endpoints": [
            "/api/auth/token",
            "/api/inventory/",
            "/api/suppliers/",
            "/api/orders/",
            "/api/ai/chat",
            "/api/ai/alerts",
            "/api/ai/status",
        ],
    }
