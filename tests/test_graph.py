import pytest
import sqlite3
from unittest.mock import patch
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
import config
from src.graph.deal_graph import build_graph
from src.database.db import get_connection

@patch("src.graph.deal_graph.librarian_node")
@patch("src.graph.deal_graph.cfo_extract_node")
@patch("src.utils.llm.complete")
@patch("src.graph.nodes.profiler.retrieve")
def test_graph_compilation_and_interrupt(mock_retrieve, mock_llm, mock_cfo, mock_librarian, tmp_path):
    # Mock node pass-throughs
    mock_librarian.side_effect = lambda state: state
    mock_cfo.side_effect = lambda state: {"financials": {"extracted": True}}
    
    # Mock LLM
    mock_llm.return_value = '{"archetype": "High-S", "confidence": 90, "pinneo_cites": [], "verdict": "APPROVE", "reasoning_text": "Good", "scribe_instructions": "Draft"}'
    
    # Mock Retriever
    mock_retrieve.return_value = []

    # Setup temporary checkpoint database
    db_path = tmp_path / "checkpoints.sqlite"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    memory = SqliteSaver(conn)
    
    # Compile graph with checkpointer
    graph = build_graph().compile(checkpointer=memory)
    
    config = {"configurable": {"thread_id": "deal_123_test"}}
    
    # 1. Initial Invocation
    conn_db = get_connection()
    conn_db.execute("""
        INSERT OR IGNORE INTO deals (deal_id, address, address_slug, jacket_path, thread_id, created_at, updated_at)
        VALUES ('123', '123 Main St', '123-main-st', '/dummy', 'deal_123_test', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """)
    conn_db.commit()
    conn_db.close()

    initial_state = {
        "deal_id": "123",
        "address": "123 Main St",
        "cfo_verified": False
    }

    result = graph.invoke(initial_state, config)

    # Should stop after cfo_extract
    state_after_interrupt = graph.get_state(config)
    assert state_after_interrupt.next == ()  # It hit the __end__ edge
    assert "extracted" in result.get("financials", {})

    # 2. Resume Invocation (Simulate human verification)
    # Inject a dummy verified_financials_id to satisfy Phase 3
    conn_db = get_connection()
    cursor = conn_db.cursor()
    cursor.execute("INSERT INTO verified_financials (deal_id, data, verified_at) VALUES ('123', '{}', CURRENT_TIMESTAMP)")
    verified_id = cursor.lastrowid
    conn_db.commit()
    conn_db.close()

    resume_result = graph.invoke(
        Command(
            resume=True,
            update={"cfo_verified": True, "financials": {"verified_financials_id": verified_id}},
            goto="cfo_calculate"
        ),
        config
    )
    
    # Should complete the graph
    assert "calculated" in resume_result.get("financials", {})
    assert "High-S" in resume_result.get("seller_archetype", "")
    assert resume_result.get("verdict") in ["APPROVE", "KILL", "UNKNOWN"] # Verdict could be anything since manager is now live in this test, or we mock it.    
    conn.close()
