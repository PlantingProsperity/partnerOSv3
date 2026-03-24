import streamlit as st

st.set_page_config(
    page_title="Partner OS v3.2",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

from src.ui.styles import inject_mac_styles
inject_mac_styles()

import streamlit as st
import sqlite3
import config
from src.ui.styles import inject_mac_styles
from src.ui.components import bento_card, render_agent_bar
from src.utils import llm
from langgraph.checkpoint.sqlite import SqliteSaver
from src.firehouse.scheduler import start_firehouse

# 1. PAGE CONFIG & GLOBAL STYLES
st.set_page_config(
    page_title="Partner OS v3.2",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_mac_styles()

with st.sidebar:
    st.markdown("### 📡 Autonomous Ops")
    # Streamlit automatically lists pages, but we can add visual context here
    st.caption("Sourcer | Librarian | Brain")
    
    st.markdown("---")
    st.markdown("### 🏗️ Active Deal Flow")
    st.caption("Forensics | Strategy | Scribe")

# 2. CORE SYSTEM INITIALIZATION
if "checkpointer" not in st.session_state:
    start_firehouse()
    conn = sqlite3.connect(str(config.CHECKPOINT_DB_PATH), check_same_thread=False)
    st.session_state.checkpointer = SqliteSaver(conn)

# 3. PRINCIPAL GREETING
st.title("Good Morning, Roman.")

# Data Freshness Check
try:
    db_conn = sqlite3.connect(str(config.DB_PATH))
    last_pacs = db_conn.execute("SELECT ts FROM maintenance_log WHERE job_name = 'pacs_ingest' AND success = 1 ORDER BY ts DESC LIMIT 1").fetchone()
    db_conn.close()
    freshness = f"Market Intel: {last_pacs[0]}" if last_pacs else "Market Intel: Pending Full Load"
except:
    freshness = "System Integrity: 100%"

st.markdown(f"<p class='mac-subtext'>Fasahov Bros. Brokerage • {freshness}</p>", unsafe_allow_html=True)

# 4. MORNING BRIEF (THE SYNTHESIS)
st.subheader("Autonomous Synthesis")

col1, col2 = st.columns([2, 1], gap="large")

with col1:
    # --- PRIORITY TARGETS ---
    st.markdown("#### Priority Targets")
    try:
        db_conn = sqlite3.connect(str(config.DB_PATH))
        db_conn.row_factory = sqlite3.Row
        prospects = db_conn.execute("SELECT owner_name, address, parcel_number, hold_years FROM prospects WHERE equity_score = 'HIGH' ORDER BY created_at DESC LIMIT 2").fetchall()
        db_conn.close()

        if prospects:
            sub_cols = st.columns(2)
            for i, p in enumerate(prospects):
                with sub_cols[i]:
                    bento_card(
                        title=p['address'],
                        content=f"Owner: {p['owner_name']}",
                        subtext=f"Hold: {p['hold_years']} yrs | APN: {p['parcel_number']}"
                    )
                    # QUICK ACTIONS
                    btn_cols = st.columns(2)
                    if btn_cols[0].button(f"Analyze Lead", key=f"p_{i}_an"):
                        st.session_state.current_deal_id = f"deal_{p['parcel_number']}"
                        st.switch_page("pages/4_Deal_Pipeline.py")
                    if btn_cols[1].button(f"Open Folder", key=f"p_{i}_f"):
                        st.info("Coming soon: Real-time folder link")
        else:
            st.info("The Sourcer is hunting for new high-equity leads...")
    except:
        st.info("Database warming up...")

@st.cache_data(ttl=900) # Cache for 15 minutes to save tokens and reduce friction
def get_cached_strategy():
    try:
        thought_prompt = "Provide one sentence of high-level strategic wisdom for a commercial real estate principal based on the Greg Pinneo 'Transaction Engineering' doctrine. Be pithy."
        return llm.complete(thought_prompt, agent="manager")
    except:
        return "The market is moving. Stay disciplined in your underwriting."

with col2:
    # --- MANAGER'S COUNSEL ---
    st.markdown("#### The Principal's Counsel")
    thought = get_cached_strategy()
    st.markdown(f"""
    <div class="bento-card" style="border-left: 4px solid var(--mac-accent);">
        <p style="font-style: italic; font-size: 15px; line-height: 1.6;">"{thought}"</p>
        <span class="mac-subtext">— The Third Partner</span>
    </div>
    """, unsafe_allow_html=True)

# 5. RECENT INTELLIGENCE AUDIT
st.markdown("#### Recent Intelligence Audit")
brief_path = config.DATA_DIR / "morning_brief.md"
if brief_path.exists():
    with open(brief_path, "r", encoding="utf-8") as f:
        content = f.read()
    st.markdown(f"<div class='bento-card' style='font-size:14px; opacity:0.9;'>{content}</div>", unsafe_allow_html=True)

# 6. AGENT STATUS BAR (Fixed at bottom)
render_agent_bar()
