import streamlit as st
import json
import pandas as pd
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
            
            st.markdown("Please verify the extracted numbers against their citations before approving.")
            
            # Prepare data for st.data_editor
            editor_data = []
            citations_map = {}
            for field, field_data in draft_data.items():
                if field_data is None:
                    editor_data.append({"Field": field.replace("_", " ").title(), "Value": 0.0})
                    citations_map[field] = {"file": "MISSING", "page": "N/A", "verbatim_text": "LLM failed to extract this field."}
                else:
                    editor_data.append({"Field": field.replace("_", " ").title(), "Value": float(field_data.get("value", 0.0))})
                    citations_map[field] = field_data.get("citation", {})
                    
            df = pd.DataFrame(editor_data)
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("**Editable Extraction**")
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "Field": st.column_config.Column(disabled=True),
                        "Value": st.column_config.NumberColumn(format="$%.2f")
                    },
                    hide_index=True,
                    width='stretch',
                    key=f"editor_{deal_id}"
                )
            
            with col2:
                st.markdown("**Citations (The Proof)**")
                for field, cite in citations_map.items():
                    with st.expander(f"{field.replace('_', ' ').title()} Source"):
                        st.caption(f"**File:** {cite.get('file', 'UNKNOWN')} | **Page:** {cite.get('page', 'UNKNOWN')}")
                        st.info(f'"{cite.get("verbatim_text", "NO CITATION PROVIDED")}"')
            
            # Approve Action
            if st.button("✅ Approve Numbers & Calculate", key=f"approve_{deal_id}", type="primary"):
                # 1. Rebuild the verified JSON structure from the edited dataframe
                verified_data = {}
                for index, row in edited_df.iterrows():
                    # Convert Display Field back to JSON key
                    original_field = row["Field"].replace(" ", "_").lower()
                    verified_data[original_field] = {
                        "value": row["Value"],
                        "citation": citations_map[original_field]
                    }
                
                # 2. Write the verified data to SQLite
                conn.execute("""
                    INSERT INTO verified_financials (deal_id, data, verified_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (deal_id, json.dumps(verified_data)))
                
                # Update the draft status
                conn.execute("UPDATE draft_financials SET status = 'VERIFIED' WHERE id = ?", (draft_row["id"],))
                conn.commit()
                
                # 3. Get the new verified ID
                verified_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                
                # 4. Resume the Graph!
                config = {"configurable": {"thread_id": deal_id}}
                with st.status("Resuming Deal Pipeline...", expanded=True) as status:
                    # We pass the verified ID back into the state, set cfo_verified=True, and tell it to resume.
                    for event in graph.stream(
                        Command(
                            resume=True, 
                            update={"cfo_verified": True, "financials": {"verified_financials_id": verified_id}},
                            goto="cfo_calculate"
                        ), 
                        config
                    ):
                        for node_name, node_output in event.items():
                            st.write(f"✅ Executed: **{node_name}**")
                    status.update(label="Pipeline Completed!", state="complete")
                
                st.success("Deal verified and pipeline resumed!")
                st.rerun()

conn.close()
