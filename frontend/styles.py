"""
SME-Flow AI — Custom CSS Styles
"""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}
.block-container { padding-top: 1rem !important; max-width: 1400px !important; }
header[data-testid="stHeader"] { background: rgba(15,23,42,0.8) !important; backdrop-filter: blur(12px) !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F172A 0%, #1a1f3a 100%) !important;
    border-right: 1px solid rgba(99,102,241,0.15) !important;
}
section[data-testid="stSidebar"] .stImage { text-align: center; }

/* ── Metric Cards ── */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(30,41,59,0.9) 0%, rgba(30,41,59,0.6) 100%);
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 16px;
    padding: 1.2rem 1rem;
    backdrop-filter: blur(10px);
    transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}
div[data-testid="stMetric"]:hover {
    border-color: rgba(99,102,241,0.5);
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(99,102,241,0.15);
}
div[data-testid="stMetric"] label { color: #94A3B8 !important; font-size: 0.8rem !important; text-transform: uppercase; letter-spacing: 0.5px; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #E2E8F0 !important; font-weight: 700 !important; font-size: 1.8rem !important; }

/* ── Tables ── */
div[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(99,102,241,0.15);
}

/* ── Chat ── */
.chat-msg-user {
    background: linear-gradient(135deg, #4F46E5, #6366F1);
    color: white; padding: 0.9rem 1.2rem; border-radius: 18px 18px 4px 18px;
    margin: 0.4rem 0; max-width: 80%; margin-left: auto;
    box-shadow: 0 2px 12px rgba(99,102,241,0.25);
    font-size: 0.95rem; line-height: 1.5;
}
.chat-msg-ai {
    background: linear-gradient(135deg, rgba(30,41,59,0.95), rgba(30,41,59,0.7));
    color: #E2E8F0; padding: 0.9rem 1.2rem; border-radius: 18px 18px 18px 4px;
    margin: 0.4rem 0; max-width: 85%;
    border: 1px solid rgba(99,102,241,0.12);
    box-shadow: 0 2px 12px rgba(0,0,0,0.1);
    font-size: 0.95rem; line-height: 1.6;
}

/* ── Alert Cards ── */
.alert-card-critical {
    background: linear-gradient(135deg, rgba(239,68,68,0.12), rgba(239,68,68,0.04));
    border-left: 4px solid #EF4444; border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 0.8rem;
    border: 1px solid rgba(239,68,68,0.2); border-left: 4px solid #EF4444;
}
.alert-card-low {
    background: linear-gradient(135deg, rgba(245,158,11,0.12), rgba(245,158,11,0.04));
    border-left: 4px solid #F59E0B; border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 0.8rem;
    border: 1px solid rgba(245,158,11,0.2); border-left: 4px solid #F59E0B;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #4F46E5, #7C3AED) !important;
    color: white !important; border: none !important; border-radius: 12px !important;
    padding: 0.6rem 1.5rem !important; font-weight: 600 !important;
    transition: all 0.3s ease !important; box-shadow: 0 4px 15px rgba(99,102,241,0.3) !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important; box-shadow: 0 6px 20px rgba(99,102,241,0.45) !important;
}

/* ── Status badges ── */
.badge-kritik { background: #EF4444; color: white; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.badge-dusuk { background: #F59E0B; color: #1E293B; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.badge-normal { background: #10B981; color: white; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.badge-yuksek { background: #06B6D4; color: white; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }

/* ── Login Page ── */
.login-container {
    max-width: 420px; margin: 3rem auto; padding: 2.5rem;
    background: linear-gradient(135deg, rgba(30,41,59,0.95), rgba(30,41,59,0.7));
    border: 1px solid rgba(99,102,241,0.2); border-radius: 24px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    backdrop-filter: blur(20px);
}
.login-title {
    text-align: center; font-size: 1.8rem; font-weight: 800;
    background: linear-gradient(135deg, #6366F1, #A78BFA);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.3rem;
}
.login-subtitle { text-align: center; color: #94A3B8; font-size: 0.9rem; margin-bottom: 1.5rem; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] {
    background: rgba(30,41,59,0.6) !important; border-radius: 10px !important;
    padding: 0.5rem 1rem !important; border: 1px solid rgba(99,102,241,0.1) !important;
    transition: all 0.3s !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #4F46E5, #6366F1) !important;
    border-color: transparent !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: rgba(30,41,59,0.6) !important; border-radius: 10px !important;
    border: 1px solid rgba(99,102,241,0.12) !important;
}

/* ── Pulse animation ── */
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
.pulse { animation: pulse 2s ease-in-out infinite; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0F172A; }
::-webkit-scrollbar-thumb { background: #4F46E5; border-radius: 3px; }
</style>
"""
