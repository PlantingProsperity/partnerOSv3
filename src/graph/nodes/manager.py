from pydantic import BaseModel, Field
import json
from src.graph.state import DealState
from src.utils.logger import get_logger
from src.utils import llm
from src.database.db import get_connection

log = get_logger("agent.manager")

class ManagerVerdict(BaseModel):
    verdict: str = Field(description="Strictly 'APPROVE' or 'KILL'")
    confidence: int = Field(description="Confidence score from 0 to 100")
    reasoning_text: str = Field(description="The analytical reasoning behind the verdict.")
    scribe_instructions: str = Field(description="If APPROVE, provide detailed bullet points for the Scribe on how to draft the LOI (terms, tone, seller-financing structure). If KILL, provide a brief summary of why.")

def manager_node(state: DealState) -> dict:
    """
    Issues final verdict and generates Scribe instructions based on full state synthesis.
    """
    deal_id = state.get("deal_id")
    log.info("executing_manager", deal_id=deal_id)
    
    # 1. Synthesize State for the Prompt
    financials = state.get("financials", {})
    property_data = state.get("property_data", {})
    archetype = state.get("seller_archetype", "UNKNOWN")
    heuristic_failures = state.get("heuristic_failures", [])
    heuristic_flagged = state.get("heuristic_flagged", False)
    
    prompt = f"""
    You are the Managing Partner of a commercial real estate firm, operating on the Greg Pinneo doctrine.
    Review the following deal data and issue a final verdict (APPROVE or KILL).
    
    DEAL ID: {deal_id}
    ADDRESS: {state.get("address")}
    
    SELLER PSYCHOLOGY:
    Archetype: {archetype}
    
    FINANCIALS (Calculated):
    DSCR: {financials.get("dscr")}
    Cap Rate: {financials.get("cap_rate")}
    
    PROPERTY DATA:
    Zoning: {property_data.get("zoning")}
    Hold Years: {property_data.get("hold_years")}
    Tax Status: {property_data.get("tax_status")}
    
    HEURISTIC GATES:
    Flagged: {heuristic_flagged}
    Failures: {json.dumps(heuristic_failures)}
    """
    
    if heuristic_flagged:
        prompt += """
        IMPORTANT: The deal failed standard mathematical heuristics. As a Pinneo disciple, do NOT automatically KILL the deal. 
        Invent creative seller-financing conditions (e.g., lower interest, interest-only periods, balloon payments) that would successfully flip this deal into a safe, cash-flowing asset. Include these specific structural terms in the scribe_instructions.
        """
        
    try:
        # 2. Call LLM
        response_str = llm.complete(
            prompt=prompt,
            tier="quality",
            agent="manager",
            deal_id=deal_id,
            response_format=ManagerVerdict
        )
        
        verdict_data = ManagerVerdict.model_validate_json(response_str)
        
        # 3. Write to SQLite
        conn = get_connection()
        conn.execute("""
            INSERT INTO verdicts (deal_id, verdict, confidence, reasoning_text, scribe_instructions, issued_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            deal_id, 
            verdict_data.verdict, 
            verdict_data.confidence, 
            verdict_data.reasoning_text, 
            verdict_data.scribe_instructions
        ))
        conn.commit()
        conn.close()
        
        return {
            "verdict": verdict_data.verdict,
            "manager_confidence": verdict_data.confidence,
            "reasoning_text": verdict_data.reasoning_text,
            "scribe_instructions": verdict_data.scribe_instructions,
            "status": "APPROVED" if verdict_data.verdict == "APPROVE" else "KILLED"
        }
        
    except Exception as e:
        log.error("manager_failed", deal_id=deal_id, error=str(e))
        return {"verdict": "ERROR", "status": "UNDER_REVIEW"}
