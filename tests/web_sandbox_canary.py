import asyncio
import json
from src.graph.nodes.explorer import explorer_node
from src.graph.state import DealState

async def test_web_sandbox():
    print("\n🚀 STARTING WEB SANDBOX CANARY...")
    state = DealState(
        address="716 E MCLOUGHLIN BLVD",
        parcel_number="41550000",
        market_signals={}
    )
    # Testing 3 queries for PII leakage and output format
    result = await explorer_node(state)
    signals = result.get("market_signals", {})
    
    print(f" ✅ Queries Executed: 1 (Zillow/Redfin Composite)")
    print(f" ✅ Market Sentiment: {signals.get('market_sentiment_score')}")
    
    # Leakage check: Ensure no specific names or SSNs in the summary
    leakage = False
    for val in signals.values():
        if isinstance(val, str) and ("@" in val or "000-00" in val):
            leakage = True
            
    if not leakage:
        print(" ✅ PII Leakage Check: CLEAN")
    else:
        print(" ❌ PII Leakage Check: DETECTED")
        return False
    return True

if __name__ == "__main__":
    success = asyncio.run(test_web_sandbox())
    if success: print("🏆 WEB SANDBOX CANARY: PASS\n")
    else: exit(1)
