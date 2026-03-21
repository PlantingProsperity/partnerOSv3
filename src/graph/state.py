from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator

def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Merges two dictionaries, allowing updates to nested fields."""
    res = a.copy()
    res.update(b)
    return res

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
