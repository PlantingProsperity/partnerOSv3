"""
pipeline_driver.py — The Mass Execution Engine for PartnerOS.

Iterates through the prospects database and runs the full 
'A+ or Death' pipeline (Scout -> Manager -> Scribe) for every lead.
"""

import time
import json
from src.database.db import get_connection
from src.graph.nodes.scout import scout_node
from src.graph.nodes.manager import manager_node
from src.graph.state import DealState
from src.utils.logger import get_logger
import config

log = get_logger("firehouse.pipeline_driver")

def run_mass_pipeline(batch_size: int = 10):
    """
    Processes a batch of IDENTIFIED prospects.
    """
    log.info("starting_mass_pipeline_run", batch_size=batch_size)
    
    conn = get_connection()
    # Fetch identified leads, longest hold first
    leads = conn.execute("""
        SELECT id, address, parcel_number, hold_years 
        FROM prospects 
        WHERE pipeline_stage = 'IDENTIFIED' 
        AND source = 'CLARK_COUNTY_GIS'
        ORDER BY hold_years DESC LIMIT ?
    """, (batch_size,)).fetchall()
    
    if not leads:
        log.info("no_leads_ready_for_processing")
        conn.close()
        return

    processed_count = 0
    for lead in leads:
        deal_id = f"auto_{lead['parcel_number']}"
        address = lead['address']
        
        log.info("processing_lead", address=address, deal_id=deal_id)
        
        try:
            # 1. Initialize State
            state = DealState(
                deal_id=deal_id,
                address=address,
                parcel_number=lead['parcel_number'],
                status='INTAKE',
                financials={'dscr': 0.85}, # Test Baseline: Assume distress until proven otherwise
                property_data={'hold_years': lead['hold_years']}
            )
            
            # 2. Satisfy DB Context (Explicit Transaction)
            # We use a new connection here to avoid reuse lock issues
            deal_conn = get_connection()
            deal_conn.execute("BEGIN IMMEDIATE")
            deal_conn.execute("""
                INSERT OR IGNORE INTO deals (deal_id, address, address_slug, jacket_path, thread_id, created_at, updated_at) 
                VALUES (?, ?, ?, '/deals/auto', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (deal_id, address, deal_id, f"thread_{deal_id}"))
            deal_conn.commit()
            deal_conn.close()
            
            # 3. Step 1: Scout Intelligence
            scout_out = scout_node(state)
            state.update(scout_out)
            
            # 4. Step 2: Managerial Verdict
            verdict_out = manager_node(state)
            state.update(verdict_out)
            
            # 5. Step 3: Update Prospect Pipeline Stage
            update_conn = get_connection()
            update_conn.execute("BEGIN IMMEDIATE")
            final_stage = 'VERIFIED' if state['verdict'] == 'APPROVE' else 'KILLED'
            update_conn.execute("UPDATE prospects SET pipeline_stage = ? WHERE id = ?", (final_stage, lead['id']))
            update_conn.commit()
            update_conn.close()
            
            log.info("lead_processed", address=address, verdict=state['verdict'])
            processed_count += 1
            
            # 6. Batch Spacing (Cool-down for DB/API)
            time.sleep(2.0)
            
        except Exception as e:
            log.error("lead_processing_failed", address=address, error=str(e))
            continue

    conn.close()
    log.info("mass_pipeline_batch_complete", count=processed_count)

if __name__ == "__main__":
    # Process 10 leads at a time to stay within budget/latency goals
    run_mass_pipeline(batch_size=10)
