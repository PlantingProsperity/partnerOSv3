import streamlit as st
import uuid
import os
import json
from pathlib import Path
from src.database.db import get_connection
from src.graph.deal_graph import build_graph
import config

st.title("Deal Pipeline")

# We compile the graph using the checkpointer stored in session_state from app.py
if "checkpointer" not in st.session_state:
    st.warning("Please start from the main app page to initialize the system.")
    st.stop()
    
graph = build_graph().compile(checkpointer=st.session_state.checkpointer)

# ── Create New Deal Form ──────────────────────────────────────────────────────
with st.expander("➕ Start New Deal Analysis", expanded=False):
    with st.form("new_deal_form"):
        col1, col2 = st.columns([1, 1])
        with col1:
            address = st.text_input("Property Address")
            parcel_number = st.text_input("Parcel Number (Optional, recommended for Scout)")
        with col2:
            uploaded_files = st.file_uploader("Upload Financials/OM", accept_multiple_files=True)
            
        submit = st.form_submit_button("Trigger Pipeline")
        
        if submit and address:
            deal_id = f"deal_{uuid.uuid4().hex[:8]}"
            
            # 0. Save uploaded files to staging/inbox/
            config.INBOX_DIR.mkdir(parents=True, exist_ok=True)
            for file in uploaded_files:
                file_path = config.INBOX_DIR / file.name
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
            
            # 1. Create record in SQLite deals table
            conn = get_connection()
            conn.execute("""
                INSERT INTO deals (deal_id, address, address_slug, jacket_path, thread_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (deal_id, address, address.replace(" ", "-").lower(), f"/deals/{deal_id}", deal_id))
            conn.commit()
            conn.close()
            
            # 2. Invoke LangGraph
            initial_state = {
                "deal_id": deal_id,
                "address": address,
                "parcel_number": parcel_number if parcel_number else None,
                "status": "INTAKE",
                "cfo_verified": False, # Forces the graph to pause at the CFO gate
                "heuristic_flagged": False,
                "heuristic_failures": [],
                "financials": {},
                "financial_doc_paths": [], # Librarian will populate this
                "property_data": {},
                "seller_archetype": "",
                "profiler_confidence": 0,
                "profiler_cites": [],
                "verdict": "",
                "reasoning_text": "",
                "manager_confidence": 0,
                "scribe_instructions": "",
                "loi_draft": ""
            }
            
            config_dict = {"configurable": {"thread_id": deal_id}}
            
            with st.status(f"Pipeline started for {deal_id}...", expanded=True) as status:
                # We use stream() to let it run until the first interrupt
                for event in graph.stream(initial_state, config_dict):
                    for node_name, node_output in event.items():
                        st.write(f"✅ Executed: **{node_name}**")
                        
                status.update(label="Paused at Hallucination Firewall", state="complete")
                    
            st.success(f"Deal {deal_id} created! It is now waiting for CFO Verification.")
            st.rerun()

from src.ui.styles import inject_mac_styles
from src.ui.components import bento_card, render_agent_bar

inject_mac_styles()

st.title("Strategic Deal Board")
st.markdown("<p class='mac-subtext'>High-Leverage Pipeline — From Ingest to Verdict</p>", unsafe_allow_html=True)

# ... (rest of the New Deal form remains the same) ...

# ── Strategic Dashboard ────────────────────────────────────────────────────
st.markdown("### Active Deal Analysis")

conn = get_connection()
# Only show distinct addresses to clean up the 'nonsense' noise
deals = conn.execute("""
    SELECT deal_id, address, created_at 
    FROM deals 
    GROUP BY address 
    ORDER BY created_at DESC
""").fetchall()
conn.close()

if not deals:
    st.info("No active deals in the pipeline.")
else:
    for deal in deals:
        deal_id = deal["deal_id"]
        
        # Check LangGraph State
        config_dict = {"configurable": {"thread_id": deal_id}}
        state = graph.get_state(config_dict)
        
        if not state.values:
            continue # Skip ghost entries

        with st.container(border=True):
            cols = st.columns([3, 1, 1])
            cols[0].markdown(f"### {deal['address']}")
            cols[0].caption(f"Principal Thread ID: `{deal_id}`")
            
            # --- STATUS HUB ---
            if state.next and 'cfo_calculate' in state.next:
                cols[1].warning("🛑 CFO PENDING")
                with st.expander("📝 Verify Forensic Extraction", expanded=False):
                    st.write("The CFO has extracted metrics. Please verify before the Manager issues a verdict.")
                    # We can eventually embed the verification form here
                    st.page_link("pages/5_CFO_Verification.py", label="Open Verification Suite", icon="📊")
            
            elif not state.next: # Graph is finished
                verdict = state.values.get("verdict", "UNKNOWN")
                if verdict == "APPROVE":
                    cols[1].success("💎 APPROVED")
                else:
                    cols[1].error("💀 KILLED")
                
                # --- THE 'STORY' (RESCUE LOGIC) ---
                fin = state.values.get("financials", {})
                reasoning = state.values.get("reasoning_text", "No synthesis provided.")
                
                m1, m2, m3 = st.columns([1, 1, 3])
                m1.metric("DSCR", f"{fin.get('dscr', 0.0):.2f}")
                m2.metric("Cap Rate", f"{fin.get('cap_rate', 0.0)*100:.1f}%")
                
                # The primary value add: The Manager's Logic
                m3.markdown(f"**Principal's Counsel:** {reasoning[:250]}...")
                
                if verdict == "APPROVE":
                    st.page_link("pages/6_Workspace.py", label="Open Deal Workspace", icon="🏗️")
            else:
                cols[1].info(f"🔄 {state.next[0]}")

# AGENT STATUS BAR
render_agent_bar()
