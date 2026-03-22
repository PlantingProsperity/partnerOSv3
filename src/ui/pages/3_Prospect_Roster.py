import streamlit as st
import pandas as pd
from src.database.db import get_connection

st.title("Prospect Roster")
st.markdown("Your Top-of-Funnel database. The Firehouse Scheduler pulls from this list to generate personalized Bird Letters.")

conn = get_connection()
# Get high-level stats
total = conn.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
high_equity = conn.execute("SELECT COUNT(*) FROM prospects WHERE equity_score = 'HIGH'").fetchone()[0]

col1, col2 = st.columns(2)
col1.metric("Total Prospects", total)
col2.metric("High Equity Prospects", high_equity)

st.divider()

# Load data into a Pandas DataFrame for interactive display
query = "SELECT id, owner_name, address, parcel_number, equity_score, pipeline_stage, source, created_at FROM prospects ORDER BY created_at DESC"
df = pd.read_sql_query(query, conn)
conn.close()

if df.empty:
    st.info("The roster is currently empty. Upload a CSV list in the Prospect Intake tab to begin.")
else:
    # Make pipeline stage categorical for filtering in the UI
    df['pipeline_stage'] = df['pipeline_stage'].astype('category')
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "owner_name": "Owner Name",
            "address": "Property Address",
            "parcel_number": "Parcel Number",
            "equity_score": st.column_config.TextColumn("Equity", help="HIGH > 40%, LOW < 20%"),
            "pipeline_stage": "Stage",
            "source": "Source",
            "created_at": st.column_config.DatetimeColumn("Imported", format="MMM DD, YYYY")
        }
    )
