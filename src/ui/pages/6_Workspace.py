import streamlit as st
import sqlite3
import json
from pathlib import Path
import config
from src.ui.styles import inject_mac_styles
from src.ui.components import bento_card, render_agent_bar
from src.utils import llm

# 1. PAGE CONFIG & STYLES
inject_mac_styles()

st.title("Unified Workspace")
st.markdown("<p class='mac-subtext'>Senior Partner Deck — Strategic Deal Synthesis</p>", unsafe_allow_html=True)

# 2. STATE INITIALIZATION
if "current_deal_id" not in st.session_state:
    st.session_state.current_deal_id = None

# 3. PANE 1: THE DOCK (Deal Selector in Sidebar)
with st.sidebar:
    st.subheader("Active Pursuits")
    try:
        conn = sqlite3.connect(str(config.DB_PATH))
        conn.row_factory = sqlite3.Row
        deals = conn.execute("SELECT deal_id, address FROM deals ORDER BY updated_at DESC").fetchall()
        conn.close()
        
        deal_options = {d['address']: d['deal_id'] for d in deals}
        selected_address = st.radio("Select Deal Context", list(deal_options.keys()))
        if selected_address:
            st.session_state.current_deal_id = deal_options[selected_address]
            st.success(f"Context: {selected_address}")
    except Exception as e:
        st.error("No active deals found.")

# 4. MAIN WORKSPACE (SPLIT PANE 2 & 3)
if st.session_state.current_deal_id:
    deal_id = st.session_state.current_deal_id
    
    col_mentor, col_stage = st.columns([1, 1.5], gap="large")
    
    # --- PANE 2: THE MENTOR (Chat) ---
    with col_mentor:
        st.subheader("🧠 The Manager")
        st.markdown("<div style='height: 400px; overflow-y: auto; background: rgba(255,255,255,0.05); padding: 20px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
        # Fetch conversation history for this deal
        # For now, we show a clean interface for interaction
        st.info("Manager is ready. Ask about the 15-year hold or seller financing structures.")
        st.markdown("</div>", unsafe_allow_html=True)
        
        user_input = st.chat_input("Command the Manager...")
        if user_input:
            with st.status("Manager is thinking...", expanded=True):
                response = llm.complete(user_input, agent="manager", deal_id=deal_id)
                st.write(response)

    # --- PANE 3: THE STAGE (Forensics & Vault) ---
    with col_stage:
        tab_forensics, tab_vault, tab_draft = st.tabs(["📊 Forensics", "📁 The Vault", "📄 Drafts"])
        
        with tab_forensics:
            st.markdown("### Underwriting Metrics")
            try:
                conn = sqlite3.connect(str(config.DB_PATH))
                conn.row_factory = sqlite3.Row
                verdict = conn.execute(\"\"\"
                    SELECT verdict, confidence, reasoning_text, scribe_instructions 
                    FROM verdicts 
                    WHERE deal_id = ? 
                    ORDER BY issued_at DESC LIMIT 1
                \"\"\", (deal_id,)).fetchone()
                conn.close()
                
                if verdict:
                    cols = st.columns(2)
                    with cols[0]:
                        bento_card("Verdict", verdict['verdict'], subtext=f"Confidence: {verdict['confidence']}%")
                    with cols[1]:
                        bento_card("Core Logic", "Creative Structuring Required", subtext="Based on Pinneo Module 04")
                    
                    st.markdown("#### Manager's Reasoning")
                    st.write(verdict['reasoning_text'])
                else:
                    st.warning("No forensic synthesis available for this deal yet.")
            except Exception as e:
                st.error(f"Forensics Error: {e}")

        with tab_vault:
            st.markdown("### Deal Jacket Documents")
            # Logic to list files in deals/{deal_id}/documents/
            deal_dir = config.BASE_DIR / "deals" / deal_id / "documents"
            if deal_dir.exists():
                files = list(deal_dir.glob("*.*"))
                for f in files:
                    st.markdown(f"📄 **{f.name}**")
            else:
                st.info("No documents uploaded to this deal jacket yet.")

        with tab_draft:
            st.markdown("### Active Strategy: LOI")
            st.text_area("Live Editor", value="Dear Seller, Based on our analysis...", height=300)
            st.button("Sign & Send (Roman)")

else:
    st.image("https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&q=80&w=1000", caption="Select a deal to begin synthesis.")

# 5. AGENT STATUS BAR
render_agent_bar()
