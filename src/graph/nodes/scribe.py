from src.graph.state import DealState
from src.utils.logger import get_logger
from src.utils import llm
from src.brain.retriever import retrieve

log = get_logger("agent.scribe")

def scribe_node(state: DealState) -> dict:
    """
    Drafts the final Letter of Intent (LOI) based on Manager instructions,
    using RAG to pull authentic templates and "voice" from the Pinneo Brain.
    """
    deal_id = state.get("deal_id")
    log.info("executing_scribe", deal_id=deal_id)
    
    instructions = state.get("scribe_instructions", "")
    if not instructions:
        log.warning("scribe_no_instructions", deal_id=deal_id)
        return {"loi_draft": "No instructions provided."}
        
    # 1. RAG: Pull authentic templates and meeting "voice"
    style_query = "Letter of intent template bird letter format Roman Fasahov voice professional real estate"
    style_chunks = retrieve(style_query, top_k=3)
    style_context = "\n\n".join([f"Source: {c.source_path}\n{c.text}" for c in style_chunks])

    prompt = f"""
    You are the Executive Scribe for Fasahov Bros. Brokerage.
    Your goal is to draft a professional, persuasive Letter of Intent (LOI) that sounds exactly like Roman or Daniil Fasahov.
    
    STYLE REFERENCE (Use this for tone and formatting):
    {style_context}
    
    MANAGER STRATEGY (Mandatory terms to include):
    {instructions}
    
    CONSTRAINTS:
    - Do NOT hallucinate financial terms. Use exact numbers from the Manager.
    - Keep the tone authoritative but collaborative ("Partnership Exit" style).
    - Output in clean Markdown.
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
