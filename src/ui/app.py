import streamlit as st

st.set_page_config(
    page_title="Partner OS v3.2",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Partner OS")
st.markdown("### The Third Partner — Fasahov Bros. Brokerage")

st.markdown("""
Welcome to the digital back-office. 

Use the sidebar to navigate to:
*   **Prospect Intake:** Upload bulk CSV lists from Propwire or Title Companies.
*   **Prospect Roster:** View and filter the Top-of-Funnel database.
*   **Deal Pipeline:** View active deals, trigger the LangGraph analysis, and see verdicts.
*   **CFO Verification:** The Hallucination Firewall. Verify extracted financial data before allowing the OS to calculate math and generate an LOI.
""")

# Initialize checkpointer in session state for cross-page persistence
if "checkpointer" not in st.session_state:
    import sqlite3
    import config
    from langgraph.checkpoint.sqlite import SqliteSaver
    from src.firehouse.scheduler import start_firehouse
    
    # Start the background scheduling engine
    start_firehouse()
    
    # Use check_same_thread=False because Streamlit runs in multiple threads
    conn = sqlite3.connect(str(config.CHECKPOINT_DB_PATH), check_same_thread=False)
    st.session_state.checkpointer = SqliteSaver(conn)
