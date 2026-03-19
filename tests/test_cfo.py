import pytest
import pandas as pd
import json
from pathlib import Path
from src.graph.nodes.cfo import _parse_document, cfo_calculate_node
from src.graph.state import DealState
from src.database.db import get_connection

def test_hybrid_parser_csv(tmp_path):
    # Create a dummy CSV
    csv_path = tmp_path / "test_financials.csv"
    df = pd.DataFrame({
        "Category": ["Gross Income", "Operating Expenses"],
        "Amount": [120000, 45000]
    })
    df.to_csv(csv_path, index=False)
    
    # Parse the document
    result = _parse_document(csv_path)
    
    # Verify it returns a Markdown string containing the data
    assert isinstance(result, str)
    assert "test_financials.csv" in result
    assert "Gross Income" in result
    assert "120000" in result
    assert "Operating Expenses" in result

def test_cfo_calculate_node():
    deal_id = "test_deal_123"
    
    # 1. Setup mock verified_financials record
    mock_verified_data = {
        "noi": {"value": 75000},
        "asking_price": {"value": 1000000},
        "annual_debt_service": {"value": 60000}
    }
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 0. Insert dummy deal to satisfy foreign key constraint
    cursor.execute("""
        INSERT OR IGNORE INTO deals (deal_id, address, address_slug, jacket_path, thread_id, created_at, updated_at)
        VALUES (?, '123 Test Ave', '123-test-ave', '/dummy', 'thread_test_123', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (deal_id,))
    
    # 1. Setup mock verified_financials record
    cursor.execute("""
        INSERT INTO verified_financials (deal_id, data, verified_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, (deal_id, json.dumps(mock_verified_data)))
    verified_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # 2. Setup mock state
    state = DealState(
        deal_id=deal_id,
        address="123 Test Ave",
        status="UNDER_REVIEW",
        cfo_verified=True,
        heuristic_flagged=False,
        heuristic_failures=[],
        financials={"verified_financials_id": verified_id},
        property_data={},
        seller_archetype="",
        verdict="",
        reasoning_text="",
        conditions_to_flip=[]
    )
    
    # 3. Execute Node
    result = cfo_calculate_node(state)
    
    # 4. Verify Math
    financials = result["financials"]
    assert financials["calculated"] is True
    assert financials["cap_rate"] == 0.075  # 75k / 1M
    assert financials["dscr"] == 1.25       # 75k / 60k
    
    # Verify Thresholds (Assuming config: CAP_FLOOR=0.06, DSCR_FLOOR=1.15)
    assert financials["below_cap_floor"] is False
    assert financials["below_dscr_floor"] is False
    
    # Clean up
    conn = get_connection()
    conn.execute("DELETE FROM verified_financials WHERE id = ?", (verified_id,))
    conn.execute("DELETE FROM financial_analyses WHERE deal_id = ?", (deal_id,))
    conn.commit()
    conn.close()
