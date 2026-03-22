from src.graph.state import DealState
from src.utils.logger import get_logger
from src.utils import llm

log = get_logger("agent.scribe")

def scribe_node(state: DealState) -> dict:
    """
    Drafts the final Letter of Intent (LOI) based strictly on Manager instructions.
    """
    deal_id = state.get("deal_id")
    log.info("executing_scribe", deal_id=deal_id)
    
    instructions = state.get("scribe_instructions", "")
    if not instructions:
        log.warning("scribe_no_instructions", deal_id=deal_id)
        return {"loi_draft": "No instructions provided."}
        
    prompt = f"""
    You are the Executive Scribe for Greg Pinneo.
    Draft a professional, persuasive Letter of Intent (LOI) or term sheet proposal based EXACTLY on the following instructions from the Managing Partner.
    Do NOT hallucinate financial terms. Use the exact numbers provided in the instructions.
    
    MANAGER INSTRUCTIONS:
    {instructions}
    
    Output the draft in clean Markdown format.
    """
    
    try:
        draft = llm.complete(
            prompt=prompt,
            tier="quality",
            agent="scribe",
            deal_id=deal_id
        )
        return {"loi_draft": draft}
    except Exception as e:
        log.error("scribe_failed", deal_id=deal_id, error=str(e))
        return {"loi_draft": f"[Scribe Error: {str(e)}]"}
