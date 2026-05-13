import logging
import uuid
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from .tools import sme_tools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen **"SME-Flow AI"** adlı tam otonom KOBİ işletme asistanısın.
İşletme sahibi adına stok, sipariş, tedarikçi ve teslimat süreçlerini yönetiyorsun.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 MİMARİ KAPASİTELERİN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• **RAG**: `search_inventory_and_suppliers` ile ChromaDB'den anlam bazlı arama.
• **Tool Calling**: Hangi aracı çağıracağını SEN karar verirsin. Asla tahminde bulunma.
• **Memory**: Geçmiş mesajları hatırlarsın. Onay verildiğinde işleme devam et.
• **Proaktif Davranış**: Kritik durumları fark edip bildirebilirsin.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  MUTLAK KURALLAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Araç olmadan asla veri üretme (halüsinasyon = yasak).
2. Mail gönder denmeden önce taslağı sun ve onay iste.
3. Cevapların **Türkçe**, **markdown formatında**, emojilerle **profesyonel** olsun.
"""


class SMEAgent:
    """
    SME-Flow'un merkezi AI ajanı.
    Gemini 1.5 Flash + LangGraph + MemorySaver kullanır.
    """

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            temperature=0.05,
            max_output_tokens=2048,
        )

        self.memory = MemorySaver()
        self.thread_id = str(uuid.uuid4())
        
        self.agent = create_react_agent(
            self.llm,
            tools=sme_tools,
            checkpointer=self.memory,
            prompt=SYSTEM_PROMPT
        )

    def ask(self, question: str) -> dict:
        """
        Kullanıcı mesajını işler ve yanıt döner.
        """
        config = {"configurable": {"thread_id": self.thread_id}}
        try:
            result = self.agent.invoke(
                {"messages": [("user", question)]},
                config=config
            )
            
            # Yanıtlar içindeki son AIMessage'ı al
            final_message = result["messages"][-1].content
            
            # Gemini bazen string yerine list of dict dönebiliyor
            if isinstance(final_message, list):
                final_message = "".join([m.get("text", "") if isinstance(m, dict) else str(m) for m in final_message])
            
            # Tool çağrılarını takip et
            tools_used = []
            steps = 0
            for msg in result["messages"]:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    steps += 1
                    for tc in msg.tool_calls:
                        tools_used.append(tc["name"])

            return {
                "output": final_message,
                "tools_used": tools_used,
                "steps": steps,
            }

        except Exception as exc:
            logger.error("Ajan hatası: %s", str(exc), exc_info=True)
            return {
                "output": (
                    "❌ **Sistem Hatası:** Ajan işlem sırasında beklenmeyen bir hatayla karşılaştı.\n\n"
                    f"*Teknik Detay: {str(exc)[:300]}*\n\n"
                    "Lütfen sorunuzu farklı bir şekilde ifade ederek tekrar deneyin."
                ),
                "tools_used": [],
                "steps": 0,
            }

    def reset_memory(self) -> None:
        """Oturum hafızasını temizler (yeni bir thread_id ile)."""
        self.thread_id = str(uuid.uuid4())
        logger.info("Ajan hafızası temizlendi (yeni thread_id oluşturuldu).")


# ──────────────────────────────────────────────
# [FIX-18] Lazy Singleton — import sırasında crash önlenir
# ──────────────────────────────────────────────

_sme_agent_instance: Optional[SMEAgent] = None


def get_sme_agent() -> SMEAgent:
    """
    SMEAgent singleton'ını döner. İlk çağrıda oluşturulur (lazy init).
    Bu sayede GOOGLE_API_KEY henüz set edilmemişse import anında crash olmaz.
    """
    global _sme_agent_instance
    if _sme_agent_instance is None:
        logger.info("SMEAgent ilk kez oluşturuluyor (lazy init)...")
        _sme_agent_instance = SMEAgent()
    return _sme_agent_instance


# Backward compat — diğer modüller `from .agent import sme_agent` ile kullanıyor
class _AgentProxy:
    """Lazy singleton wrapper — attribute erişimini gerçek instance'a yönlendirir."""
    def __getattr__(self, name):
        return getattr(get_sme_agent(), name)

sme_agent = _AgentProxy()
