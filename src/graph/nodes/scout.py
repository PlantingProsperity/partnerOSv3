"""
scout.py — Scout Agent (LangGraph Node)

Collects Clark County property intelligence for a specific deal using 
the two-tier ArcGIS REST + Playwright architecture.
"""

import datetime
import json
from src.graph.state import DealState
from src.utils.logger import get_logger
from src.database.db import get_connection
from src.integrations import clark_county_api

log = get_logger("agent.scout")

def scout_node(state: DealState, config: dict | None = None) -> dict:
    """
    LangGraph node function for the Scout agent.
    """
    deal_id = state.get("deal_id")
    address = state.get("address")
    parcel_number = state.get("parcel_number")
    
    # We use config to trigger Tier 2 deep-dives
    use_playwright = False
    if config and "configurable" in config:
        use_playwright = config["configurable"].get("use_playwright", False)
        
    log.info("executing_scout_v4", deal_id=deal_id, address=address, use_playwright=use_playwright)
    
    property_data = {
        "tax_status": "CURRENT",
        "hold_years": None,
        "zoning": None
    }
    gis_data = None
    
    # --- Tier 1: ArcGIS REST API (Fast, Bulk) ---
    try:
        # 1. Resolve address -> prop_id/parcel
        if not parcel_number and address:
            log.info("scout_resolving_address", address=address)
            gis_data = clark_county_api.fetch_parcel_by_address(address)
        elif parcel_number:
            log.info("scout_fetching_parcel", prop_id=parcel_number)
            # Spec uses prop_id as primary lookup
            gis_data = clark_county_api.fetch_parcel_by_prop_id(parcel_number)
            
        if gis_data:
            # 2. Extract Tier 1 Metrics
            prop_id = gis_data['prop_id']
            hold_years = clark_county_api.compute_hold_years(prop_id, last_sale_ms=gis_data.get('last_sale_date'))
            permit_count = clark_county_api.fetch_permit_count(prop_id)
            
            # --- Phase 5: Secret Strategic Signals ---
            signals = clark_county_api.fetch_strategic_signals(prop_id)
            property_data.update(signals)
            
            # --- Phase 6: Shadow Intelligence (Spatial) ---
            lat, lon = gis_data.get('lat'), gis_data.get('lon')
            if lat and lon:
                shadow = clark_county_api.fetch_shadow_pipeline(lat, lon)
                vblm = clark_county_api.fetch_vblm_details(lat, lon)
                property_data["shadow_pipeline"] = shadow
                property_data.update(vblm)
            
            property_data["tax_status"] = "DELINQUENT" if gis_data.get('tax_stat') else "CURRENT"
            property_data["hold_years"] = hold_years
            property_data["zoning"] = gis_data.get('zone1')
            property_data["pt1_desc"] = gis_data.get('pt1_desc')
            property_data["mkt_tot_val"] = gis_data.get('mkt_tot_val')
            property_data["permit_count_5yr"] = permit_count
            property_data["raw_gis_json"] = json.dumps(gis_data.get('raw_attributes'))
            
            # --- Phase 7: Strategic Signal Extraction (Panoramic Optimization) ---
            # Instead of raw JSON, we extract the top signals for the Manager
            raw = gis_data.get('raw_attributes', {})
            property_data["panoramic_signals"] = {
                "units": raw.get("Units"),
                "building_condition": raw.get("BldgCond"),
                "neighborhood_market": raw.get("Nbrhd"),
                "persons_per_household": raw.get("pph"),
                "jurisdiction": raw.get("JurisDesc"),
                "use_class": raw.get("PropertyUseClass"),
                "legal_description": raw.get("LegalShort"),
                "tax_amount": raw.get("TaxAmount")
            }
            
            # 3. Compute Equity Score
            if hold_years is None or hold_years >= 10:
                property_data["equity_score"] = "HIGH"
            elif hold_years >= 5:
                property_data["equity_score"] = "MEDIUM"
            else:
                property_data["equity_score"] = "LOW"
                
            # 4. Upsert property_records
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO property_records (
                    deal_id, prop_id, zone1, mkt_tot_val, tax_stat, 
                    bldg_yr_blt, nbrhd, assrSqFt, sale_date_most_recent,
                    permit_count_5yr, redevelopment_score, last_physical_inspection,
                    shadow_pipeline_json, vblm_net_acres, vblm_category,
                    raw_gis_json, created_at, scrape_status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(prop_id) DO UPDATE SET
                    mkt_tot_val = excluded.mkt_tot_val,
                    tax_stat = excluded.tax_stat,
                    shadow_pipeline_json = excluded.shadow_pipeline_json,
                    vblm_net_acres = excluded.vblm_net_acres,
                    raw_gis_json = excluded.raw_gis_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                deal_id, prop_id, property_data["zoning"], property_data["mkt_tot_val"],
                property_data["tax_status"], gis_data.get('bldg_yr_blt'),
                gis_data.get('nbrhd'), gis_data.get('assrSqFt'),
                None, # TODO: sale_date
                permit_count,
                property_data.get("redevelopment_score"),
                property_data.get("last_physical_inspection"),
                json.dumps(property_data.get("shadow_pipeline")),
                property_data.get("vblm_net_acres"),
                property_data.get("vblm_category"),
                json.dumps(gis_data.get('raw_attributes')),
                "PARTIAL" # REST only
            ))
            conn.commit()
            property_record_id = cursor.lastrowid
            conn.close()
            
            property_data["property_record_id"] = property_record_id
            
    except Exception as e:
        log.error("scout_tier1_failed", deal_id=deal_id, error=str(e))
        # Don't crash, let pipeline continue with partial data

    # --- Tier 2: Playwright Deep Dive (Optional, Forensic) ---
    if use_playwright:
        log.info("scout_triggering_playwright_deep_dive", deal_id=deal_id)
        # TODO: Implement scout_scraper integration
        # from src.integrations.scout_scraper import scrape_pic_details
        # from src.utils.parser import extract_json
        # raw_pic = await scrape_pic_details(prop_id)
        # data = extract_json(raw_pic)
        
    return {"property_data": property_data}
