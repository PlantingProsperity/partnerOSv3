from src.graph.state import DealState
from src.utils.logger import get_logger

log = get_logger("agent.profiler")

def profiler_node(state: DealState) -> dict:
    """
    Analyzes seller archetype based on context.
    """
    log.info("executing_profiler", deal_id=state.get("deal_id"))
    return {"seller_archetype": "High-S"}
