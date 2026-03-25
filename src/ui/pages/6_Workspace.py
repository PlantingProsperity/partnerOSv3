import streamlit as st
import sqlite3
import json
from pathlib import Path
import config
from src.graph.deal_graph import deal_graph as graph
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

# --- Cognitive Memory Hard-Init (ADR-S9-01) ---
if "checkpointer" not in st.session_state:
    from langgraph.checkpoint.sqlite import SqliteSaver
    conn = sqlite3.connect(str(config.CHECKPOINT_DB_PATH), check_same_thread=False)
    st.session_state.checkpointer = SqliteSaver(conn)
    st.toast("Cognitive Memory Initialized", icon="🧠")

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
        
        # 1. Persistent Chat History for this Deal
        if f"chat_history_{deal_id}" not in st.session_state:
            st.session_state[f"chat_history_{deal_id}"] = []
            
        chat_container = st.container(height=500)
        
        with chat_container:
            for msg in st.session_state[f"chat_history_{deal_id}"]:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
        
        user_input = st.chat_input("Command the Manager...")
        if user_input:
            # Display user message
            with chat_container:
                with st.chat_message("user"):
                    st.write(user_input)
            st.session_state[f"chat_history_{deal_id}"].append({"role": "user", "content": user_input})
            
            # Call Manager with Thinking Trace
            with st.status("The Principal is contemplating...", expanded=True):
                response_str = llm.complete(user_input, agent="manager", deal_id=deal_id)
                
                import re
                # Extract <think> content if present (DeepSeek-R1 style)
                think_match = re.search(r"<think>(.*?)</think>", response_str, re.DOTALL)
                final_advice = response_str
                
                if think_match:
                    think_content = think_match.group(1).strip()
                    final_advice = response_str.replace(think_match.group(0), "").strip()
                    with st.expander("🔍 Internal Thinking Process", expanded=False):
                        st.markdown(f"<p class='mac-subtext'>{think_content}</p>", unsafe_allow_html=True)
                
                st.write(final_advice)
                
            st.session_state[f"chat_history_{deal_id}"].append({"role": "assistant", "content": final_advice})
            st.rerun()

    # --- PANE 3: THE STAGE (Forensics & Vault) ---
    with col_stage:
        # --- Cognitive State Initialization (Global for all tabs) ---
        state_dict = st.session_state.get(f"last_state_{deal_id}", {})
        if not state_dict:
            # Fetch latest state if not in session
            config_dict = {"configurable": {"thread_id": deal_id}}
            # We must provide the checkpointer from session state
            checkpointer = st.session_state.get("checkpointer")
            if checkpointer:
                raw_state = graph.get_state(config_dict, checkpointer=checkpointer)
                if raw_state and raw_state.values:
                    state_dict = raw_state.values

        tab_forensics, tab_vault, tab_draft = st.tabs(["📊 Forensics", "📁 The Vault", "📄 Drafts"])
        
        with tab_forensics:
            st.markdown("### Underwriting Metrics")
            try:
                conn = sqlite3.connect(str(config.DB_PATH))
                conn.row_factory = sqlite3.Row
                verdict = conn.execute("""
                    SELECT verdict, confidence, reasoning_text, scribe_instructions 
                    FROM verdicts 
                    WHERE deal_id = ? 
                    ORDER BY issued_at DESC LIMIT 1
                """, (deal_id,)).fetchone()
                conn.close()
                
                if verdict:
                    cols = st.columns(2)
                    with cols[0]:
                        bento_card("Verdict", verdict['verdict'], subtext=f"Confidence: {verdict['confidence']}%")
                    with cols[1]:
                        bento_card("Core Logic", "Creative Structuring Required", subtext="Based on Pinneo Module 04")
                    
                    st.markdown("#### Manager's Reasoning")
                    st.write(verdict['reasoning_text'])
                    
                    # --- X-RAY VISION (Phase 1 Optimization) ---
                    st.markdown("#### 🔍 AI Logic Tree (X-Ray)")
                    
                    if state_dict:
                        failures = state_dict.get('heuristic_failures', [])
                        fin = state_dict.get('financials', {})
                        dscr = fin.get('dscr', 0.0)
                        
                        import altair as alt
                        import pandas as pd
                        
                        # Build logic tree visualization
                        # Did it pass the DSCR floor?
                        dscr_pass = dscr >= 1.25
                        # Did it pass Cap Rate floor?
                        cap_pass = fin.get('cap_rate', 0.0) >= 0.06
                        
                        tree_data = [
                            {"Logic Gate": "DSCR >= 1.25", "Status": "PASS" if dscr_pass else "FAIL", "Score": 100 if dscr_pass else 20},
                            {"Logic Gate": "Cap Rate >= 6.0%", "Status": "PASS" if cap_pass else "FAIL", "Score": 100 if cap_pass else 30},
                            {"Logic Gate": "Pinneo Rescue Pattern Match", "Status": "PASS" if verdict['verdict'] == 'APPROVE' and failures else "N/A", "Score": 95 if verdict['verdict'] == 'APPROVE' else 10}
                        ]
                        
                        df = pd.DataFrame(tree_data)
                        
                        chart = alt.Chart(df).mark_bar(cornerRadiusEnd=4).encode(
                            x=alt.X('Score:Q', scale=alt.Scale(domain=[0, 100]), title="Alignment Score"),
                            y=alt.Y('Logic Gate:N', sort=None, title=""),
                            color=alt.Color('Status:N', scale=alt.Scale(domain=['PASS', 'FAIL', 'N/A'], range=['#34c759', '#ff3b30', '#8e8e93']), legend=None),
                            tooltip=['Logic Gate', 'Status']
                        ).properties(height=150)
                        
                        st.altair_chart(chart, width='stretch')
                        
                        if failures:
                            st.caption(f"**Triggered Failures:** {', '.join(failures)}")
                    # --- GENERATIVE UI (Phase 3 Optimization) ---
                    st.markdown("---")
                    st.markdown("### 🏗️ Strategic Engineering")
                    from src.ui.registry import UI_COMPONENTS
                    
                    # The Manager now outputs 'ui_modules' in its JSON (H-MEM logic)
                    # For now, we infer from verdict reasoning or type
                    reasoning_text = verdict.get("reasoning_text", "").upper()
                    
                    # Check for keywords to trigger dynamic UI
                    triggered = False
                    if "WRAP" in reasoning_text or "SUBJECT-TO" in reasoning_text:
                        UI_COMPONENTS["WRAP"](dict(verdict))
                        triggered = True
                    if "REDEVELOPMENT" in reasoning_text or "DENSITY" in reasoning_text:
                        UI_COMPONENTS["REDEVELOPMENT"](dict(verdict))
                        triggered = True
                    
                    if not triggered:
                        st.caption("No specialized engineering tools required for this archetype.")
                else:
                    st.warning("No forensic synthesis available for this deal yet.")
            except Exception as e:
                st.error(f"Forensics Error: {e}")

        with tab_vault:
            st.markdown("### Deal Jacket Documents")
            
            # --- TIER 3 FORENSIC DEEP-LINKS ---
            st.markdown("#### 🔍 External Forensic Portals")
            col_a, col_b = st.columns(2)
            
            # Pad prop_id for Clark County systems
            search_id = deal_id.split('_')[-1] # Simple extraction
            if len(search_id) < 8: search_id = "41550000" # Fallback for test deals
            
            col_a.link_button("📜 Auditor: Recorded Docs", 
                             f"https://e-docs.clark.wa.gov/LandmarkWeb/Search/index?searchType=parcelid&parcelId={search_id}")
            col_b.link_button("📸 GIS: Property Photos", 
                             f"https://gis.clark.wa.gov/gishome/property/index.cfm?fuseaction=factsheet&account={search_id}")
            
            st.markdown("---")
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
            
            # Fetch speculative draft from state if it exists
            draft_content = "Dear Seller, Based on our analysis..."
            if state_dict:
                if state_dict.get("loi_draft"):
                    draft_content = state_dict.get("loi_draft")
                    st.success("✨ Auto-Drafted by Speculative Agent")
                
            st.text_area("Live Editor", value=draft_content, height=300)
            st.button("Sign & Send (Roman)")

else:
    st.image("https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&q=80&w=1000", caption="Select a deal to begin synthesis.")

# 5. AGENT STATUS BAR
render_agent_bar()
