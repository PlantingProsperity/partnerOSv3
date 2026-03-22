import pandas as pd
import datetime
from pathlib import Path
from src.database.db import get_connection
from src.utils.logger import get_logger

log = get_logger("integration.csv_intake")

def process_prospect_csv(file_path: Path) -> dict:
    """
    Parses a Propwire/Title Company CSV and inserts records into the prospects table.
    Deduplicates based on parcel_number.
    """
    stats = {"total_rows": 0, "inserted": 0, "duplicates_skipped": 0, "errors": 0}
    
    if not file_path.exists():
        log.error("csv_missing", path=str(file_path))
        return stats

    log.info("starting_csv_intake", path=str(file_path))
    
    try:
        df = pd.read_csv(file_path, dtype=str)
        stats["total_rows"] = len(df)
        
        # Fuzzy Column Mapping
        # Real-world CSVs have varied headers. We map them to our schema.
        col_mapping = {}
        for col in df.columns:
            clean_col = col.lower().strip().replace(" ", "_")
            if any(x in clean_col for x in ["owner_name", "owner", "owner 1", "name"]):
                col_mapping[col] = "owner_name"
            elif any(x in clean_col for x in ["address", "property_address", "site_address"]):
                col_mapping[col] = "address"
            elif any(x in clean_col for x in ["parcel", "apn", "tax_id"]):
                col_mapping[col] = "parcel_number"
            elif any(x in clean_col for x in ["equity", "equity_percent", "estimated_equity"]):
                col_mapping[col] = "equity_score"
                
        if not all(k in col_mapping.values() for k in ["owner_name", "address", "parcel_number"]):
            log.warning("csv_missing_required_columns", found_mapped=list(col_mapping.values()))
            
        df = df.rename(columns=col_mapping)
        
        # Ensure minimum required columns exist
        for req in ["owner_name", "address", "parcel_number", "equity_score"]:
            if req not in df.columns:
                df[req] = "UNKNOWN" if req == "equity_score" else ""
                
        records = df.to_dict('records')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        now = datetime.datetime.now(datetime.UTC).isoformat()
        
        # INSERT OR IGNORE automatically handles deduplication on the parcel_number UNIQUE constraint
        insert_query = """
            INSERT OR IGNORE INTO prospects (
                owner_name, address, parcel_number, equity_score, 
                pipeline_stage, source, created_at
            ) VALUES (?, ?, ?, ?, 'IDENTIFIED', 'csv_import', ?)
        """
        
        for r in records:
            if not r['parcel_number'] or pd.isna(r['parcel_number']):
                stats["errors"] += 1
                continue
                
            # Basic equity categorization logic
            raw_equity = r.get('equity_score', 'UNKNOWN')
            equity_cat = 'UNKNOWN'
            if isinstance(raw_equity, str):
                if '%' in raw_equity or raw_equity.replace('.','',1).isdigit():
                    try:
                        val = float(raw_equity.replace('%', ''))
                        if val > 40: equity_cat = 'HIGH'
                        elif val < 20: equity_cat = 'LOW'
                    except ValueError:
                        pass
                        
            cursor.execute(insert_query, (
                str(r['owner_name']), 
                str(r['address']), 
                str(r['parcel_number']), 
                equity_cat, 
                now
            ))
            
            if cursor.rowcount > 0:
                stats["inserted"] += 1
            else:
                stats["duplicates_skipped"] += 1
                
        conn.commit()
        
        # Log to the new S0 csv_import_log table for auditability
        conn.execute("""
            INSERT INTO csv_import_log (filename, imported_at, rows_total, rows_new, rows_updated, rows_skipped)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (file_path.name, now, stats["total_rows"], stats["inserted"], 0, stats["duplicates_skipped"]))
        conn.commit()
        
        log.info("csv_intake_complete", stats=stats)
        
    except Exception as e:
        log.error("csv_intake_failed", error=str(e))
        stats["errors"] += 1
    finally:
        if 'conn' in locals():
            conn.close()
            
    return stats