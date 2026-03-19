from src.graph.state import DealState
from src.utils.logger import get_logger

log = get_logger("agent.librarian")

def librarian_node(state: DealState) -> dict:
    """
    Initializes the state and routes incoming documents.
    """
    log.info("executing_librarian", deal_id=state.get("deal_id"))
    return {"status": "UNDER_REVIEW"}
