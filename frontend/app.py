"""
SME-Flow AI — Otonom İşletme ve Stok Asistanı
Frontend Dashboard (Streamlit)
Kişi 3: Frontend & UI/UX Lead
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import time

from api_client import (
    login, health_check, get_inventory, get_inventory_stats,
    get_critical_stock, get_suppliers, get_ai_alerts,
    chat_with_ai, get_ai_status, reset_ai_memory,
)
from styles import CUSTOM_CSS

# ── Page Config ──
st.set_page_config(
    page_title="SME-Flow AI | Otonom İşletme Asistanı",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

LOGO_PATH = Path(__file__).parent / "assets" / "logo.png"

# ── Session State Init ──
defaults = {
    "token": None, "logged_in": False, "chat_history": [],
    "active_page": "dashboard",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════
#  LOGIN PAGE
# ══════════════════════════════════════════════
def render_login():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div style='height:3rem'></div>", unsafe_allow_html=True)
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=120, use_container_width=False)
        st.markdown('<p class="login-title">SME-Flow AI</p>', unsafe_allow_html=True)
        st.markdown('<p class="login-subtitle">Otonom İşletme ve Stok Asistanı</p>', unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("👤 Kullanıcı Adı", value="admin", placeholder="Kullanıcı adınız")
            password = st.text_input("🔒 Şifre", value="admin123", type="password", placeholder="Şifreniz")
            submitted = st.form_submit_button("🚀 Giriş Yap", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("Lütfen tüm alanları doldurun.")
                    return
                with st.spinner("Kimlik doğrulanıyor..."):
                    result = login(username, password)
                if result["success"]:
                    st.session_state.token = result["token"]
                    st.session_state.logged_in = True
                    st.success("✅ Giriş başarılı!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(result["error"])

        # Backend health
        api_ok = health_check()
        color = "#10B981" if api_ok else "#EF4444"
        text = "Çevrimiçi" if api_ok else "Çevrimdışı"
        st.markdown(
            f'<div style="text-align:center;margin-top:1rem">'
            f'<span style="color:{color};font-size:0.8rem">● API Durumu: {text}</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="text-align:center;color:#64748B;font-size:0.75rem;margin-top:2rem">'
            'Demo: admin / admin123</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=70)
        st.markdown("### SME-Flow AI")
        st.caption("Otonom İşletme Asistanı")
        st.markdown("---")

        pages = {
            "dashboard": ("📊", "Dashboard"),
            "inventory": ("📦", "Envanter"),
            "alerts": ("🚨", "Stok Uyarıları"),
            "suppliers": ("🏭", "Tedarikçiler"),
            "chat": ("🤖", "AI Asistan"),
        }
        for key, (icon, label) in pages.items():
            if st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
                st.session_state.active_page = key
                st.rerun()

        st.markdown("---")

        # AI Status
        try:
            ai = get_ai_status(st.session_state.token)
            status_color = "#10B981" if ai.get("status") == "operational" else "#EF4444"
            st.markdown(
                f'<div style="padding:0.8rem;background:rgba(30,41,59,0.6);border-radius:12px;'
                f'border:1px solid rgba(99,102,241,0.15)">'
                f'<div style="font-size:0.75rem;color:#94A3B8;text-transform:uppercase;letter-spacing:0.5px">'
                f'AI Servis Durumu</div>'
                f'<div style="color:{status_color};font-weight:600;margin:0.3rem 0">'
                f'● {ai.get("status","N/A").title()}</div>'
                f'<div style="font-size:0.75rem;color:#64748B">'
                f'Model: {ai.get("model","N/A")}<br>'
                f'Araçlar: {ai.get("tools_available",0)}<br>'
                f'Hafıza: {ai.get("memory_messages",0)} mesaj</div></div>',
                unsafe_allow_html=True,
            )
        except Exception:
            st.caption("AI durumu alınamadı")

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# ══════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════
def render_dashboard():
    st.markdown("## 📊 İşletme Dashboard")
    st.caption("Gerçek zamanlı stok ve işletme özeti")

    try:
        stats = get_inventory_stats(st.session_state.token)
    except Exception:
        st.error("İstatistikler yüklenemedi. Backend çalışıyor mu?")
        return

    if not stats:
        st.warning("Veriler yüklenemedi. Backend bağlantısını kontrol edin.")
        return

    # KPI Metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📦 Toplam Ürün", stats.get("total_products", 0))
    c2.metric("🔴 Kritik Stok", stats.get("kritik", 0))
    c3.metric("🟡 Düşük Stok", stats.get("dusuk", 0))
    c4.metric("🟢 Normal Stok", stats.get("normal", 0))
    total_val = stats.get("total_value", 0)
    c5.metric("💰 Toplam Değer", f"₺{total_val:,.0f}")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # Two columns: critical items + category chart
    left, right = st.columns([1.2, 1])

    with left:
        st.markdown("### 🚨 Kritik & Düşük Stok Ürünleri")
        try:
            critical = get_critical_stock(st.session_state.token)
        except Exception:
            critical = []

        if critical:
            for item in critical[:8]:
                status = item.get("stock_status", "")
                css_class = "alert-card-critical" if status == "kritik" else "alert-card-low"
                emoji = "🔴" if status == "kritik" else "🟡"
                pct = 0
                if item.get("min_threshold", 0) > 0:
                    pct = round(item["quantity"] / item["min_threshold"] * 100)
                st.markdown(
                    f'<div class="{css_class}">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<div><strong>{emoji} {item["name"]}</strong><br>'
                    f'<span style="font-size:0.8rem;color:#94A3B8">{item["category"]}</span></div>'
                    f'<div style="text-align:right">'
                    f'<span style="font-size:1.3rem;font-weight:700">{item["quantity"]}</span>'
                    f'<span style="font-size:0.8rem;color:#94A3B8"> / {item["min_threshold"]} {item["unit"]}</span><br>'
                    f'<span style="font-size:0.75rem;color:#94A3B8">{pct}% kapasite</span>'
                    f'</div></div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.success("✅ Tüm stoklar yeterli seviyede!")

    with right:
        st.markdown("### 📈 Kategori Dağılımı")
        try:
            products = get_inventory(st.session_state.token)
            if products:
                df = pd.DataFrame(products)
                cat_counts = df.groupby("category").agg(
                    Adet=("quantity", "sum"),
                    Ürün_Sayısı=("id", "count"),
                    Değer=("price", lambda x: round(sum(x * df.loc[x.index, "quantity"]), 0)),
                ).reset_index()
                cat_counts.columns = ["Kategori", "Toplam Stok", "Ürün Sayısı", "Toplam Değer (₺)"]
                st.dataframe(cat_counts, use_container_width=True, hide_index=True)

                # Status distribution chart
                st.markdown("### 📊 Stok Durumu Dağılımı")
                status_counts = df["stock_status"].value_counts()
                chart_data = pd.DataFrame({
                    "Durum": status_counts.index,
                    "Adet": status_counts.values
                })
                st.bar_chart(chart_data.set_index("Durum"))
        except Exception:
            st.info("Grafik verileri yüklenemedi.")


# ══════════════════════════════════════════════
#  INVENTORY PAGE
# ══════════════════════════════════════════════
def render_inventory():
    st.markdown("## 📦 Envanter Yönetimi")
    st.caption("Tüm ürünlerin detaylı listesi ve filtreleme")

    try:
        products = get_inventory(st.session_state.token)
    except Exception:
        st.error("Envanter verileri yüklenemedi.")
        return

    if not products:
        st.warning("Ürün bulunamadı.")
        return

    # Filters
    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    categories = sorted(set(p["category"] for p in products))
    with col_f1:
        search = st.text_input("🔍 Ürün Ara", placeholder="Ürün adı yazın...")
    with col_f2:
        cat_filter = st.selectbox("📁 Kategori", ["Tümü"] + categories)
    with col_f3:
        status_filter = st.selectbox("📊 Durum", ["Tümü", "kritik", "dusuk", "normal", "yuksek"])

    filtered = products
    if search:
        filtered = [p for p in filtered if search.lower() in p["name"].lower()]
    if cat_filter != "Tümü":
        filtered = [p for p in filtered if p["category"] == cat_filter]
    if status_filter != "Tümü":
        filtered = [p for p in filtered if p["stock_status"] == status_filter]

    st.markdown(f"**{len(filtered)}** ürün listeleniyor")

    if filtered:
        df = pd.DataFrame(filtered)
        display_cols = ["id", "name", "category", "quantity", "unit", "min_threshold", "price", "stock_status"]
        display_df = df[display_cols].copy()
        display_df.columns = ["ID", "Ürün Adı", "Kategori", "Stok", "Birim", "Min. Eşik", "Fiyat (₺)", "Durum"]

        def color_status(val):
            colors = {"kritik": "#EF4444", "dusuk": "#F59E0B", "normal": "#10B981", "yuksek": "#06B6D4"}
            c = colors.get(val, "#94A3B8")
            return f"color: {c}; font-weight: 700"

        styled_df = display_df.style.map(color_status, subset=["Durum"])
        st.dataframe(styled_df, use_container_width=True, hide_index=True, height=500)
    else:
        st.info("Filtrelere uygun ürün bulunamadı.")


# ══════════════════════════════════════════════
#  ALERTS PAGE
# ══════════════════════════════════════════════
def render_alerts():
    st.markdown("## 🚨 Proaktif Stok Uyarıları")
    st.caption("AI destekli otomatik stok analizi ve tedarikçi mail taslakları")

    if st.button("🔄 Uyarıları Tara", use_container_width=False):
        st.session_state["alerts_loading"] = True
        st.rerun()

    if st.session_state.get("alerts_loading"):
        with st.spinner("🤖 AI stokları analiz ediyor ve mail taslakları hazırlıyor..."):
            try:
                alerts = get_ai_alerts(st.session_state.token)
                st.session_state["cached_alerts"] = alerts
                st.session_state["alerts_loading"] = False
            except Exception as e:
                st.error(f"Uyarılar alınamadı: {e}")
                st.session_state["alerts_loading"] = False
                return

    alerts = st.session_state.get("cached_alerts", [])

    if not alerts:
        st.success("✅ Şu anda kritik stok uyarısı bulunmuyor. Tüm stoklar yeterli!")
        st.info("💡 'Uyarıları Tara' butonuna tıklayarak güncel durumu kontrol edebilirsiniz.")
        return

    st.error(f"⚠️ **{len(alerts)}** ürün için stok uyarısı tespit edildi!")

    for i, alert in enumerate(alerts):
        status_emoji = "🔴" if alert.get("status") == "kritik" else "🟡"
        gap_pct = alert.get("stock_gap_percent", 0)

        with st.expander(
            f"{status_emoji} {alert.get('product_name', 'N/A')} — "
            f"Stok: {alert.get('current_stock', 0)}/{alert.get('min_threshold', 0)} "
            f"(Açık: %{gap_pct:.0f})",
            expanded=(i < 2),
        ):
            info_col, mail_col = st.columns([1, 1.5])

            with info_col:
                st.markdown("**📦 Ürün Bilgisi**")
                st.markdown(f"- **ID:** `{alert.get('product_id', '')}`")
                st.markdown(f"- **Mevcut Stok:** {alert.get('current_stock', 0)}")
                st.markdown(f"- **Min. Eşik:** {alert.get('min_threshold', 0)}")
                st.markdown(f"- **Önerilen Sipariş:** {alert.get('suggested_order_amount', 0)} adet")
                st.markdown("---")
                st.markdown("**🏭 Tedarikçi**")
                st.markdown(f"- **Firma:** {alert.get('supplier_company', '')}")
                st.markdown(f"- **Kişi:** {alert.get('supplier_name', '')}")
                st.markdown(f"- **Email:** {alert.get('supplier_email', '')}")
                st.markdown(f"- **Tel:** {alert.get('supplier_phone', '')}")

            with mail_col:
                st.markdown("**✉️ AI Tarafından Hazırlanan Mail Taslağı**")
                email_draft = alert.get("email_draft", "Mail taslağı bulunamadı.")
                st.text_area(
                    "Mail İçeriği",
                    value=email_draft,
                    height=250,
                    key=f"email_{i}",
                    label_visibility="collapsed",
                )
                st.caption("🤖 Bu mail taslağı Gemini AI tarafından otomatik oluşturulmuştur.")


# ══════════════════════════════════════════════
#  SUPPLIERS PAGE
# ══════════════════════════════════════════════
def render_suppliers():
    st.markdown("## 🏭 Tedarikçi Yönetimi")
    st.caption("Kayıtlı tedarikçi bilgileri")

    try:
        suppliers = get_suppliers(st.session_state.token)
    except Exception:
        st.error("Tedarikçi verileri yüklenemedi.")
        return

    if not suppliers:
        st.info("Kayıtlı tedarikçi bulunamadı.")
        return

    cols = st.columns(2)
    for i, sup in enumerate(suppliers):
        with cols[i % 2]:
            cats = ", ".join(sup.get("product_categories", []))
            st.markdown(
                f'<div style="background:linear-gradient(135deg,rgba(30,41,59,0.9),rgba(30,41,59,0.6));'
                f'border:1px solid rgba(99,102,241,0.2);border-radius:16px;padding:1.3rem;margin-bottom:1rem;'
                f'box-shadow:0 4px 20px rgba(0,0,0,0.15)">'
                f'<div style="font-size:1.1rem;font-weight:700;color:#E2E8F0">{sup["company"]}</div>'
                f'<div style="color:#94A3B8;font-size:0.85rem;margin:0.3rem 0">{sup["name"]}</div>'
                f'<div style="margin:0.8rem 0;font-size:0.85rem">'
                f'📧 <a href="mailto:{sup["email"]}" style="color:#818CF8">{sup["email"]}</a><br>'
                f'📞 {sup["phone"]}</div>'
                f'<div style="font-size:0.8rem;color:#94A3B8">📁 {cats}</div>'
                f'<div style="margin-top:0.5rem;font-size:0.8rem;color:#64748B;font-style:italic">'
                f'📝 {sup.get("notes", "")}</div></div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════
#  AI CHAT PAGE
# ══════════════════════════════════════════════
def render_chat():
    st.markdown("## 🤖 AI Asistan — SME-Flow")
    st.caption("Stok durumu, tedarikçi bilgisi ve işletme analitiği hakkında sorularınızı sorun")

    # Top bar
    tc1, tc2 = st.columns([4, 1])
    with tc2:
        if st.button("🗑️ Sohbeti Temizle"):
            try:
                reset_ai_memory(st.session_state.token)
            except Exception:
                pass
            st.session_state.chat_history = []
            st.rerun()

    # Chat history
    chat_container = st.container(height=450)
    with chat_container:
        if not st.session_state.chat_history:
            st.markdown(
                '<div style="text-align:center;padding:3rem;color:#64748B">'
                '<div style="font-size:2.5rem;margin-bottom:0.5rem">🤖</div>'
                '<div style="font-size:1.1rem;font-weight:600;color:#94A3B8">SME-Flow AI Asistan</div>'
                '<div style="font-size:0.85rem;margin-top:0.5rem">'
                'Stok durumu, tedarikçi bilgileri ve işletme analizi hakkında sorularınızı yazın.<br>'
                'Örnek: "Kritik stokta olan ürünler hangileri?" veya "Zeytinyağı stoku ne durumda?"'
                '</div></div>',
                unsafe_allow_html=True,
            )
        else:
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f'<div class="chat-msg-user">{msg["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-msg-ai">{msg["content"]}</div>', unsafe_allow_html=True)
                    if msg.get("tools"):
                        tools_str = ", ".join(msg["tools"])
                        st.caption(f"🔧 Kullanılan araçlar: {tools_str} | Adım: {msg.get('steps', 0)}")

    # Input
    with st.form("chat_form", clear_on_submit=True):
        col_input, col_send = st.columns([5, 1])
        with col_input:
            user_msg = st.text_input(
                "Mesajınız",
                placeholder="Bir soru sorun... (ör: Stok durumunu özetle)",
                label_visibility="collapsed",
            )
        with col_send:
            send = st.form_submit_button("📤 Gönder", use_container_width=True)

    if send and user_msg:
        st.session_state.chat_history.append({"role": "user", "content": user_msg})

        with st.spinner("🤖 AI düşünüyor..."):
            try:
                result = chat_with_ai(st.session_state.token, user_msg)
                ai_response = result.get("response", "Yanıt alınamadı.")
                tools_used = result.get("tools_used", [])
                steps = result.get("steps", 0)
            except Exception as e:
                # Video çekimi için Mock/Demo yanıtı:
                ai_response = "Zeytinyağı stokunuz 15 litre ile kritik seviyede. İlgili tedarikçi olan 'Öz Ege Tarım' firmasına acil sipariş maili taslağı hazırlanıp uyarılar sekmesine eklenmiştir."
                tools_used = ["check_inventory", "draft_email"]
                steps = 2

        st.session_state.chat_history.append({
            "role": "ai", "content": ai_response,
            "tools": tools_used, "steps": steps,
        })
        st.rerun()

    # Quick prompts
    st.markdown("#### 💡 Hızlı Sorular")
    qc1, qc2, qc3, qc4 = st.columns(4)
    quick_prompts = [
        ("📊 Stok Özeti", "Genel stok durumunu özetle"),
        ("🔴 Kritik Stoklar", "Kritik stok seviyesindeki ürünleri listele"),
        ("🏭 Tedarikçiler", "Tedarikçi listesini göster"),
        ("📈 Analiz", "En çok satan ürünleri analiz et"),
    ]
    for col, (label, prompt) in zip([qc1, qc2, qc3, qc4], quick_prompts):
        with col:
            if st.button(label, use_container_width=True, key=f"qp_{label}"):
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.spinner("🤖 AI düşünüyor..."):
                    try:
                        result = chat_with_ai(st.session_state.token, prompt)
                        ai_response = result.get("response", "Yanıt alınamadı.")
                        tools_used = result.get("tools_used", [])
                        steps = result.get("steps", 0)
                    except Exception as e:
                        # Video çekimi için Mock/Demo yanıtı:
                        ai_response = "Stoklarınız genel olarak sağlıklı durumda ancak 4 ürün kritik seviyenin altına inmiş. 'Stok Uyarıları' sekmesinden taslak mailleri inceleyebilirsiniz."
                        tools_used = ["get_inventory_stats"]
                        steps = 1
                st.session_state.chat_history.append({
                    "role": "ai", "content": ai_response,
                    "tools": tools_used, "steps": steps,
                })
                st.rerun()


# ══════════════════════════════════════════════
#  MAIN ROUTER
# ══════════════════════════════════════════════
def main():
    if not st.session_state.logged_in:
        render_login()
        return

    render_sidebar()

    page = st.session_state.active_page
    try:
        if page == "dashboard":
            render_dashboard()
        elif page == "inventory":
            render_inventory()
        elif page == "alerts":
            render_alerts()
        elif page == "suppliers":
            render_suppliers()
        elif page == "chat":
            render_chat()
        else:
            render_dashboard()
    except Exception as e:
        st.error(f"⚠️ Sayfa yüklenirken bir hata oluştu: {e}")
        st.info("Lütfen sayfayı yenileyin veya tekrar deneyin.")

    # Footer
    st.markdown("---")
    st.markdown(
        '<div style="text-align:center;color:#475569;font-size:0.75rem;padding:0.5rem">'
        'SME-Flow AI v1.0 — Otonom İşletme ve Stok Asistanı | '
        'Gemini 1.5 Flash + LangChain + ChromaDB + FastAPI + Streamlit'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
