import json
from typing import List, Optional
from pydantic import BaseModel, Field
from src.database.db import get_connection
from src.utils.logger import get_logger
from src.utils import llm

log = get_logger("firehouse.sourcer")

# ── Pydantic Schemas for AI Sourcer ───────────────────────────────────────────

class TargetProspect(BaseModel):
    parcel_number: str = Field(description="The exact parcel number of the prospect.")
    owner_name: str = Field(description="The owner's name.")
    address: str = Field(description="The property address.")
    reasoning: str = Field(description="A 2-3 sentence rationale explaining why this property indicates distress or high motivation based on the Pinneo doctrine.")
    suggested_strategy: str = Field(description="The specific negotiation or financing approach to take (e.g., 'Offer substitution of security', 'Pitch installment sale to avoid capital gains').")

class SourcerReport(BaseModel):
    top_picks: List[TargetProspect] = Field(description="The top 3-5 most promising prospects from the provided dataset.")

# ── Logic ─────────────────────────────────────────────────────────────────────

def analyze_uncontacted_prospects() -> Optional[SourcerReport]:
    """
    Pulls raw JSON records for uncontacted prospects and uses a large-context LLM 
    to surface the most promising targets based on the Pinneo doctrine.
    """
    conn = get_connection()
    # Pull up to 100 uncontacted prospects (this easily fits in Gemini's 2M window)
    rows = conn.execute("""
        SELECT parcel_number, raw_data 
        FROM prospects 
        WHERE pipeline_stage = 'IDENTIFIED' 
        ORDER BY created_at DESC 
        LIMIT 100
    """).fetchall()
    conn.close()
    
    if not rows:
        log.info("no_uncontacted_prospects_found")
        return None
        
    log.info("starting_prospect_sourcing", count=len(rows))
    
    # Construct the massive JSON payload
    prospect_data = []
    for row in rows:
        try:
            data = json.loads(row["raw_data"])
            # Ensure the LLM knows which parcel is which
            data["_system_parcel_number"] = row["parcel_number"]
            prospect_data.append(data)
        except Exception:
            pass
            
    payload = json.dumps(prospect_data, indent=2)
    
    prompt = f"""
    You are an expert commercial real estate sourcer trained in the Greg Pinneo doctrine.
    I am providing you with a raw JSON dump of {len(prospect_data)} properties from a Title Company.
    
    Analyze EVERY property and select the top 3-5 most promising targets for creative seller financing.
    
    PINNEO SOURCING HEURISTICS:
    1. Motivation Matrix (Age): Older owners (likely 60-70+) often want to downsize and want an income stream without management hassle. These are prime targets for Installment Sales to avoid massive capital gains taxes.
    2. Motivation Matrix (Hold Time): Target non-owner occupied properties owned for 10+ years. High equity is required to structure creative seller notes.
    3. Distress Indicators: Look for Delinquent Tax Status or extremely low assessed values compared to market, indicating deferred maintenance or financial stress.
    4. "All Cash" Myth: Sellers asking for all cash usually just need a specific amount of cash to buy something else (a boat, an RV, a smaller condo). The rest of their equity can be converted to terms.
    
    RAW PROPERTY DATA:
    {payload}
    
    Review the data and return the Top Picks using the requested schema.
    """
    
    try:
        # Use the system's configured QUALITY_MODEL (currently NVIDIA Llama 3.1 70B)
        # The payload is ~33k tokens, which easily fits in Llama's 128k context window.
        response_str = llm.complete(
            prompt=prompt,
            tier="quality",
            agent="prospect_sourcer",
            response_format=SourcerReport
        )
        
        report = SourcerReport.model_validate_json(response_str)
        
        log.info("prospect_sourcing_complete", picks=len(report.top_picks))
        return report
        
    except Exception as e:
        log.error("prospect_sourcing_failed", error=str(e))
        return None

if __name__ == "__main__":
    report = analyze_uncontacted_prospects()
    if report:
        print(report.model_dump_json(indent=2))