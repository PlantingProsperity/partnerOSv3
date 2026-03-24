import json
import time
from src.graph.nodes.scout import scout_node
from src.graph.state import DealState
from src.database.db import get_connection

def run_shadow_scan():
    print("\n" + "="*60)
    print("🚀 STARTING LIVE SHADOW INTELLIGENCE SCAN")
    print("="*60)

    # 1. Select a high-stakes target
    # 716 E MCLOUGHLIN BLVD is a known commercial landmark in Vancouver
    target_address = "716 E MCLOUGHLIN BLVD"
    deal_id = f"shadow_scan_{int(time.time())}"
    
    print(f"\n[Phase 1] Initializing Deal: {target_address}")
    
    # Ensure Deal exists for FK integrity
    conn = get_connection()
    conn.execute("""
        INSERT INTO deals (deal_id, address, address_slug, jacket_path, thread_id, created_at, updated_at) 
        VALUES (?, ?, 'shadow-scan', '/dummy', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (deal_id, target_address, f"thread_{deal_id}"))
    conn.commit()
    
    state = DealState(
        deal_id=deal_id,
        address=target_address,
        parcel_number="41550000",
        status='UNDER_REVIEW',
        financials={},
        property_data={}
    )

    # 2. Trigger the Scout Node (Tier 1 + Shadow)
    print("\n[Phase 2] Executing Scout Node (Shadow Intelligence Suite)...")
    result = scout_node(state)
    
    data = result.get("property_data", {})
    
    print("\n" + "-"*40)
    print("💎 SHADOW INTELLIGENCE REPORT")
    print("-"*40)
    print(f"📍 Address: {target_address}")
    print(f"📊 Hold Years: {data.get('hold_years')}")
    print(f"🏗️ Zoning: {data.get('zoning')}")
    print(f"💰 Mkt Value: ${data.get('mkt_tot_val', 0):,.0f}")
    
    print(f"\n🔍 SECRET SIGNALS:")
    print(f"   - Redevelopment Score: {data.get('redevelopment_score', 'NONE')}")
    print(f"   - Last Inspection: {data.get('last_physical_inspection', 'N/A')}")
    
    print(f"\n📡 SHADOW PIPELINE (Proposed Neighbors):")
    pipeline = data.get("shadow_pipeline", [])
    if pipeline:
        for project in pipeline:
            print(f"   - {project.get('MarketingName') or 'Unnamed'}: {project.get('Description')}")
            print(f"     Status: {project.get('StatusDescription')} | Units: {project.get('NumberOfBuildings')}")
    else:
        print("   - No proposed developments within 500ft.")

    print(f"\n📐 BUILDABLE TRUTH (VBLM):")
    print(f"   - Net Buildable Acres: {data.get('vblm_net_acres', 'N/A')}")
    print(f"   - Utilization Category: {data.get('vblm_category', 'N/A')}")
    print(f"   - Environmental Constraints: {'YES' if data.get('vblm_constrained') else 'NO'}")

    conn.close()
    print("\n" + "="*60)
    print("🏆 SHADOW SCAN COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_shadow_scan()
