from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator

def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively deep merges two dictionaries. 
    Nested dictionaries are merged rather than overwritten.
    """
    res = a.copy()
    for k, v in b.items():
        if k in res and isinstance(res[k], dict) and isinstance(v, dict):
            res[k] = merge_dicts(res[k], v)
        else:
            res[k] = v
    return res

def merge_lists(a: List[Any], b: List[Any]) -> List[Any]:
    """Combines two lists via simple concatenation. Safely handles None values."""
    return (a or []) + (b or [])

class DealState(TypedDict):
    """
    The permanent state object that flows through the LangGraph pipeline.
    """
    deal_id: str
    address: str
    parcel_number: Optional[str]
    status: str  # 'INTAKE', 'UNDER_REVIEW', 'APPROVED', 'KILLED'
    
    # ── Routing Flags ──
    cfo_verified: bool
    heuristic_flagged: bool
    heuristic_failures: List[str]
    
    # ── Agent Payloads ──
    financial_doc_paths: List[str]
    # Annotated with a merge function so agents can update specific keys 
    # without overwriting the entire dictionary.
    financials: Annotated[Dict[str, Any], merge_dicts]
    property_data: Annotated[Dict[str, Any], merge_dicts]
    seller_archetype: str
    profiler_confidence: int
    profiler_cites: List[str]
    
    # Final Output
    verdict: str
    reasoning_text: str
    manager_confidence: int
    scribe_instructions: str
    loi_draft: str
    speculative_drafts: Annotated[dict, merge_dicts]
    market_signals: Annotated[dict, merge_dicts]
    proposed_structures: Annotated[list, merge_lists]
    risk_monte_carlo: Annotated[dict, merge_dicts]
