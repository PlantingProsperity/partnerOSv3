import pytest
import sqlite3
import asyncio
from unittest.mock import patch, MagicMock
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from src.graph.deal_graph import build_graph
from src.database.db import get_connection

@patch("src.graph.deal_graph.librarian_node_wrapper")
@patch("src.graph.deal_graph.cfo_extract_node")
@patch("src.graph.deal_graph.scout_node_wrapper")
@patch("src.graph.deal_graph.profiler_node")
@patch("src.graph.deal_graph.explorer_node")
@patch("src.graph.deal_graph.deal_architect_node")
@patch("src.graph.deal_graph.risk_sentinel_node")
@patch("src.graph.deal_graph.manager_node")
@patch("src.graph.deal_graph.scribe_node")
@pytest.mark.asyncio
async def test_scribe_routing_approve(mock_scribe, mock_manager, mock_sentinel, mock_architect, mock_explorer, mock_profiler, mock_scout, mock_cfo, mock_librarian, tmp_path):
    """
    Verifies that the graph correctly routes to the Scribe node on APPROVE verdict using ainvoke.
    """
    # Agnostic Mocks
    mock_librarian.side_effect = lambda *args, **kwargs: {}
    mock_cfo.side_effect = lambda *args, **kwargs: {}
    mock_scout.side_effect = lambda *args, **kwargs: {}
    mock_profiler.side_effect = lambda *args, **kwargs: {}
    mock_explorer.side_effect = lambda *args, **kwargs: {}
    mock_architect.side_effect = lambda *args, **kwargs: {}
    mock_sentinel.side_effect = lambda *args, **kwargs: {}
    
    # Manager mocks APPROVE verdict
    mock_manager.side_effect = lambda *args, **kwargs: {"verdict": "APPROVE", "scribe_instructions": "Draft LOI"}
    
    # Scribe mocks draft
    mock_scribe.side_effect = lambda *args, **kwargs: {"loi_draft": "# Letter of Intent\n\nWe offer $1M."}
    
    # Setup Checkpointer
    db_path = tmp_path / "checkpoints.sqlite"
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as memory:
        graph = build_graph().compile(checkpointer=memory)
        config_dict = {"configurable": {"thread_id": "test_s8_approve"}}
        
        initial_state = {
            "deal_id": "S8-DEAL-APP",
            "cfo_verified": True,
            "financials": {"calculated": True, "dscr": 1.5, "cap_rate": 0.08}
        }
        
        # Run graph
        result = await graph.ainvoke(initial_state, config_dict)
        
        # Verify it hit the Scribe
        assert result["verdict"] == "APPROVE"
        assert "We offer $1M" in result.get("loi_draft", "")
        assert mock_scribe.called

@patch("src.graph.deal_graph.librarian_node_wrapper")
@patch("src.graph.deal_graph.cfo_extract_node")
@patch("src.graph.deal_graph.scout_node_wrapper")
@patch("src.graph.deal_graph.profiler_node")
@patch("src.graph.deal_graph.explorer_node")
@patch("src.graph.deal_graph.deal_architect_node")
@patch("src.graph.deal_graph.risk_sentinel_node")
@patch("src.graph.deal_graph.manager_node")
@patch("src.graph.deal_graph.scribe_node")
@pytest.mark.asyncio
async def test_scribe_routing_kill(mock_scribe, mock_manager, mock_sentinel, mock_architect, mock_explorer, mock_profiler, mock_scout, mock_cfo, mock_librarian, tmp_path):
    """
    Verifies that the graph correctly skips the Scribe node on KILL verdict using ainvoke.
    """
    # Agnostic Mocks
    mock_librarian.side_effect = lambda *args, **kwargs: {}
    mock_cfo.side_effect = lambda *args, **kwargs: {}
    mock_scout.side_effect = lambda *args, **kwargs: {}
    mock_profiler.side_effect = lambda *args, **kwargs: {}
    mock_explorer.side_effect = lambda *args, **kwargs: {}
    mock_architect.side_effect = lambda *args, **kwargs: {}
    mock_sentinel.side_effect = lambda *args, **kwargs: {}
    
    # Manager mocks KILL verdict
    mock_manager.side_effect = lambda *args, **kwargs: {"verdict": "KILL", "scribe_instructions": "No deal"}
    
    # Setup Checkpointer
    db_path = tmp_path / "checkpoints.sqlite"
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as memory:
        graph = build_graph().compile(checkpointer=memory)
        config_dict = {"configurable": {"thread_id": "test_s8_kill"}}
        
        initial_state = {
            "deal_id": "S8-DEAL-KILL",
            "cfo_verified": True,
            "financials": {"calculated": True, "dscr": 0.5, "cap_rate": 0.02}
        }
        
        # Run graph
        result = await graph.ainvoke(initial_state, config_dict)
        
        # Verify it skipped the Scribe
        assert result["verdict"] == "KILL"
        assert not mock_scribe.called
