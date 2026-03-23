from pydantic import BaseModel, Field
import json
from src.graph.state import DealState
from src.utils.logger import get_logger
from src.utils import llm
from src.database.db import get_connection

log = get_logger("agent.manager")

class ManagerVerdict(BaseModel):
    verdict: str = Field(
        description="Strictly 'APPROVE' or 'KILL'",
        validation_alias="decision"
    )
    confidence: int = Field(
        description="Confidence score from 0 to 100",
        validation_alias="confidence_level"
    )
    reasoning_text: str = Field(
        description="The analytical reasoning behind the verdict.",
        validation_alias="justification"
    )
    scribe_instructions: str = Field(
        description="If APPROVE, provide detailed bullet points for the Scribe on how to draft the LOI (terms, tone, seller-financing structure). If KILL, provide a brief summary of why.",
        validation_alias="instructions"
    )

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
        import re
        # 2. Call LLM
        response_str = llm.complete(
            prompt=prompt,
            tier="quality",
            agent="manager",
            deal_id=deal_id,
            response_format=ManagerVerdict
        )
        
        if not response_str:
            log.error("manager_received_empty_response", deal_id=deal_id)
            return {"verdict": "ERROR", "status": "UNDER_REVIEW"}

        # Aggressive JSON Extraction (ADR-006 Hardening)
        json_match = re.search(r"(\{.*\})", response_str, re.DOTALL)
        if json_match:
            response_str = json_match.group(1)
        
        # Additional cleanup
        response_str = response_str.replace("```json", "").replace("```", "").strip()
        
        # Flexible JSON Parsing: NVIDIA models often hallucinate key names or nesting
        data = json.loads(response_str)
        
        verdict = data.get("verdict") or data.get("decision") or "KILL"
        confidence = data.get("confidence") or data.get("confidence_level") or 0
        
        # Handle cases where reasoning/instructions might be nested objects or lists
        reasoning = data.get("reasoning_text") or data.get("justification") or data.get("reasoning")
        if isinstance(reasoning, (dict, list)):
            reasoning = json.dumps(reasoning, indent=2)
        elif not reasoning:
            reasoning = "No reasoning provided."
            
        instructions = data.get("scribe_instructions") or data.get("instructions")
        if isinstance(instructions, (dict, list)):
            instructions = json.dumps(instructions, indent=2)
        elif not instructions:
            instructions = ""
        
        # 3. Write to SQLite
        conn = get_connection()
        conn.execute("""
            INSERT INTO verdicts (deal_id, verdict, confidence, reasoning_text, scribe_instructions, issued_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            deal_id, 
            str(verdict).upper(), 
            int(confidence), 
            str(reasoning), 
            str(instructions)
        ))
        conn.commit()
        conn.close()
        
        return {
            "verdict": str(verdict).upper(),
            "manager_confidence": int(confidence),
            "reasoning_text": str(reasoning),
            "scribe_instructions": str(instructions),
            "status": "APPROVED" if str(verdict).upper() == "APPROVE" else "KILLED"
        }
        
    except Exception as e:
        log.error("manager_failed", deal_id=deal_id, error=str(e))
        return {"verdict": "ERROR", "status": "UNDER_REVIEW"}
