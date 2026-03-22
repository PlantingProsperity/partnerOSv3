import streamlit as st
import json
from src.database.db import get_connection
from src.graph.deal_graph import build_graph
from langgraph.types import Command

st.title("CFO Verification (Hallucination Firewall)")

# Compile graph using shared checkpointer
if "checkpointer" not in st.session_state:
    st.warning("Please start from the main app page to initialize the system.")
    st.stop()
    
graph = build_graph().compile(checkpointer=st.session_state.checkpointer)

# 1. Find all deals waiting for verification
conn = get_connection()
deals = conn.execute("SELECT * FROM deals ORDER BY created_at DESC").fetchall()

pending_deals = []
for deal in deals:
    config = {"configurable": {"thread_id": deal["deal_id"]}}
    state = graph.get_state(config)
    if state.next and 'cfo_calculate' in state.next:
        pending_deals.append((deal, state))

if not pending_deals:
    st.success("No deals currently waiting for CFO Verification.")
else:
    # 2. Build UI for each pending deal
    for deal, state in pending_deals:
        deal_id = deal["deal_id"]
        with st.container(border=True):
            st.subheader(f"Deal: {deal['address']}")
            
            # Fetch the unverified extraction from the database
            draft_row = conn.execute(
                "SELECT id, citations FROM draft_financials WHERE deal_id = ? ORDER BY created_at DESC LIMIT 1", 
                (deal_id,)
            ).fetchone()
            
            if not draft_row:
                st.error("Draft financials record missing. The LLM extraction may have failed.")
                continue
                
            draft_data = json.loads(draft_row["citations"])
            
            # Display fields for verification
            st.markdown("Please verify the extracted numbers against their citations before approving.")
            
            verified_data = {}
            for field, field_data in draft_data.items():
                if field_data is None:
                    # Missing value/citation handling (ADR-S4-02)
                    st.error(f"**{field.upper()}** — LLM failed to extract.")
                    val = st.number_input(f"Manually enter {field}", key=f"{deal_id}_{field}", value=0.0)
                    verified_data[field] = {"value": val, "citation": {"manual_override": True}}
                else:
                    val = field_data.get("value", 0.0)
                    cite = field_data.get("citation", {})
                    
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        verified_data[field] = {"value": st.number_input(f"{field.upper()}", key=f"{deal_id}_{field}", value=float(val)), "citation": cite}
                    with col2:
                        st.caption(f"**File:** {cite.get('file', 'UNKNOWN')} | **Page:** {cite.get('page', 'UNKNOWN')}")
                        st.info(f'"{cite.get("verbatim_text", "NO CITATION PROVIDED")}"')
            
            # Approve Action
            if st.button("✅ Approve Numbers & Calculate", key=f"approve_{deal_id}", type="primary"):
                # 1. Write the verified data to SQLite
                conn.execute("""
                    INSERT INTO verified_financials (deal_id, data, verified_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (deal_id, json.dumps(verified_data)))
                
                # Update the draft status
                conn.execute("UPDATE draft_financials SET status = 'VERIFIED' WHERE id = ?", (draft_row["id"],))
                conn.commit()
                
                # 2. Get the new verified ID
                verified_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                
                # 3. Resume the Graph!
                config = {"configurable": {"thread_id": deal_id}}
                with st.spinner("Resuming Deal Pipeline..."):
                    # We pass the verified ID back into the state, set cfo_verified=True, and tell it to resume.
                    for event in graph.stream(
                        Command(
                            resume=True, 
                            update={"cfo_verified": True, "financials": {"verified_financials_id": verified_id}}
                        ), 
                        config
                    ):
                        pass # Stream to the end
                
                st.success("Deal verified and pipeline resumed!")
                st.rerun()

conn.close()
