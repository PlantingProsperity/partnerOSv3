from typing import Literal
from langgraph.graph import StateGraph, START, END
from src.graph.state import DealState
from src.graph.nodes.librarian import librarian_node
from src.graph.nodes.cfo import cfo_extract_node, cfo_calculate_node
from src.graph.nodes.pinneo_gate import pinneo_gate_node
from src.graph.nodes.scout import scout_node
from src.graph.nodes.profiler import profiler_node
from src.graph.nodes.manager import manager_node
from src.graph.nodes.scribe import scribe_node

def verify_gate(state: DealState) -> Literal["cfo_calculate", "__end__"]:
    """
    Conditional edge: routes to __end__ (interrupt) if CFO verification is pending.
    """
    if state.get("cfo_verified"):
        return "cfo_calculate"
    return "__end__"

def manager_router(state: DealState) -> Literal["scribe", "__end__"]:
    """
    Conditional edge: routes to Scribe if deal is APPROVED, else ends the graph.
    """
    if state.get("verdict") == "APPROVE":
        return "scribe"
    return "__end__"

def build_graph() -> StateGraph:
    builder = StateGraph(DealState)
    
    # Add nodes
    builder.add_node("librarian", librarian_node)
    builder.add_node("cfo_extract", cfo_extract_node)
    builder.add_node("cfo_calculate", cfo_calculate_node)
    builder.add_node("pinneo_gate", pinneo_gate_node)
    builder.add_node("scout", scout_node)
    builder.add_node("profiler", profiler_node)
    builder.add_node("manager", manager_node)
    builder.add_node("scribe", scribe_node)
    
    # Edges
    builder.add_edge(START, "librarian")
    builder.add_edge("librarian", "cfo_extract")
    
    # Interrupt Edge
    builder.add_conditional_edges(
        "cfo_extract",
        verify_gate,
        {
            "cfo_calculate": "cfo_calculate",
            "__end__": END
        }
    )
    
    builder.add_edge("cfo_calculate", "pinneo_gate")
    
    # Parallel Fan-out
    builder.add_edge("pinneo_gate", "scout")
    builder.add_edge("pinneo_gate", "profiler")
    
    # Fan-in
    builder.add_edge(["scout", "profiler"], "manager")
    
    # Verdict Routing
    builder.add_conditional_edges(
        "manager",
        manager_router,
        {
            "scribe": "scribe",
            "__end__": END
        }
    )
    
    builder.add_edge("scribe", END)
    
    return builder

# Compiled graph for import
deal_graph = build_graph().compile()
