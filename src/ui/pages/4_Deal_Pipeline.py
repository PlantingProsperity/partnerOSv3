import streamlit as st
import uuid
import json
from src.database.db import get_connection
from src.graph.deal_graph import build_graph

st.title("Deal Pipeline")

# We compile the graph using the checkpointer stored in session_state from app.py
if "checkpointer" not in st.session_state:
    st.warning("Please start from the main app page to initialize the system.")
    st.stop()
    
graph = build_graph().compile(checkpointer=st.session_state.checkpointer)

# ── Create New Deal Form ──────────────────────────────────────────────────────
with st.expander("➕ Start New Deal Analysis", expanded=False):
    with st.form("new_deal_form"):
        address = st.text_input("Property Address")
        parcel_number = st.text_input("Parcel Number (Optional, recommended for Scout)")
        submit = st.form_submit_button("Trigger Pipeline")
        
        if submit and address:
            deal_id = f"deal_{uuid.uuid4().hex[:8]}"
            
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
            
            config = {"configurable": {"thread_id": deal_id}}
            
            with st.spinner("Librarian and CFO Phase 1 executing..."):
                # We use stream() to let it run until the first interrupt
                for event in graph.stream(initial_state, config):
                    pass # We just want it to reach the interrupt state
                    
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
                    with st.expander("View LOI Draft"):
                        st.markdown(state.values.get("loi_draft", "No draft generated."))
                else:
                    cols[1].error("❌ KILLED")
                    with st.expander("View Reasoning"):
                        st.write(state.values.get("reasoning_text", ""))
                        st.write("Scribe Instructions:", state.values.get("scribe_instructions", ""))
            else:
                cols[1].info(f"Processing: {state.next}")
