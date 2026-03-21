import datetime
from src.graph.state import DealState
from src.utils.logger import get_logger
from src.database.db import get_connection

log = get_logger("agent.scout")

def scout_node(state: DealState) -> dict:
    """
    Gathers external data by querying the local Clark County data warehouse.
    """
    deal_id = state.get("deal_id")
    address = state.get("address")
    parcel_number = state.get("parcel_number")
    log.info("executing_scout", deal_id=deal_id, parcel_number=parcel_number)
    
    conn = get_connection()
    row = None
    
    # 1. Primary lookup via canonical parcel_number
    if parcel_number:
        row = conn.execute("SELECT * FROM clark_county_cache WHERE parcel_number = ?", (parcel_number,)).fetchone()
        
    # 2. Fallback lookup via fuzzy address match
    if not row and address:
        log.warning("scout_falling_back_to_address_search", deal_id=deal_id, address=address)
        row = conn.execute("""
            SELECT * FROM clark_county_cache 
            WHERE address LIKE ? COLLATE NOCASE 
            LIMIT 1
        """, (f"%{address}%",)).fetchone()
    
    conn.close()
    
    property_data = {}
    if row:
        log.info("scout_found_property", deal_id=deal_id)
        property_data["tax_status"] = row["tax_status"]
        property_data["zoning"] = row["zoning"]
        
        # Calculate hold years
        last_sale = row["last_sale_date"]
        if last_sale:
            try:
                # Assuming YYYY-MM-DD or similar
                sale_year = int(last_sale[:4])
                current_year = datetime.datetime.now(datetime.UTC).year
                property_data["hold_years"] = current_year - sale_year
            except ValueError:
                property_data["hold_years"] = None
        else:
            property_data["hold_years"] = None
    else:
        log.warning("scout_property_not_found", deal_id=deal_id, address=address)
        # NULL policy per PRD
        property_data["tax_status"] = None
        property_data["hold_years"] = None
        property_data["zoning"] = None
        
    return {"property_data": property_data}
