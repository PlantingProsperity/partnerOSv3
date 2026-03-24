import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from langgraph.checkpoint.sqlite import SqliteSaver
from src.graph.deal_graph import build_graph
from src.database.db import get_connection

@patch("src.graph.deal_graph.librarian_node")
@patch("src.graph.deal_graph.cfo_extract_node")
@patch("src.graph.nodes.profiler.retrieve")
@patch("src.utils.llm.complete")
def test_s6_parallel_execution(mock_complete, mock_retrieve, mock_cfo, mock_librarian, tmp_path):
    # Mock node pass-throughs
    mock_librarian.side_effect = lambda state: state
    mock_cfo.side_effect = lambda state: state

    # Mock LLM for all nodes (Librarian, CFO, Profiler, Manager)
    # The return value needs to be a valid JSON string for any node that expects structured output
    def mock_llm_side_effect(*args, **kwargs):
        agent = kwargs.get("agent")
        if agent == "profiler":
            return '{"archetype": "High-D", "confidence": 95, "pinneo_cites": ["Control the narrative."]}'
        elif agent == "librarian":
            return '{"content_class": "OTHER", "deal_id": null}'
        elif agent == "cfo_p1":
            return '{}'
        return "{}"
        
    mock_complete.side_effect = mock_llm_side_effect
    
    # Mock Retriever to avoid DB locks and API calls
    mock_chunk = MagicMock()
    mock_chunk.source_path = "mock_path.md"
    mock_chunk.text = "Mock Pinneo Wisdom"
    mock_retrieve.return_value = [mock_chunk]
    
    # 1. Setup Scout & Deal Test Data in local DB
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO deals (deal_id, address, address_slug, jacket_path, thread_id, created_at, updated_at) 
        VALUES ('S6-DEAL', '123 Parallel St', '123-parallel', '/dummy', 'thread_s6', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """)
    conn.execute("INSERT OR REPLACE INTO clark_county_cache (parcel_number, address, tax_status, last_sale_date, updated_at) VALUES ('S6-TEST', '123 Parallel St', 'DELINQUENT', '2015-01-01', '2026-03-18')")
    conn.commit()
    conn.close()

    # 2. Setup Graph with Checkpointer
    db_path = tmp_path / "checkpoints.sqlite"
    cp_conn = sqlite3.connect(str(db_path), check_same_thread=False)
    memory = SqliteSaver(cp_conn)
    graph = build_graph().compile(checkpointer=memory)
    config = {"configurable": {"thread_id": "test_s6"}}

    # 3. Inject State
    initial_state = {
        "deal_id": "S6-DEAL",
        "address": "123 Parallel St",
        "parcel_number": "S6-TEST",
        "cfo_verified": True,
        "financials": {"calculated": True, "dscr": 1.2, "cap_rate": 0.08, "verified_financials_id": 999}
    }

    # Run the graph
    result = graph.invoke(initial_state, config)

    # 4. Verify parallel state merges
    assert result.get("property_data", {}).get("tax_status") == "DELINQUENT"

    cp_conn.close()

    # Cleanup with explicit timeout/retry or just ignore lock on cleanup
    try:
        conn = get_connection()
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM clark_county_cache WHERE parcel_number = 'S6-TEST'")
        conn.execute("DELETE FROM deals WHERE deal_id = 'S6-DEAL'")
        conn.commit()
        conn.close()
    except:
        pass
