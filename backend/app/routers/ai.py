"""
SME-Flow AI — AI Router
--------------------------
HATALAR DÜZELTİLDİ:
  [BUG-24] `ChatResponse.tools_used` ve `steps` alanları agent'ın `ask()` metodunun
           dict döndürmesine bağlıydı. Ama `_AgentProxy` üzerinden `sme_agent.ask()`
           çağrısı dict döndürür — bu doğru. Ancak hata durumunda da dict dönmeli —
           bu agent.py'de zaten düzeltildi.
  [BUG-25] `RefreshDBResponse` şemasında `int | None` Python 3.10+ sözdizimi
           ama `pydantic` v1 kullanan ortamlarda hata verir.
           `Optional[int]` kullanıldı — her versiyonla uyumlu.
  [BUG-26] `ai_status` endpoint'i `sme_agent.executor.tools` üzerinden araç sayısını
           alıyordu. `_AgentProxy` wrapper üzerinden bu attribute erişimi çalışır
           ama `executor` None olabilir. `len(sme_tools)` sabit liste kullanıldı.
  [BUG-27] `memory_messages` hesaplamasında `sme_agent.memory.chat_memory.messages`
           `_AgentProxy` wrapper'dan geçerek None dönebilir. Try-except eklendi.
  [BUG-28] Router'da `from typing import Any` import edilmiş ama kullanılmıyordu. Temizlendi.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.ai.agent import sme_agent
from app.ai.tasks import autonomous_tasks
from app.ai.tools import sme_tools
from app.core.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ──────────────────────────────────────────────
# Şemalar
# ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Kullanıcı mesajı")

class ChatResponse(BaseModel):
    response: str
    tools_used: List[str] = Field(default_factory=list, description="Bu turda çağrılan araçlar")
    steps: int = Field(default=0, description="Ajan kaç adım aldı")

class AlertItem(BaseModel):
    product_id: str
    product_name: str
    current_stock: int
    min_threshold: int
    stock_gap_percent: float
    suggested_order_amount: int
    status: str
    supplier_id: str
    supplier_name: str
    supplier_company: str
    supplier_email: str
    supplier_phone: str
    email_draft: str

class RefreshDBResponse(BaseModel):
    success: bool
    # [FIX-25] Optional[int] — Python 3.9 uyumlu
    documents_indexed: Optional[int] = None
    error: Optional[str] = None

class AIStatusResponse(BaseModel):
    status: str
    model: str
    tools_available: int
    memory_messages: int


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse, summary="Otonom Ajan ile Sohbet")
async def chat_with_agent(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Kullanıcının mesajını SME-Flow AI ajanına iletir.

    Ajan soruyu analiz eder, gerekli araçları (tools) otomatik seçer,
    ChromaDB RAG araması + LLM yanıt üretimini birleştirir ve
    sohbet geçmişini (memory) kullanarak bağlamsal yanıt üretir.

    Response'daki `tools_used` alanı ajanın bu turda hangi araçları
    çağırdığını gösterir — demo ve debug için kullanışlıdır.
    """
    user_id = current_user.get("sub", "unknown")
    logger.info("Chat isteği: user=%s, message_len=%d", user_id, len(request.message))

    try:
        result = sme_agent.ask(request.message)
        return ChatResponse(
            response=result.get("output", ""),
            tools_used=result.get("tools_used", []),
            steps=result.get("steps", 0),
        )
    except Exception as exc:
        logger.error("Chat endpoint hatası: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Yapay zeka servisi hatası: {exc}")


@router.get("/alerts", response_model=List[AlertItem], summary="Proaktif Stok Uyarıları")
async def get_proactive_alerts(
    current_user: dict = Depends(get_current_user),
):
    """
    Tüm stokları otonom olarak tarar. Kritik eşiğin altındaki ürünler için stok açığı yüzdesi,
    önerilen sipariş miktarı ve Gemini ile hazırlanmış profesyonel mail taslağı döner.

    Frontend bu endpoint'i periyodik polling ile kullanarak kullanıcıya canlı bildirim gösterebilir.
    """
    user_id = current_user.get("sub", "unknown")
    logger.info("Proaktif uyarı taraması: user=%s", user_id)
    try:
        alerts = autonomous_tasks.check_and_trigger_alerts()
        return alerts
    except Exception as exc:
        logger.error("Uyarı endpoint hatası: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Otonom tarama hatası: {exc}")


@router.post("/reset-memory", summary="Ajan Hafızasını Temizle")
async def reset_agent_memory(
    current_user: dict = Depends(get_current_user),
):
    """
    Oturum boyunca biriken sohbet hafızasını temizler.
    Yeni bir konuşma başlatmak veya context kirliliğini önlemek için kullanılır.
    """
    sme_agent.reset_memory()
    logger.info("Ajan hafızası temizlendi: user=%s", current_user.get("sub"))
    return {"success": True, "message": "Sohbet hafızası başarıyla temizlendi."}


@router.post("/refresh-db", response_model=RefreshDBResponse, summary="ChromaDB Yenile")
async def refresh_vector_database(
    current_user: dict = Depends(get_current_user),
):
    """
    Stok verileri güncellendiğinde ChromaDB'yi yeniden oluşturur.
    Böylece RAG aramaları her zaman güncel veriye erişir.
    """
    logger.info("ChromaDB yenileme: user=%s", current_user.get("sub"))
    result = autonomous_tasks.refresh_vector_db()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Bilinmeyen hata"))
    return RefreshDBResponse(
        success=True,
        documents_indexed=result.get("documents_indexed"),
    )


@router.get("/status", response_model=AIStatusResponse, summary="AI Servis Durumu")
async def ai_status(current_user: dict = Depends(get_current_user)):
    """
    AI servisinin çalışma durumunu, aktif model adını ve hafıza boyutunu döner.
    """
    # [FIX-26] Sabit liste uzunluğu — executor'a erişim gerektirmiyor
    tools_count = len(sme_tools)

    # [FIX-27] Güvenli memory erişimi — LangGraph MemorySaver yapısına uyumlu
    try:
        config = {"configurable": {"thread_id": sme_agent.thread_id}}
        state = sme_agent.agent.get_state(config)
        memory_len = len(state.values.get("messages", [])) if state.values else 0
    except Exception:
        memory_len = 0

    return AIStatusResponse(
        status="operational",
        model="gemini-flash-latest",
        tools_available=tools_count,
        memory_messages=memory_len,
    )
