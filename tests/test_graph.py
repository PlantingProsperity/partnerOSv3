import pytest
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
import config
from src.graph.deal_graph import build_graph

def test_graph_compilation_and_interrupt(tmp_path):
    # Setup temporary checkpoint database
    db_path = tmp_path / "checkpoints.sqlite"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    memory = SqliteSaver(conn)
    
    # Compile graph with checkpointer
    graph = build_graph().compile(checkpointer=memory)
    
    config = {"configurable": {"thread_id": "deal_123_test"}}
    
    # 1. Initial Invocation
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
    assert "calculated" not in result.get("financials", {})
    
    # 2. Resume Invocation (Simulate human verification)
    # We update the state to cfo_verified=True and resume from cfo_calculate
    resume_result = graph.invoke(
        Command(
            resume=True,
            update={"cfo_verified": True},
            goto="cfo_calculate"
        ), 
        config
    )
    
    # Should complete the graph
    assert "calculated" in resume_result.get("financials", {})
    assert resume_result.get("seller_archetype") == "High-S"
    assert resume_result.get("verdict") == "APPROVE"
    
    conn.close()
