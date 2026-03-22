import streamlit as st
import os
from pathlib import Path
import config
from src.integrations.csv_intake import process_prospect_csv

st.title("Bulk Prospect Intake")
st.markdown("Upload Title Company or Propwire `.csv` lists here. The system will map the columns, calculate equity categories, and deduplicate against existing parcels automatically.")

with st.container(border=True):
    uploaded_file = st.file_uploader("Upload Prospect List (CSV)", type=['csv'])
    
    if uploaded_file is not None:
        if st.button("Process List", type="primary"):
            with st.spinner("Processing list and deduplicating..."):
                # Save file to staging
                config.LISTS_DIR.mkdir(parents=True, exist_ok=True)
                file_path = config.LISTS_DIR / uploaded_file.name
                
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                    
                # Process the file
                stats = process_prospect_csv(file_path)
                
                # Display results
                if stats["errors"] > 0 and stats["total_rows"] == 0:
                    st.error("Failed to parse CSV. Please ensure it has Owner, Address, and Parcel columns.")
                else:
                    st.success("Import Complete!")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Rows", stats["total_rows"])
                    c2.metric("New Prospects Inserted", stats["inserted"], delta=stats["inserted"], delta_color="normal")
                    c3.metric("Duplicates Skipped", stats["duplicates_skipped"], delta=-stats["duplicates_skipped"], delta_color="off")
                    
                    st.info("You can view the updated database in the Prospect Roster tab.")
