import pytest
import sqlite3
import asyncio
from unittest.mock import patch
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
import config
from src.graph.deal_graph import build_graph
from src.database.db import get_connection

@patch("src.graph.deal_graph.librarian_node_wrapper")
@patch("src.graph.deal_graph.cfo_extract_node")
@patch("src.utils.llm.complete")
@patch("src.graph.nodes.profiler.retrieve")
@pytest.mark.asyncio
async def test_graph_compilation_and_interrupt_async(mock_retrieve, mock_llm, mock_cfo, mock_librarian, tmp_path):
    """
    Verifies graph interrupt at cfo_extract and resumption via ainvoke with AsyncSqliteSaver.
    """
    # Agnostic Mocks to prevent signature mismatch
    mock_librarian.side_effect = lambda *args, **kwargs: args[0]
    mock_cfo.side_effect = lambda *args, **kwargs: {"financials": {"extracted": True}}
    
    # Mock LLM
    mock_llm.return_value = '{"archetype": "High-S", "confidence": 90, "pinneo_cites": [], "verdict": "APPROVE", "reasoning_text": "Good", "scribe_instructions": "Draft"}'
    
    # Mock Retriever
    mock_retrieve.return_value = []

    # Setup temporary asynchronous checkpoint database
    db_path = tmp_path / "checkpoints.sqlite"
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as memory:
        # Compile graph with async checkpointer
        graph = build_graph().compile(checkpointer=memory)
        
        config_dict = {"configurable": {"thread_id": "deal_123_test"}}
        
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

        # First Invocation
        result = await graph.ainvoke(initial_state, config_dict)

        # Should stop after cfo_extract
        state_after_interrupt = await graph.aget_state(config_dict)
        assert state_after_interrupt.next == ()  # It hit the __end__ edge
        assert "extracted" in result.get("financials", {})

        # 2. Resume Invocation (Simulate human verification)
        conn_db = get_connection()
        cursor = conn_db.cursor()
        cursor.execute("INSERT INTO verified_financials (deal_id, data, verified_at) VALUES ('123', '{}', CURRENT_TIMESTAMP)")
        verified_id = cursor.lastrowid
        conn_db.commit()
        conn_db.close()

        resume_result = await graph.ainvoke(
            Command(
                resume=True,
                update={"cfo_verified": True, "financials": {"verified_financials_id": verified_id}},
                goto="cfo_calculate"
            ),
            config_dict
        )
        
        # Should complete the graph
        assert "calculated" in resume_result.get("financials", {})
        assert "High-S" in resume_result.get("seller_archetype", "")

@pytest.mark.asyncio
async def test_graph_entry(tmp_path):
    # Wrapper to trigger the async test properly in pytest
    await test_graph_compilation_and_interrupt_async(tmp_path=tmp_path)
