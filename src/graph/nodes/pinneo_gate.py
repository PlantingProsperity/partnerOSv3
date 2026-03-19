import config
from src.graph.state import DealState
from src.utils.logger import get_logger

log = get_logger("agent.pinneo_gate")

def pinneo_gate_node(state: DealState) -> dict:
    """
    Pure Python heuristics check against financial thresholds.
    This node evaluates the DealState WITHOUT using an LLM.
    """
    deal_id = state.get("deal_id")
    log.info("executing_pinneo_gate", deal_id=deal_id)
    
    failures = []
    financials = state.get("financials", {})
    
    # Check DSCR
    dscr = financials.get("dscr")
    if dscr is not None and dscr < config.CFO_DSCR_FLOOR:
        failures.append(
            f"DSCR {dscr:.2f} is below the floor of {config.CFO_DSCR_FLOOR}. "
            f"Annual debt service exceeds Pinneo's minimum safety threshold."
        )
        
    # Check Cap Rate
    cap_rate = financials.get("cap_rate")
    if cap_rate is not None and cap_rate < config.CFO_CAP_RATE_FLOOR:
        failures.append(
            f"Cap rate {cap_rate*100:.1f}% is below the floor of "
            f"{config.CFO_CAP_RATE_FLOOR*100:.0f}%. Property income insufficient at asking price."
        )

    flagged = len(failures) > 0
    if flagged:
        log.warning("pinneo_gate_flagged", deal_id=deal_id, failure_count=len(failures))

    return {
        "heuristic_failures": failures,
        "heuristic_flagged": flagged
    }
