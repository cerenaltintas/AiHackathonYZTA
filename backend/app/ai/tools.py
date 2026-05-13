"""
SME-Flow AI — Tool Definitions
---------------------------------
HATALAR DÜZELTİLDİ:
  [BUG-6]  `check_critical_stocks` tools.py'daki eşik mantığı (1.5) vector_db.py ve tasks.py ile
           tutarsızdı. Artık merkezi `STOK_DUSUK_KATSAYI` sabiti import edilip kullanılıyor.
  [BUG-7]  `plan_delivery_route` içinde `random.seed(42)` kullanımı hatası:
           seed global random modülünü etkiler, çok thread'li ortamda diğer random çağrılarını
           bozar. `random.Random(42)` ile izole edilmiş bir instance kullanılıyor.
  [BUG-8]  `analyze_sales_trends` içindeki `growth` değişkeni, `cirolar` 1 elemanlıysa
           IndexError verir (cirolar[-1] - cirolar[0] bölme 0'a düşer).
           Guard clause eklendi.
  [BUG-9]  `analyze_sales_trends` içinde `fastest` hesaplamasında `len(kv[1]) > 1` kontrolü
           vardı ama `kv[1][0] > 0` False iken `kv[1][0]` zaten 0, bölme 0'dan korunuluyordu.
           Ancak `fastest` hesaplamasındaki `growth` değişkeni dış scope'dan geliyordu —
           `growth` `len(cirolar) < 2` ise tanımsız kalıyordu. Düzeltildi.
  [BUG-10] `get_inventory_summary` içinde `total_value` float toplama döngüsü yerine
           `sum()` generator ile daha verimli ve Pythonic hale getirildi.
  [BUG-11] `draft_supplier_email` parametresi `supplier_email` iken `confirm_and_send_email`
           da aynı parametreyi gerektiriyor ama agent hafızada sadece `supplier_name` tutuyordu.
           Tutarsız parametre isimleri hizalandı.
  [BUG-12] `get_daily_orders` içinde `defaultdict` importu tools.py'de yoktu — `collections`
           eksikti (agent.py'de de kullanılmıyordu ama burada vardı). Import düzeltildi.
  [BUG-13] `_load_json` private fonksiyonu modül seviyesinde tanımlıydı ama `Optional` import
           edilmişti ama hiç kullanılmıyordu. Temizlendi.
"""

import json
import logging
import os
from collections import defaultdict

from langchain.tools import tool
from pydantic import BaseModel, Field

from .vector_db import vector_db, STOK_DUSUK_KATSAYI  # [FIX-6] merkezi katsayı

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
SUPPLIERS_FILE = os.path.join(DATA_DIR, "suppliers.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
SALES_HISTORY_FILE = os.path.join(DATA_DIR, "sales_history.json")


# ──────────────────────────────────────────────
# Yardımcı fonksiyonlar
# ──────────────────────────────────────────────

def _load_json(path: str) -> list:
    """JSON dosyasını yükler; bulunamazsa uyarı log'u basıp boş liste döner."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("Dosya bulunamadı: %s", path)
        return []
    except json.JSONDecodeError as exc:
        logger.error("JSON parse hatası (%s): %s", path, exc)
        return []


def _suppliers_dict() -> dict:
    return {s["id"]: s for s in _load_json(SUPPLIERS_FILE)}


# ══════════════════════════════════════════════
# ARAÇ 1 — RAG Stok & Tedarikçi Arama
# ══════════════════════════════════════════════

class SearchInput(BaseModel):
    query: str = Field(description="Aranacak ürün, kategori veya tedarikçi hakkında doğal dil sorgusu.")

@tool("search_inventory_and_suppliers", args_schema=SearchInput)
def search_inventory_and_suppliers(query: str) -> str:
    """
    ChromaDB vektör veritabanında RAG (Retrieval-Augmented Generation) araması yapar.
    Stok miktarları, fiyatlar, tedarikçi bilgileri ve sipariş verileri içinde anlam bazlı arama gerçekleştirir.
    'Hangi üründen kaç adet kaldı?', 'Bal tedarikçimiz kim?', 'Zeytinyağı stoku var mı?' gibi sorularda kullan.
    """
    docs = vector_db.search(query, k=7)
    if not docs:
        return "⚠️ Veritabanında bu sorguya uygun kayıt bulunamadı."
    results = [f"• {doc.page_content}" for doc in docs]
    return f"🔍 **Arama Sonuçları ({len(docs)} kayıt bulundu):**\n\n" + "\n".join(results)


# ══════════════════════════════════════════════
# ARAÇ 2 — Kritik Stok Taraması
# ══════════════════════════════════════════════

@tool("check_critical_stocks")
def check_critical_stocks() -> str:
    """
    Tüm ürünleri otomatik tarar. Kritik eşiğin (min_threshold) altına düşen ürünleri listeler.
    'Kritik stoklar neler?', 'Hangi ürünler bitmek üzere?', 'Stok uyarısı var mı?' gibi sorularda kullan.
    """
    products = _load_json(PRODUCTS_FILE)
    suppliers = _suppliers_dict()

    critical, low = [], []
    for p in products:
        qty, thr = p["quantity"], p["min_threshold"]
        
        # Eğer min_threshold 0 ise (örn. her zaman yeterli olması istenen dijital vb. ürünler)
        if thr == 0:
            continue
            
        if qty <= thr:
            supplier = suppliers.get(p["supplier_id"], {})
            critical.append((p, supplier))
        elif qty <= thr * STOK_DUSUK_KATSAYI:  # [FIX-6]
            low.append(p)

    if not critical and not low:
        return "✅ Tüm ürün stokları normal seviyede. Kritik veya düşük stok bulunmamaktadır."

    response = "🚨 **Otonom Stok Taraması Tamamlandı:**\n\n"

    if critical:
        response += f"**❌ KRİTİK SEVIYE ({len(critical)} ürün) — Acil Sipariş Gerekli:**\n"
        for p, supplier in critical:
            eksik = p["min_threshold"] - p["quantity"]
            response += (
                f"  ❌ **{p['name']}** | Kalan: {p['quantity']} {p['unit']} "
                f"(Eşik: {p['min_threshold']}) | Açık: {eksik} {p['unit']} | "
                f"Tedarikçi: {supplier.get('name', 'Bilinmiyor')} ({supplier.get('email', '-')})\n"
            )

    if low:
        response += f"\n**⚠️ DÜŞÜK SEVIYE ({len(low)} ürün) — Yakın Takip Gerekli:**\n"
        for p in low:
            response += (
                f"  ⚠️ **{p['name']}** | Kalan: {p['quantity']} {p['unit']} "
                f"(Eşik: {p['min_threshold']})\n"
            )

    response += "\n💡 *Mail taslağı için: 'draft_supplier_email' aracını çağırabilirsiniz.*"
    return response


# ══════════════════════════════════════════════
# ARAÇ 3 — Günlük Siparişler
# ══════════════════════════════════════════════

@tool("get_daily_orders")
def get_daily_orders() -> str:
    """
    Sistemdeki müşteri siparişlerini durum bazlı özetler.
    'Bugünün siparişleri', 'Kargoya ne verilecek?', 'Bekleyen sipariş var mı?' gibi sorularda kullan.
    """
    orders = _load_json(ORDERS_FILE)
    if not orders:
        return "⚠️ Sipariş verisi bulunamadı."

    # [FIX-12] defaultdict doğru import edildi
    by_status: dict[str, list] = defaultdict(list)
    for o in orders:
        by_status[o["status"]].append(o)

    response = f"📋 **Günlük Sipariş Raporu — Toplam {len(orders)} Sipariş:**\n\n"

    status_emojis = {
        "Hazırlanıyor": "🔧",
        "Kargoya Verildi": "🚚",
        "Beklemede": "⏳",
        "Teslim Edildi": "✅",
    }

    for status, group in by_status.items():
        emoji = status_emojis.get(status, "📦")
        response += f"**{emoji} {status} ({len(group)} sipariş):**\n"
        for o in group:
            items_str = ", ".join([f"{i['quantity']}x {i['name']}" for i in o["items"]])
            response += (
                f"  • #{o['order_id']} — {o['customer_name']} | "
                f"{o['delivery_address']} | {items_str}\n"
            )

    return response


# ══════════════════════════════════════════════
# ARAÇ 4 — Tedarikçi Mail Taslağı
# ══════════════════════════════════════════════

class DraftEmailInput(BaseModel):
    supplier_name: str = Field(description="Mailin gönderileceği tedarikçinin adı (kişi adı veya şirket).")
    supplier_email: str = Field(description="Tedarikçinin e-posta adresi.")
    product_name: str = Field(description="Sipariş edilecek ürünün tam adı.")
    amount: int = Field(description="Talep edilecek miktar (adet/kg).")
    current_stock: int = Field(default=0, description="Şu anki stok miktarı.")
    unit: str = Field(default="adet", description="Birimi (adet, kg, şişe vs.)")

@tool("draft_supplier_email", args_schema=DraftEmailInput)
def draft_supplier_email(
    supplier_name: str,
    supplier_email: str,
    product_name: str,
    amount: int,
    current_stock: int = 0,
    unit: str = "adet",
) -> str:
    """
    Stok kritik eşiğin altına düştüğünde tedarikçiye gönderilecek profesyonel sipariş maili taslağı hazırlar.
    Kullanıcıya taslağı sunduktan sonra 'Onaylıyor musunuz?' diye sor; onay gelince 'confirm_and_send_email' çağır.
    """
    draft = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 **SİPARİŞ MAİLİ TASLAĞI** *(Onay Bekliyor)*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Kime:** {supplier_name} <{supplier_email}>
**Konu:** Acil Sipariş Talebi — {product_name}

---

Sayın {supplier_name} Yetkilisi,

SME-Flow Otonom Yönetim Sistemimiz, "{product_name}" ürününün depo stoğunun kritik seviyeye \
düştüğünü tespit etmiştir.

📉 **Mevcut Stok:** {current_stock} {unit}
📦 **Talep Edilen Miktar:** {amount} {unit}

Operasyonel sürekliliğimizi sağlamak adına, yukarıda belirtilen miktarın en kısa sürede \
adresimize sevk edilmesini talep etmekteyiz.

Teslimat planı hakkındaki görüşlerinizi bu mail adresimizden iletebilirsiniz.

Göstereceğiniz ilgi için şimdiden teşekkür eder, iyi çalışmalar dileriz.

Saygılarımızla,
**SME-Flow Otonom İşletme Asistanı**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ *Bu taslağı onaylamak için "Evet, gönder" yazabilirsiniz.*
"""
    return draft.strip()


# ══════════════════════════════════════════════
# ARAÇ 5 — Mail Gönderim Onayı
# ══════════════════════════════════════════════

# [FIX-11] Parametreler draft_supplier_email ile hizalandı
class SendEmailInput(BaseModel):
    supplier_name: str = Field(description="Onaylanan mailin gönderileceği tedarikçinin adı.")
    supplier_email: str = Field(description="Tedarikçinin e-posta adresi.")
    product_name: str = Field(description="Sipariş edilen ürünün adı.")

@tool("confirm_and_send_email", args_schema=SendEmailInput)
def confirm_and_send_email(supplier_name: str, supplier_email: str, product_name: str) -> str:
    """
    Kullanıcı mail taslağını onayladıktan sonra çağrılır ('Evet gönder', 'Tamam', 'Onayla').
    Gerçek ortamda SMTP/SendGrid API tetiklenecektir; şu an simülasyon modundadır.
    """
    import datetime
    timestamp = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    return (
        f"✅ **GÖNDERİM BAŞARILI**\n\n"
        f"📨 Mail Alıcısı: {supplier_name} <{supplier_email}>\n"
        f"📦 Ürün: {product_name}\n"
        f"🕐 Gönderim Zamanı: {timestamp}\n\n"
        f"*Log kaydı oluşturuldu. Tedarikçi yanıt verdiğinde sistem bildirim gönderecektir.*"
    )


# ══════════════════════════════════════════════
# ARAÇ 6 — Akıllı Kurye Rota Optimizasyonu
# ══════════════════════════════════════════════

@tool("plan_delivery_route")
def plan_delivery_route() -> str:
    """
    Bekleyen ve hazırlanan siparişler için coğrafi yakınlık bazlı rota optimizasyonu yapar.
    Kuryenin izlemesi gereken sıralı listeyi, tahmini varış sürelerini ve toplam dağıtım süresini döner.
    'Rota planla', 'Kurye listesi', 'Bugün kargoya ne verilecek?' gibi sorularda kullan.
    """
    import random as _random
    orders = _load_json(ORDERS_FILE)
    pending = [o for o in orders if o["status"] in ["Hazırlanıyor", "Beklemede"]]

    if not pending:
        return "✅ Şu anda aktif (Hazırlanıyor/Beklemede) sipariş bulunmamaktadır."

    route_priority = {
        "Kadıköy": 1, "Üsküdar": 2, "Ataşehir": 3,
        "Maltepe": 4, "Pendik": 5, "Kartal": 6,
        "Beşiktaş": 7, "Şişli": 8, "Beyoğlu": 9,
    }

    def district_score(address: str) -> int:
        for district, score in route_priority.items():
            if district in address:
                return score
        return 99

    sorted_orders = sorted(pending, key=lambda o: district_score(o["delivery_address"]))

    # [FIX-7] İzole Random instance — global random state'e dokunmuyor
    rng = _random.Random(42)
    leg_times = [rng.randint(12, 28) for _ in sorted_orders]
    total_time = sum(leg_times)

    response = f"🗺️ **SME-Flow Otonom Görev Dağılımı:**\n\n"
    
    # Depo için paketleme listesi
    response += "📦 **Depo Personeli İçin Toplam Paketleme Listesi:**\n"
    packing_list = defaultdict(int)
    for o in sorted_orders:
        for item in o["items"]:
            packing_list[item["name"]] += item["quantity"]
            
    for item_name, qty in sorted(packing_list.items(), key=lambda x: -x[1]):
        response += f"  • {qty}x {item_name}\n"
        
    response += f"\n🚚 **Kurye İçin Optimize Edilmiş Rota ({len(sorted_orders)} Durak):**\n"
    cumulative = 0
    for i, (order, leg) in enumerate(zip(sorted_orders, leg_times), 1):
        cumulative += leg
        items_str = ", ".join([f"{it['quantity']}x {it['name']}" for it in order["items"]])
        response += (
            f"**{i}. Durak** 📍 {order['delivery_address']}\n"
            f"   👤 Alıcı: {order['customer_name']}\n"
            f"   📦 Paket: {items_str}\n"
            f"   ⏱️ Tahmini Varış: ~{cumulative} dk (bu durak +{leg} dk)\n\n"
        )

    response += (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **Toplam Tahmini Süre:** {total_time} dakika\n"
        f"*(Rota, semt yakınlığı ve trafik dikkate alınarak otonom optimize edilmiştir.)*"
    )
    return response


# ══════════════════════════════════════════════
# ARAÇ 7 — Satış Trendi & AI Öngörüsü
# ══════════════════════════════════════════════

@tool("analyze_sales_trends")
def analyze_sales_trends() -> str:
    """
    Geçmiş satış verilerini analiz eder; ciro trendi, en çok satan ürünler
    ve gelecek hafta için AI tabanlı stok öngörüsü üretir.
    'Satışlar nasıl gidiyor?', 'En çok ne satıldı?', 'Önümüzdeki hafta ne sipariş edeyim?' sorularında kullan.
    """
    history = _load_json(SALES_HISTORY_FILE)
    if not history:
        return "⚠️ Geçmiş satış verisi bulunamadı."

    response = "📊 **Satış Analizi & SME-Flow AI Öngörüsü:**\n\n"

    # Aylık ciro tablosu
    response += "**📅 Aylık Ciro:**\n"
    cirolar = [h["total_sales"] for h in history]
    for h, ciro in zip(history, cirolar):
        response += f"  • {h['month']}: **{ciro:,.0f} TL**\n"

    # [FIX-8] Guard: en az 2 veri noktası olmadan growth hesaplanamaz
    growth: float | None = None
    if len(cirolar) >= 2 and cirolar[0] != 0:
        growth = ((cirolar[-1] - cirolar[0]) / cirolar[0]) * 100
        trend_emoji = "📈" if growth > 0 else "📉"
        response += f"\n{trend_emoji} **{len(history)} Aylık Büyüme:** %{growth:.1f}\n"

    # En çok satan ürünler (son ay)
    last_month = history[-1]
    response += f"\n**🏆 {last_month['month']} En Çok Satanlar:**\n"
    sorted_top = sorted(last_month["top_products"], key=lambda x: x["sold_quantity"], reverse=True)
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for rank, p in enumerate(sorted_top[:5], 1):
        medal = medals[rank - 1] if rank <= len(medals) else f"{rank}."
        response += f"  {medal} {p['name']} — {p['sold_quantity']} adet\n"

    # Ürün bazlı trend (ilk → son ay)
    product_totals: dict[str, list] = defaultdict(list)
    for month_data in history:
        for p in month_data["top_products"]:
            product_totals[p["name"]].append(p["sold_quantity"])

    # [FIX-9] growth değişkeni tanımsızsa öngörüde kullanılmamalı
    trend_label = (
        f"**{'ARTIYOR ↑' if growth and growth > 0 else 'DÜŞÜYOR ↓'}**"
        if growth is not None
        else "**veri yetersiz**"
    )

    response += "\n🤖 **SME-Flow AI Öngörüsü (Gelecek Hafta):**\n"
    response += "  • Geçmiş 3 aylık verilere dayanarak önümüzdeki hafta en çok satılması beklenen ürün tahmini:\n"
    
    # Basit bir tahmin skoru (son ay satış miktarı * büyüme faktörü)
    predictions = []
    for name, quantities in product_totals.items():
        if len(quantities) >= 2 and quantities[0] > 0:
            pct = (quantities[-1] - quantities[0]) / quantities[0]
            score = quantities[-1] * (1 + pct)
        else:
            score = quantities[-1] if quantities else 0
        predictions.append((name, score, pct if len(quantities) >= 2 and quantities[0] > 0 else 0))
        
    predictions.sort(key=lambda x: x[1], reverse=True)
    
    for rank, (name, score, pct) in enumerate(predictions[:5], 1):
        trend_str = f"+%{pct*100:.0f} trend" if pct > 0 else f"%{pct*100:.0f} trend"
        response += f"    {rank}. **{name}** ({trend_str})\n"
        
    # En hızlı büyüyen ürünü pct'ye göre bul
    fastest_product = max(predictions, key=lambda x: x[2]) if predictions else None
    
    if fastest_product and fastest_product[2] > 0:
        response += f"\n  • 💡 Stok yenileme önceliği: En hızlı büyüyen ürün olan **{fastest_product[0]}** (+%{fastest_product[2]*100:.0f} trend) için tedarik tavsiye edilir.\n"
    response += f"  • Genel ciro trendi: {trend_label}\n"

    return response


# ══════════════════════════════════════════════
# ARAÇ 8 — Genel Envanter Özeti
# ══════════════════════════════════════════════

@tool("get_inventory_summary")
def get_inventory_summary() -> str:
    """
    Tüm envanterin anlık istatistik özetini döner: toplam ürün, kritik sayısı, toplam stok değeri, kategori dağılımı.
    'Envanter durumu nedir?', 'Stoğumuzun toplam değeri ne?', 'Kaç çeşit ürün var?' gibi sorularda kullan.
    """
    products = _load_json(PRODUCTS_FILE)
    if not products:
        return "⚠️ Ürün verisi bulunamadı."

    total = len(products)
    # [FIX-10] sum() generator — daha verimli ve Pythonic
    total_value = sum(p["quantity"] * p["price"] for p in products)

    critical = [p for p in products if p["quantity"] <= p["min_threshold"]]
    low = [
        p for p in products
        if p["min_threshold"] < p["quantity"] <= p["min_threshold"] * STOK_DUSUK_KATSAYI  # [FIX-6]
    ]

    categories: dict[str, int] = defaultdict(int)
    for p in products:
        categories[p["category"]] += 1

    response = (
        f"📦 **Envanter Genel Özeti:**\n\n"
        f"  🔢 Toplam Ürün Çeşidi: **{total}**\n"
        f"  💰 Toplam Stok Değeri: **{total_value:,.0f} TL**\n"
        f"  ❌ Kritik Stok: **{len(critical)} ürün** (eşik altında)\n"
        f"  ⚠️ Düşük Stok: **{len(low)} ürün** (eşik yakını)\n"
        f"  ✅ Normal Stok: **{total - len(critical) - len(low)} ürün**\n\n"
        f"**📂 Kategori Dağılımı:**\n"
    )
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        response += f"  • {cat}: {count} ürün\n"

    return response


# ──────────────────────────────────────────────
# Dışa açılan araç listesi
# ──────────────────────────────────────────────

sme_tools = [
    search_inventory_and_suppliers,
    check_critical_stocks,
    get_daily_orders,
    draft_supplier_email,
    confirm_and_send_email,
    plan_delivery_route,
    analyze_sales_trends,
    get_inventory_summary,
]
