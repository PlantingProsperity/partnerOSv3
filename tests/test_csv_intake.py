import pytest
import pandas as pd
import uuid
from pathlib import Path
from src.integrations.csv_intake import process_prospect_csv
from src.database.db import get_connection

def test_csv_intake_deduplication(tmp_path):
    # 1. Create dummy CSV with weird headers
    csv_path = tmp_path / "messy_prospects.csv"
    p1, p2, p3 = f"P-{uuid.uuid4()}", f"P-{uuid.uuid4()}", f"P-{uuid.uuid4()}"
    df = pd.DataFrame({
        "Owner 1 Name": ["John Doe", "Jane Smith", "Bob Corp"],
        "Property_Address": ["123 Main St", "456 Oak Ave", "789 Pine Rd"],
        "APN": [p1, p2, p3],
        "Estimated_Equity": ["55%", "15%", "Unknown"]
    })
    df.to_csv(csv_path, index=False)
    
    # 2. Run Intake (First pass)
    stats1 = process_prospect_csv(csv_path)
    assert stats1["inserted"] == 3
    assert stats1["duplicates_skipped"] == 0
    
    # Verify DB
    conn = get_connection()
    count = conn.execute(f"SELECT COUNT(*) FROM prospects WHERE parcel_number IN ('{p1}', '{p2}', '{p3}')").fetchone()[0]
    assert count == 3
    
    # Verify Equity categorization
    high_equity = conn.execute(f"SELECT equity_score FROM prospects WHERE parcel_number = '{p1}'").fetchone()[0]
    assert high_equity == 'HIGH'
    
    low_equity = conn.execute(f"SELECT equity_score FROM prospects WHERE parcel_number = '{p2}'").fetchone()[0]
    assert low_equity == 'LOW'
    
    # 3. Run Intake (Second pass - should deduplicate all)
    stats2 = process_prospect_csv(csv_path)
    assert stats2["inserted"] == 0
    assert stats2["duplicates_skipped"] == 3
    
    # 4. Clean up
    conn.execute(f"DELETE FROM prospects WHERE parcel_number IN ('{p1}', '{p2}', '{p3}')")
    conn.execute("DELETE FROM csv_import_log WHERE filename = 'messy_prospects.csv'")
    conn.commit()
    conn.close()
