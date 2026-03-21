import pandas as pd
import datetime
from pathlib import Path
from src.database.db import get_connection
from src.utils.logger import get_logger

log = get_logger("integration.clark_county")

def sync_from_csv(csv_path: Path):
    """
    Parses a Clark County bulk data CSV (pipe-delimited) and UPSERTs 
    the records into the clark_county_cache table.
    """
    if not csv_path.exists():
        log.error("sync_failed_file_missing", path=str(csv_path))
        return

    log.info("starting_clark_county_sync", path=str(csv_path))
    
    try:
        # Clark County data is typically pipe-delimited
        df = pd.read_csv(csv_path, sep="|", dtype=str)
        
        # Standardize column names (mapping from typical county formats to ours)
        # In a real scenario, this mapping would be very specific to the county's schema.
        # We assume the CSV has columns matching our table for this implementation.
        required_cols = ['parcel_number', 'address', 'owner_name', 'zoning', 'year_built', 'assessed_value', 'tax_status', 'last_sale_date']
        
        # Add missing columns with None if the CSV doesn't have them
        for col in required_cols:
            if col not in df.columns:
                df[col] = None
                
        # Clean up types
        df['year_built'] = pd.to_numeric(df['year_built'], errors='coerce')
        df['assessed_value'] = pd.to_numeric(df['assessed_value'], errors='coerce')
        
        records = df[required_cols].to_dict('records')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        now = datetime.datetime.now(datetime.UTC).isoformat()
        
        upsert_query = """
            INSERT INTO clark_county_cache (
                parcel_number, address, owner_name, zoning, year_built, 
                assessed_value, tax_status, last_sale_date, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(parcel_number) DO UPDATE SET
                address=excluded.address,
                owner_name=excluded.owner_name,
                zoning=excluded.zoning,
                year_built=excluded.year_built,
                assessed_value=excluded.assessed_value,
                tax_status=excluded.tax_status,
                last_sale_date=excluded.last_sale_date,
                updated_at=excluded.updated_at
        """
        
        data_tuples = [
            (
                r['parcel_number'], r['address'], r['owner_name'], r['zoning'], 
                r['year_built'], r['assessed_value'], r['tax_status'], 
                r['last_sale_date'], now
            ) for r in records if pd.notna(r['parcel_number'])
        ]
        
        cursor.executemany(upsert_query, data_tuples)
        conn.commit()
        
        log.info("sync_complete", records_updated=len(data_tuples))
        
    except Exception as e:
        log.error("sync_failed", error=str(e))
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        sync_from_csv(Path(sys.argv[1]))
    else:
        print("Usage: python src/integrations/clark_county_sync.py <path_to_csv>")
