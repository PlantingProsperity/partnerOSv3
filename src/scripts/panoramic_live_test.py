import json
import time
from src.graph.nodes.scout import scout_node
from src.graph.nodes.manager import manager_node
from src.graph.state import DealState
from src.database.db import get_connection

def run_panoramic_test():
    print("\n" + "="*60)
    print("🚀 STARTING PANORAMIC INTELLIGENCE LIVE TEST")
    print("="*60)

    target_address = "716 E MCLOUGHLIN BLVD"
    deal_id = f"panoramic_{int(time.time())}"
    
    # 1. Database Setup
    conn = get_connection()
    conn.execute("""
        INSERT INTO deals (deal_id, address, address_slug, jacket_path, thread_id, created_at, updated_at) 
        VALUES (?, ?, 'panoramic-test', '/dummy', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (deal_id, target_address, f"thread_{deal_id}"))
    conn.commit()

    # 2. Scout Node: Exhaustive Ingest
    print(f"\n[Phase 1] Scout: Harvesting Exhaustive GIS Metadata...")
    state = DealState(
        deal_id=deal_id,
        address=target_address,
        parcel_number="41550000",
        status='UNDER_REVIEW',
        financials={'dscr': 0.85}, # Force a rescue scenario
        property_data={}
    )
    
    scout_out = scout_node(state)
    state.update(scout_out)
    
    raw_data = state['property_data'].get('raw_gis_json')
    if raw_data:
        print(f" ✅ SUCCESS: Ingested {len(json.loads(raw_data))} raw attribute fields.")
    else:
        print(" ❌ FAILED: Raw GIS data not captured.")
        return

    # 3. Manager Node: Panoramic Forensics
    print("\n[Phase 2] Manager: Performing Panoramic Data Forensics (NVIDIA Ultra 253B)...")
    verdict = manager_node(state)
    
    print("\n" + "-"*40)
    print("💎 MANAGER'S PANORAMIC VERDICT")
    print("-"*40)
    print(f"Verdict: {verdict.get('verdict')}")
    print(f"Confidence: {verdict.get('manager_confidence')}%")
    print("\nStrategic Pattern Matching:")
    print(verdict.get('reasoning_text'))
    
    print("\n" + "="*60)
    print("🏆 PANORAMIC TEST COMPLETE")
    print("="*60 + "\n")
    conn.close()

if __name__ == "__main__":
    run_panoramic_test()
