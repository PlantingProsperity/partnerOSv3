from typing import List
from pydantic import BaseModel, Field
from src.graph.state import DealState
from src.utils.logger import get_logger
from src.utils import llm
from src.brain.retriever import retrieve

log = get_logger("agent.profiler")

class SellerProfile(BaseModel):
    archetype: str = Field(description="The primary DISC archetype: High-D, High-I, High-S, or High-C.")
    confidence: int = Field(description="Confidence score from 0 to 100.")
    pinneo_cites: List[str] = Field(description="Relevant quotes or wisdom from the Pinneo Brain used to make this determination.")

def profiler_node(state: DealState) -> dict:
    """
    Analyzes seller archetype based on context using Pinneo Brain RAG.
    """
    deal_id = state.get("deal_id")
    log.info("executing_profiler", deal_id=deal_id)
    
    try:
        # 1. Query the Brain
        brain_results = retrieve("seller psychology DISC archetype negotiation")
        brain_context = "\n\n".join([f"Source: {r.source_path}\n{r.text}" for r in brain_results])
        
        # 2. Build the Prompt (In a real run, we'd include transcript_paths here)
        prompt = f"""
        You are a commercial real estate profiler trained in the Greg Pinneo doctrine.
        Analyze the seller for Deal {deal_id} and determine their DISC archetype.
        
        Pinneo Wisdom Context:
        {brain_context}
        
        Determine if they are High-D (Dominant), High-I (Influential), High-S (Steady), or High-C (Compliant).
        """
        
        import json
        
        # 3. Call LLM with Structured Output
        response_str = llm.complete(
            prompt=prompt,
            tier="fast",
            agent="profiler",
            deal_id=deal_id,
            response_format=SellerProfile
        )
        
        profile = SellerProfile.model_validate_json(response_str)
        
        return {
            "seller_archetype": profile.archetype,
            "profiler_confidence": profile.confidence,
            "profiler_cites": profile.pinneo_cites
        }
        
    except Exception as e:
        log.error("profiler_failed", deal_id=deal_id, error=str(e))
        return {"seller_archetype": "UNKNOWN"}
