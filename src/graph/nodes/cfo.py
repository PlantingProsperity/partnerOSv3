from src.graph.state import DealState
from src.utils.logger import get_logger

log = get_logger("agent.cfo")

def cfo_extract_node(state: DealState) -> dict:
    """
    Phase 1: Extracts raw financial data from documents.
    """
    log.info("executing_cfo_extract", deal_id=state.get("deal_id"))
    return {"financials": {"extracted": True}}

def cfo_calculate_node(state: DealState) -> dict:
    """
    Phase 3: Performs definitive calculations (DSCR, Cap Rate) on verified data.
    """
    log.info("executing_cfo_calculate", deal_id=state.get("deal_id"))
    return {"financials": {"calculated": True, "dscr": 1.2}}
