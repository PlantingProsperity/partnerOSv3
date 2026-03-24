"""
deal_architect.py — Creative Structuring Agent (LangGraph Node)

Consumes Scout + Explorer output to propose elite Pinneo-aligned transaction structures.
Generates exactly 3 structures: Subject-To, Wrap, and Lease-Option.
"""

import json
from src.graph.state import DealState
from src.utils.logger import get_logger
from src.utils import llm
from src.utils.parser import extract_json

log = get_logger("agent.deal_architect")

def deal_architect_node(state: DealState) -> dict:
    """
    LangGraph node for creative deal structuring.
    """
    address = state.get("address")
    financials = state.get("financials", {})
    property_data = state.get("property_data", {})
    market_signals = state.get("market_signals", {})
    
    log.info("executing_deal_architect", address=address)
    
    # 1. Formulate Design Prompt
    prompt = f"""
    You are the Lead Deal Architect for Fasahov Bros. Brokerage.
    Based on the following property intelligence and market signals, design exactly THREE 
    creative transaction engineering structures following the Greg Pinneo doctrine.
    
    PROPERTY: {address}
    FINANCIALS: {json.dumps(financials)}
    SIGNALS: {json.dumps(market_signals)}
    
    REQUIRED STRUCTURES:
    1. SUBJECT-TO (Existing financing preservation)
    2. THE WRAP (Equity arbitrage)
    3. LEASE-OPTION (Low-capital infill control)
    
    For each structure, provide:
    - Name
    - Strategy (Pinneo alignment)
    - Key Terms (Rate, Term, Payment)
    - NIM Confidence Score (0.0 to 1.0)
    
    Output strictly in JSON.
    """
    
    # 2. Call NVIDIA NIM
    log.info("calling_nvidia_nim_for_structure_design")
    response = llm.complete(prompt, agent="manager") # Re-using Manager model for architecture
    
    data = extract_json(response)
    
    return {"proposed_structures": data.get("structures", []) if isinstance(data, dict) else []}
