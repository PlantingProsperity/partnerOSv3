"""
full_system_canary.py — End-to-End Strategic Validation

Simulates a complete deal through the elevated v4.0 pipeline.
Librarian -> Scout -> Explorer -> Architect -> Sentinel -> CFO Firewall.
"""

import asyncio
from src.graph.deal_graph import deal_graph
from src.graph.state import DealState
from src.utils.logger import get_logger

log = get_logger("tests.full_canary")

async def run_end_to_end_simulation():
    print("\n🚀 INITIALIZING FULL SYSTEM CANARY...")
    
    # 1. Setup Initial State
    state = DealState(
        deal_id="full_canary_001",
        address="716 E MCLOUGHLIN BLVD",
        parcel_number="41550000",
        status="INTAKE",
        cfo_verified=True, # Auto-verify for test
        financials={"dscr": 0.8, "asking_price": 1000000, "noi": 80000, "annual_debt_service": 100000},
        property_data={},
        market_signals={},
        proposed_structures=[],
        risk_monte_carlo={}
    )
    
    # 2. Execute Graph
    print(" - Executing Strategic Pipeline...")
    config = {"configurable": {"thread_id": "full_canary_test"}}
    
    # We skip librarian and cfo_extract nodes for this test to focus on logic flow
    # Starting from cfo_calculate
    try:
        final_state = await deal_graph.ainvoke(state, config)
        
        print("\n" + "="*40)
        print("💎 CANARY PIPELINE RESULTS")
        print("="*40)
        print(f"📍 Target: {final_state.get('address')}")
        print(f"🛡️ Risk Sentinel: {final_state.get('risk_monte_carlo', {}).get('risk_level')}")
        print(f"🧠 Architect Proposals: {len(final_state.get('proposed_structures', []))}")
        print(f"⚖️ Manager Verdict: {final_state.get('verdict')}")
        print("="*40 + "\n")
        
        return True
    except Exception as e:
        print(f"❌ PIPELINE ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_end_to_end_simulation())
    if success:
        print("🏆 FULL SYSTEM CANARY: PASS\n")
    else:
        print("💀 FULL SYSTEM CANARY: FAIL\n")
        exit(1)
