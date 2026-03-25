import pytest
import sqlite3
import asyncio
from unittest.mock import patch, MagicMock
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from src.graph.deal_graph import build_graph
from src.database.db import get_connection

@patch("src.graph.deal_graph.librarian_node_wrapper")
@patch("src.graph.deal_graph.cfo_extract_node")
@patch("src.graph.nodes.profiler.retrieve")
@patch("src.utils.llm.complete")
@pytest.mark.asyncio
async def test_s6_parallel_execution(mock_complete, mock_retrieve, mock_cfo, mock_librarian, tmp_path):
    """
    Verifies parallel node execution and state merging in the v4.0 graph using ainvoke.
    """
    # Agnostic Mocks
    mock_librarian.side_effect = lambda *args, **kwargs: args[0]
    mock_cfo.side_effect = lambda *args, **kwargs: args[0]

    # Mock LLM for all nodes
    def mock_llm_side_effect(*args, **kwargs):
        agent = kwargs.get("agent")
        if agent == "profiler":
            return '{"archetype": "High-D", "confidence": 95, "pinneo_cites": ["Control the narrative."]}'
        elif agent == "librarian":
            return '{"content_class": "OTHER", "deal_id": null}'
        elif agent == "cfo_p1":
            return '{}'
        return '{"verdict": "APPROVE", "confidence": 90, "reasoning_text": "A+", "scribe_instructions": "Draft"}'
        
    mock_complete.side_effect = mock_llm_side_effect
    
    # Mock Retriever
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
    conn.commit()
    conn.close()

    # 2. Setup Graph with Async Checkpointer
    db_path = tmp_path / "checkpoints.sqlite"
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as memory:
        graph = build_graph().compile(checkpointer=memory)
        config_dict = {"configurable": {"thread_id": "test_s6"}}

        # 3. Inject State
        initial_state = {
            "deal_id": "S6-DEAL",
            "address": "123 Parallel St",
            "parcel_number": "S6-TEST",
            "cfo_verified": True,
            "financials": {"calculated": True, "dscr": 1.2, "cap_rate": 0.08, "verified_financials_id": 999}
        }

        # Run the graph asynchronously
        result = await graph.ainvoke(initial_state, config_dict)

        # 4. Verify results
        assert result.get("verdict") == "APPROVE"

    cp_conn_cleanup = sqlite3.connect(str(db_path))
    cp_conn_cleanup.close()
