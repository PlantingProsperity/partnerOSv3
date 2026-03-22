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

# ── Active Deals Dashboard ────────────────────────────────────────────────────
st.markdown("### Active Deals")

conn = get_connection()
deals = conn.execute("SELECT * FROM deals ORDER BY created_at DESC").fetchall()
conn.close()

if not deals:
    st.info("No active deals in the pipeline.")
else:
    for deal in deals:
        deal_id = deal["deal_id"]
        
        with st.container(border=True):
            cols = st.columns([3, 2, 2])
            cols[0].markdown(f"**{deal['address']}**")
            cols[0].caption(f"ID: `{deal_id}`")
            
            # Check LangGraph State
            config = {"configurable": {"thread_id": deal_id}}
            state = graph.get_state(config)
            
            if not state.values:
                cols[1].warning("Graph not started")
            elif state.next and 'cfo_calculate' in state.next:
                cols[1].error("🛑 Waiting for CFO Verification")
                cols[2].page_link("pages/5_CFO_Verification.py", label="Go to Verification")
            elif not state.next: # Graph is finished
                verdict = state.values.get("verdict", "UNKNOWN")
                
                if verdict == "APPROVE":
                    cols[1].success("✅ APPROVED")
                else:
                    cols[1].error("❌ KILLED")
                    
                # Rich State Visibility
                fin = state.values.get("financials", {})
                prop = state.values.get("property_data", {})
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("DSCR", f"{fin.get('dscr', 0.0):.2f}")
                m2.metric("Cap Rate", f"{fin.get('cap_rate', 0.0)*100:.1f}%")
                m3.metric("Hold Yrs", f"{prop.get('hold_years', 'N/A')}")
                m4.metric("Archetype", f"{state.values.get('seller_archetype', 'N/A')}")
                
                with st.expander("Manager Verdict & Instructions"):
                    st.write(state.values.get("reasoning_text", ""))
                    st.markdown("**Instructions given to Scribe:**")
                    st.write(state.values.get("scribe_instructions", ""))
                    
                if verdict == "APPROVE":
                    with st.expander("View LOI Draft"):
                        st.markdown(state.values.get("loi_draft", "No draft generated."))
            else:
                cols[1].info(f"Processing: {state.next}")
