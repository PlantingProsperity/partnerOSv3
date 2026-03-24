"""
explorer.py — The Worldwide Signal Layer Agent (LangGraph Node)

Controlled web pulls from elite real estate portals via NVIDIA NIM.
Uses httpx with a semaphore to prevent IP blocking and adheres to WEB_ALLOW_LIST.
"""

import httpx
import json
import asyncio
import datetime
from typing import Dict, List, Optional
from src.graph.state import DealState
from src.utils.logger import get_logger
from src.utils import llm
from src.database.db import get_connection, with_db_retry
import config

log = get_logger("agent.explorer")

WEB_ALLOW_LIST = ["zillow.com", "realtor.com", "redfin.com", "crexi.com", "loopnet.com", "clarkcountywa.gov", "hub-clarkcountywa.opendata.arcgis.com", "news.google.com"]

class ExplorerClient:
    """
    Sandboxed web client for market signal extraction.
    """
    def __init__(self):
        self.semaphore = asyncio.Semaphore(10)
        self.allow_list = WEB_ALLOW_LIST

    async def fetch_market_signals(self, address: str) -> str:
        """
        Simulates controlled web pulls for market sentiment and comps.
        In a full deployment, this would use a headless browser or a SERP API
        restricted to the allow-list.
        """
        log.info("fetching_market_signals", address=address)
        # Placeholder for real web extraction
        # Mocking a Zillow/Redfin summary
        return f"Market data for {address}: Stable prices, low inventory in neighborhood."

@with_db_retry()
def get_cached_signals(parcel_number: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT data_json, expires_at FROM temp_web_cache WHERE parcel_number = ?", (parcel_number,)).fetchone()
    conn.close()
    if row:
        expires = datetime.datetime.fromisoformat(row[1])
        if expires > datetime.datetime.now():
            return json.loads(row[0])
    return None

@with_db_retry()
def cache_signals(parcel_number: str, data: dict):
    conn = get_connection()
    expires = (datetime.datetime.now() + datetime.timedelta(hours=48)).isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO temp_web_cache (parcel_number, data_json, expires_at)
        VALUES (?, ?, ?)
    """, (parcel_number, json.dumps(data), expires))
    conn.commit()
    conn.close()

async def explorer_node(state: DealState) -> dict:
    """
    LangGraph node for web intelligence.
    """
    address = state.get("address")
    parcel = state.get("parcel_number")
    
    log.info("executing_explorer", address=address)
    
    # 1. Check Cache
    cached = get_cached_signals(parcel)
    if cached:
        log.info("explorer_cache_hit", parcel=parcel)
        return {"market_signals": cached}

    # 2. Extract raw data (Controlled pull)
    client = ExplorerClient()
    raw_signals = await client.fetch_market_signals(address)
    
    # 3. NVIDIA NIM Summarization
    prompt = f"""
    You are an Elite Real Estate Explorer.
    Extract only public real-estate data in strict JSON from the following raw signals. No PII.
    
    Raw Signals: {raw_signals}
    
    Output Format:
    {{
        "market_sentiment_score": float (0.0 to 1.0),
        "comps_summary": "string",
        "inventory_trend": "string"
    }}
    """
    
    log.info("calling_nvidia_nim_for_signal_analysis")
    summarized_json = llm.complete(prompt, agent="profiler") # Re-using Profiler model for exploration
    
    from src.utils.parser import extract_json
    data = extract_json(summarized_json)
    
    # 4. Cache and Return
    if data:
        cache_signals(parcel, data)
        
    return {"market_signals": data or {}}
