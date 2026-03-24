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

# 1. Custom Kanban Styling
st.markdown("""
<style>
    /* Force horizontal layout for columns */
    [data-testid="stHorizontalBlock"] {
        overflow-x: auto !important;
        display: flex !important;
        flex-wrap: nowrap !important;
        gap: 20px;
        padding-bottom: 20px;
    }
    
    /* Ensure columns have a strategic width */
    [data-testid="column"] {
        min-width: 320px !important;
        max-width: 320px !important;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 20px;
        padding: 15px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .kanban-stage-header {
        font-size: 14px;
        font-weight: 700;
        color: var(--mac-sub);
        text-transform: uppercase;
        margin-bottom: 15px;
        padding-left: 5px;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

st.title("Strategic Deal Flow")
st.markdown("<p class='mac-subtext'>Fasahov Bros. Principal Dashboard • Real-Time Pipeline Velocity</p>", unsafe_allow_html=True)

# ── KANBAN ARCHITECTURE ──────────────────────────────────────────────────
stages = {
    "INTAKE": "🆕 Intake",
    "UNDER_REVIEW": "📊 Underwriting",
    "STRATEGY": "🧠 Strategy",
    "VERDICT": "💎 Verdict"
}

cols = st.columns(len(stages))

conn = get_connection()
deals = conn.execute("SELECT * FROM deals ORDER BY updated_at DESC").fetchall()
conn.close()

for i, (stage_key, stage_label) in enumerate(stages.items()):
    with cols[i]:
        st.markdown(f'<div class="kanban-stage-header">{stage_label}</div>', unsafe_allow_html=True)
        
        # Filter deals for this stage
        for deal in deals:
            deal_id = deal["deal_id"]
            config_dict = {"configurable": {"thread_id": deal_id}}
            state = graph.get_state(config_dict)
            
            # Map LangGraph state to Kanban stage
            current_deal_stage = "INTAKE"
            if not state.values: continue
            
            if state.next:
                if 'cfo_calculate' in state.next: current_deal_stage = "UNDER_REVIEW"
                elif 'manager' in state.next: current_deal_stage = "STRATEGY"
            elif not state.next:
                current_deal_stage = "VERDICT"
                
            if current_deal_stage == stage_key:
                with st.container():
                    # --- THE DEAL CARD ---
                    verdict = state.values.get("verdict", "PENDING")
                    bg_color = "rgba(10, 132, 255, 0.1)" # Default Blue
                    if verdict == "APPROVE": bg_color = "rgba(52, 199, 89, 0.1)" # Green
                    elif verdict == "KILL": bg_color = "rgba(255, 59, 48, 0.1)" # Red
                    
                    st.markdown(f\"\"\"
                    <div class="bento-card" style="background: {bg_color}; padding: 15px; margin-bottom: 10px; min-height: 120px;">
                        <div style="font-weight: 700; font-size: 15px; color: white;">{deal['address']}</div>
                        <div style="font-size: 12px; color: rgba(255,255,255,0.6); margin-top: 5px;">ID: {deal_id[:8]}</div>
                        <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 10px 0;">
                        <div style="font-size: 13px; font-style: italic; color: rgba(255,255,255,0.8);">
                            {state.values.get('reasoning_text', 'Third Partner is analyzing...').split('.')[0]}
                        </div>
                    </div>
                    \"\"\", unsafe_allow_html=True)
                    
                    # Direct Action Links
                    if stage_key == "UNDER_REVIEW":
                        st.page_link("pages/5_CFO_Verification.py", label="Verify Forensics", icon="📊")
                    elif stage_key == "VERDICT":
                        st.page_link("pages/6_Workspace.py", label="Open Workspace", icon="🏗️")

# AGENT STATUS BAR
render_agent_bar()
