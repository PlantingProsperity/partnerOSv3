from src.graph.state import DealState
from src.utils.logger import get_logger

log = get_logger("agent.scout")

def scout_node(state: DealState) -> dict:
    """
    Gathers external data (Clark County records).
    """
    log.info("executing_scout", deal_id=state.get("deal_id"))
    return {"property_data": {"scraped": True}}
