import pytest
import pandas as pd
from pathlib import Path
from src.integrations.csv_intake import process_prospect_csv
from src.database.db import get_connection

def test_csv_intake_deduplication(tmp_path):
    # 1. Create dummy CSV with weird headers
    csv_path = tmp_path / "messy_prospects.csv"
    df = pd.DataFrame({
        "Owner 1 Name": ["John Doe", "Jane Smith", "Bob Corp"],
        "Property_Address": ["123 Main St", "456 Oak Ave", "789 Pine Rd"],
        "APN": ["P-100", "P-200", "P-300"],
        "Estimated_Equity": ["55%", "15%", "Unknown"]
    })
    df.to_csv(csv_path, index=False)
    
    # 2. Run Intake (First pass)
    stats1 = process_prospect_csv(csv_path)
    assert stats1["inserted"] == 3
    assert stats1["duplicates_skipped"] == 0
    
    # Verify DB
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
    assert count == 3
    
    # Verify Equity categorization
    high_equity = conn.execute("SELECT equity_score FROM prospects WHERE parcel_number = 'P-100'").fetchone()[0]
    assert high_equity == 'HIGH'
    
    low_equity = conn.execute("SELECT equity_score FROM prospects WHERE parcel_number = 'P-200'").fetchone()[0]
    assert low_equity == 'LOW'
    
    # 3. Run Intake (Second pass - should deduplicate all)
    stats2 = process_prospect_csv(csv_path)
    assert stats2["inserted"] == 0
    assert stats2["duplicates_skipped"] == 3
    
    # 4. Clean up
    conn.execute("DELETE FROM prospects")
    conn.execute("DELETE FROM csv_import_log")
    conn.commit()
    conn.close()
