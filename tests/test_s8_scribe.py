import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from langgraph.checkpoint.sqlite import SqliteSaver
from src.graph.deal_graph import build_graph
from src.database.db import get_connection

@patch("src.graph.deal_graph.librarian_node")
@patch("src.graph.deal_graph.cfo_extract_node")
@patch("src.graph.deal_graph.scout_node")
@patch("src.graph.deal_graph.profiler_node")
@patch("src.graph.deal_graph.manager_node")
@patch("src.graph.deal_graph.scribe_node")
def test_scribe_routing_approve(mock_scribe, mock_manager, mock_profiler, mock_scout, mock_cfo, mock_librarian, tmp_path):
    # Mock pass-throughs
    mock_librarian.side_effect = lambda state: {}
    mock_cfo.side_effect = lambda state: {}
    mock_scout.side_effect = lambda state: {}
    mock_profiler.side_effect = lambda state: {}
    
    # Manager mocks APPROVE verdict state update
    mock_manager.side_effect = lambda state: {"verdict": "APPROVE", "scribe_instructions": "Draft LOI"}
    
    # Scribe mocks draft
    mock_scribe.side_effect = lambda state: {"loi_draft": "# Letter of Intent\n\nWe offer $1M."}
    
    # Setup Checkpointer
    db_path = tmp_path / "checkpoints.sqlite"
    cp_conn = sqlite3.connect(str(db_path), check_same_thread=False)
    memory = SqliteSaver(cp_conn)
    graph = build_graph().compile(checkpointer=memory)
    config = {"configurable": {"thread_id": "test_s8_approve"}}
    
    initial_state = {
        "deal_id": "S8-DEAL-APP",
        "cfo_verified": True,
        "financials": {"calculated": True, "dscr": 1.5, "cap_rate": 0.08}
    }
    
    # Run graph
    result = graph.invoke(initial_state, config)
    
    # Verify it hit the Scribe
    assert result["verdict"] == "APPROVE"
    assert "We offer $1M" in result.get("loi_draft", "")
    assert mock_scribe.called
    
    cp_conn.close()

@patch("src.graph.deal_graph.librarian_node")
@patch("src.graph.deal_graph.cfo_extract_node")
@patch("src.graph.deal_graph.scout_node")
@patch("src.graph.deal_graph.profiler_node")
@patch("src.graph.deal_graph.manager_node")
@patch("src.graph.deal_graph.scribe_node")
def test_scribe_routing_kill(mock_scribe, mock_manager, mock_profiler, mock_scout, mock_cfo, mock_librarian, tmp_path):
    # Mock pass-throughs
    mock_librarian.side_effect = lambda state: {}
    mock_cfo.side_effect = lambda state: {}
    mock_scout.side_effect = lambda state: {}
    mock_profiler.side_effect = lambda state: {}
    
    # Manager mocks KILL verdict
    mock_manager.side_effect = lambda state: {"verdict": "KILL", "scribe_instructions": "No deal"}
    
    # Setup Checkpointer
    db_path = tmp_path / "checkpoints.sqlite"
    cp_conn = sqlite3.connect(str(db_path), check_same_thread=False)
    memory = SqliteSaver(cp_conn)
    graph = build_graph().compile(checkpointer=memory)
    config = {"configurable": {"thread_id": "test_s8_kill"}}
    
    initial_state = {
        "deal_id": "S8-DEAL-KILL",
        "cfo_verified": True,
        "financials": {"calculated": True, "dscr": 0.5, "cap_rate": 0.02}
    }
    
    # Run graph
    result = graph.invoke(initial_state, config)
    
    # Verify it skipped the Scribe
    assert result["verdict"] == "KILL"
    assert result.get("loi_draft") is None or result.get("loi_draft") == ""
    assert not mock_scribe.called
    
    cp_conn.close()
