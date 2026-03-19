from src.graph.state import DealState
from src.utils.logger import get_logger

log = get_logger("agent.manager")

def manager_node(state: DealState) -> dict:
    """
    Issues final verdict and generates LOI or rejection conditions.
    """
    log.info("executing_manager", deal_id=state.get("deal_id"))
    return {"verdict": "APPROVE"}
