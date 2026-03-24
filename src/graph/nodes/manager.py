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
    
    # 1. Build context-rich prompt
    # Panoramic Intelligence: Using the high-signal extraction from the Scout
    signals = property_data.get('panoramic_signals', {})
    
    prompt = f"""
    You are the Managing Partner of Fasahov Bros. Brokerage. 
    Your role is to protect the firm's capital and time. 
    Issue a strategic verdict for: {state.get("address")}
    
    SYSTEM MANTRA: Unless it proves to be an A+ all around, a deal dies and we move on to the next hunt.
    
    --- STRATEGIC GIS SIGNALS ---
    - Units: {signals.get('units')}
    - Building Condition: {signals.get('building_condition')}
    - Neighborhood Market: {signals.get('neighborhood_market')}
    - Demographic Load (PPH): {signals.get('persons_per_household')}
    - Jurisdiction: {signals.get('jurisdiction')}
    - Tax Load: ${signals.get('tax_amount')}
    
    --- DEAL FINANCIALS ---
    - DSCR: {financials.get("dscr")}
    - Cap Rate: {financials.get("cap_rate")}
    - Seller Archetype: {archetype}
    
    --- DISCIPLINED DIRECTIVE ---
    You are an Elite Filter. We only pursue 'A+' opportunities.
    
    CRITERIA FOR 'APPROVE':
    1. Financials: DSCR must be healthy or have a CRYSTAL CLEAR 'Rescue' path that guarantees A+ returns.
    2. Condition: Building condition must not be a 'Money Pit' unless the land value is anomalous.
    3. Sentiment: Seller must show high motivation (long hold or tax issues).
    
    If ANY category is mediocre or 'B-grade', the verdict MUST be 'KILL'. 
    We do not settle for average deals. If you KILL it, explain exactly why it failed the A+ standard.
    
    Output strictly in JSON format.
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

        # Flexible JSON Parsing: Using the new robust extraction utility
        from src.utils.parser import extract_json
        data = extract_json(response_str)
        
        if not data:
            log.error("manager_json_extraction_failed", deal_id=deal_id, snippet=response_str[:100])
            return {"verdict": "ERROR", "status": "UNDER_REVIEW"}

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
            INSERT INTO verdicts (deal_id, verdict, confidence, reasoning_text, logic_tree, scribe_instructions, issued_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            deal_id, 
            str(verdict).upper(), 
            int(confidence), 
            str(reasoning),
            None, # logic_tree logic replaced by UI-level heuristics
            str(instructions)
        ))
        conn.commit()
        conn.close()
        
        result = {
            "verdict": str(verdict).upper(),
            "manager_confidence": int(confidence),
            "reasoning_text": str(reasoning),
            "scribe_instructions": str(instructions),
            "status": "APPROVED" if str(verdict).upper() == "APPROVE" else "KILLED"
        }
        
        # --- Speculative Action (Phase 2 Optimization) ---
        if result["verdict"] == "APPROVE":
            import threading
            from src.graph.nodes.scribe import scribe_node
            
            def speculative_draft():
                try:
                    # Create a copy of state updated with Manager's results for the Scribe
                    spec_state = state.copy()
                    spec_state.update(result)
                    scribe_result = scribe_node(spec_state)
                    if "loi_draft" in scribe_result:
                        # Write speculative draft to DB or state cache if needed
                        log.info("speculative_draft_complete", deal_id=deal_id)
                except Exception as e:
                    log.error("speculative_draft_failed", deal_id=deal_id, error=str(e))
            
            # Fire and forget
            threading.Thread(target=speculative_draft, daemon=True).start()
            
        return result
        
    except Exception as e:
        log.error("manager_failed", deal_id=deal_id, error=str(e))
        return {"verdict": "ERROR", "status": "UNDER_REVIEW"}
