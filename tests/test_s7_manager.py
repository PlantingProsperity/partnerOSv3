import pytest
from unittest.mock import patch
from src.graph.nodes.manager import manager_node
from src.graph.state import DealState
from src.database.db import get_connection

@patch("src.graph.nodes.manager.llm.complete")
def test_manager_node_approve(mock_complete):
    deal_id = "test_manager_123"
    
    # 1. Setup mock LLM response
    mock_complete.return_value = '{"verdict": "APPROVE", "confidence": 92, "reasoning_text": "Good deal.", "scribe_instructions": "- Offer 1M\\n- 10% down"}'
    
    # 2. Setup initial state
    state = DealState(
        deal_id=deal_id,
        address="123 Manager St",
        parcel_number="123",
        status="UNDER_REVIEW",
        cfo_verified=True,
        heuristic_flagged=True,
        heuristic_failures=["DSCR below floor"],
        financials={"dscr": 0.9, "cap_rate": 0.08},
        property_data={"zoning": "R1", "hold_years": 10, "tax_status": "CURRENT"},
        seller_archetype="High-S",
        profiler_confidence=90,
        profiler_cites=[],
        verdict="",
        reasoning_text="",
        manager_confidence=0,
        scribe_instructions="",
        loi_draft=""
    )
    
    # 3. Insert dummy deal to satisfy foreign key constraint
    conn = get_connection()
    conn.execute("""
        INSERT OR IGNORE INTO deals (deal_id, address, address_slug, jacket_path, thread_id, created_at, updated_at)
        VALUES (?, '123 Manager St', '123-manager-st', '/dummy', 'thread_manager_123', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (deal_id,))
    conn.commit()
    conn.close()
    
    # 4. Execute node
    result = manager_node(state)
    
    # 5. Verify results
    assert result["verdict"] == "APPROVE"
    assert result["manager_confidence"] == 92
    assert "10% down" in result["scribe_instructions"]
    assert result["status"] == "APPROVED"
    
    # 6. Verify SQLite insert
    conn = get_connection()
    row = conn.execute("SELECT * FROM verdicts WHERE deal_id = ?", (deal_id,)).fetchone()
    assert row is not None
    assert row["verdict"] == "APPROVE"
    
    # 7. Cleanup
    conn.execute("DELETE FROM verdicts WHERE deal_id = ?", (deal_id,))
    conn.execute("DELETE FROM deals WHERE deal_id = ?", (deal_id,))
    conn.commit()
    conn.close()
