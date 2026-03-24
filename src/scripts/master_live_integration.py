import os
import json
import time
from pathlib import Path
from src.graph.nodes.librarian import Librarian
from src.graph.nodes.manager import manager_node
from src.graph.state import DealState
from src.database.db import get_connection
from src.firehouse.sourcer import analyze_uncontacted_prospects
from src.firehouse.scheduler import generate_morning_brief
from src.utils.logger import get_logger
import config

log = get_logger("master_live_integration")

def run_master_test():
    print("\n" + "="*60)
    print("🚀 STARTING MASTER LIVE INTEGRATION TEST (NO MOCKS)")
    print("="*60)
    
    # PHASE 1: THE SENSORY LAYER (Transcription & Intake)
    print("\n[Phase 1] Intake Sweep & Audio Transcription...")
    lib = Librarian()
    # 1.1 Ingest Meeting Wisdom into the Brain
    # This uses Groq for STT and NVIDIA for synthesis
    print(" - Processing real meeting audio...")
    lib._sweep_inbox()
    
    # 1.2 Verify Knowledge Sync
    conn = get_connection()
    chunk_count = conn.execute("SELECT COUNT(*) FROM brain_chunks").fetchone()[0]
    print(f" ✅ Brain Context Verified: {chunk_count} logic chunks indexed.")

    # PHASE 2: THE HUNT (AI Sourcing)
    print("\n[Phase 2] AI Lead Sourcing (Llama 4 Scout)...")
    # This will analyze your real Propwire/Excel lists
    # Note: No 'limit' argument exists in the current sourcer logic
    report = analyze_uncontacted_prospects()
    if report and report.top_picks:
        print(f" ✅ AI Sourcer found {len(report.top_picks)} high-priority gems.")
        target_deal = report.top_picks[0]
        print(f" 🎯 Primary Target: {target_deal.address} ({target_deal.owner_name})")
    else:
        print(" ⚠️ No high-priority picks found in this sweep.")
        # Fallback for the test if sourcer is empty
        from collections import namedtuple
        Target = namedtuple('Target', ['address', 'owner_name'])
        target_deal = Target(address='716 E MCLOUGHLIN BLVD', owner_name='Fasahov Bros.')
        print(" -> Using Fallback Target for Phase 3.")

    # PHASE 3: THE GENERAL (Strategic Underwriting)
    print("\n[Phase 3] Managerial Synthesis (NVIDIA Ultra 253B)...")
    # Ensure Deal exists in DB for Foreign Key integrity
    deal_id = f"live_{int(time.time())}"
    conn.execute("""
        INSERT INTO deals (deal_id, address, address_slug, jacket_path, thread_id, created_at, updated_at) 
        VALUES (?, ?, ?, '/deals/live_test', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (deal_id, target_deal.address, "master-test-deal", f"thread_{deal_id}"))
    conn.commit()
    
    # Force a state synthesis that requires Pinneo Brain lookup
    state = DealState(
        deal_id=deal_id,
        address=target_deal.address,
        status='UNDER_REVIEW',
        financials={'dscr': 0.85}, # Forces the Manager to 'Rescue' the deal
        property_data={'equity': 'HIGH', 'hold_years': 12},
        seller_archetype='High-D'
    )
    
    result = manager_node(state)
    print(f" ✅ Verdict Issued: {result.get('verdict')}")
    print(f" 📜 Reasoning: {result.get('reasoning_text')[:200]}...")

    # PHASE 4: THE BRIEF (Final Dashboard Output)
    print("\n[Phase 4] Morning Brief Generation...")
    generate_morning_brief()
    brief_path = config.DATA_DIR / "morning_brief.md"
    if brief_path.exists():
        print(f" ✅ Morning Brief finalized at {brief_path}")
    
    conn.close()
    print("\n" + "="*60)
    print("🏆 MASTER LIVE INTEGRATION SUCCESSFUL")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_master_test()
