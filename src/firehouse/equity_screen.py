"""
equity_screen.py — Firehouse Equity Screening Job

Scheduled by APScheduler (daily or on-demand from UI).
Runs clark_county_api.run_equity_screen() and writes results to 
the prospects table for Morning Brief surfacing.
"""

import datetime
from src.database.db import get_connection
from src.integrations import clark_county_api
from src.utils.logger import get_logger
import config

log = get_logger("firehouse.equity_screen")

def run_firehouse_hunt():
    """
    The automated daily hunt for high-equity gems.
    1. Runs the Tier 1 REST screening.
    2. Upserts findings into prospects and property_records.
    """
    log.info("starting_firehouse_equity_hunt")
    
    try:
        # 1. Run the screen (Hold years >= 10, Multi-Family/Commercial)
        high_equity_leads = clark_county_api.run_equity_screen(
            property_types=['Multi-Family', 'Commercial', 'Industrial'],
            hold_years_min=10
        )
        
        log.info("equity_screen_complete", found_count=len(high_equity_leads))
        
        conn = get_connection()
        for p in high_equity_leads:
            # 2. Upsert into property_records
            conn.execute("""
                INSERT INTO property_records (
                    prop_id, zone1, mkt_tot_val, tax_stat, 
                    bldg_yr_blt, nbrhd, assrSqFt, 
                    hold_years, created_at, scrape_status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'PARTIAL', CURRENT_TIMESTAMP)
                ON CONFLICT(prop_id) DO UPDATE SET
                    mkt_tot_val = excluded.mkt_tot_val,
                    hold_years = excluded.hold_years,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                p['prop_id'], p['zone1'], p['mkt_tot_val'], 
                "DELINQUENT" if p.get('tax_stat') else "CURRENT",
                p.get('bldg_yr_blt'), p.get('nbrhd'), p.get('assrSqFt'),
                p.get('hold_years')
            ))
            
            # 3. Upsert into prospects for Morning Brief
            # Note: We use a simplified mapping for the bulk hunt
            conn.execute("""
                INSERT INTO prospects (
                    address, owner_name, parcel_number, equity_score, 
                    hold_years, source, pipeline_stage, created_at
                ) VALUES (?, ?, ?, 'HIGH', ?, 'CLARK_COUNTY_GIS', 'IDENTIFIED', CURRENT_TIMESTAMP)
                ON CONFLICT(parcel_number) DO UPDATE SET
                    hold_years = excluded.hold_years
            """, (
                p['prop_id'], # Using prop_id as temporary name holder if name redacted
                "Redacted (County GIS)", 
                p['prop_id'], 
                p.get('hold_years')
            ))
            
        conn.commit()
        conn.close()
        log.info("firehouse_hunt_ingestion_complete")
        
    except Exception as e:
        log.error("firehouse_hunt_failed", error=str(e))

if __name__ == "__main__":
    run_firehouse_hunt()
