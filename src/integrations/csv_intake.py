import pandas as pd
import datetime
from pathlib import Path
from src.database.db import get_connection
from src.utils.logger import get_logger

log = get_logger("integration.csv_intake")

def process_prospect_csv(file_path: Path) -> dict:
    """
    Parses a Propwire/Title Company CSV or XLSX and inserts records into the prospects table.
    Deduplicates based on parcel_number.
    """
    stats = {"total_rows": 0, "inserted": 0, "duplicates_skipped": 0, "errors": 0}
    
    if not file_path.exists():
        log.error("file_missing", path=str(file_path))
        return stats

    log.info("starting_file_intake", path=str(file_path))
    try:
        ext = file_path.suffix.lower()
        if ext == '.xlsx':
            df = pd.read_excel(file_path, dtype=str)
        else:
            # Try standard comma first (Propwire)
            df = pd.read_csv(file_path, dtype=str)
            # If it only parsed one giant column, it's probably pipe-delimited (Clark County)
            if len(df.columns) == 1:
                df = pd.read_csv(file_path, sep="|", dtype=str)

        stats["total_rows"] = len(df)

        # 1. Specific handler for Split Names (Propwire & Skamania)
        # Propwire: 'Owner 1 First Name', 'Owner 1 Last Name'
        # Skamania: '1st Owner\'s First Name', '1st Owner\'s Last Name'
        name_combos = [
            ('Owner 1 First Name', 'Owner 1 Last Name'),
            ("1st Owner's First Name", "1st Owner's Last Name")
        ]
        for first_key, last_key in name_combos:
            if first_key in df.columns and last_key in df.columns:
                df['owner_name'] = df[first_key].fillna('') + ' ' + df[last_key].fillna('')
                df['owner_name'] = df['owner_name'].str.strip()
                break

        # 2. Fuzzy Column Mapping
        col_mapping = {}
        for col in df.columns:
            clean_col = col.lower().strip().replace(" ", "_").replace("/", "").replace("'", "")
            
            # Parcel Number
            if any(x == clean_col for x in ["parcelid", "apn", "parcel", "tax_id", "parcel_number", "apn__parcel_number_(text)", "apn__parcel_number_text"]):
                col_mapping[col] = "parcel_number"
            
            # Address
            elif any(x == clean_col for x in ["siteaddr", "site_address", "address", "property_address"]):
                col_mapping[col] = "address"
                
            # Owner Name
            elif "owner_name" not in df.columns and any(x == clean_col for x in ["ownernm", "owner_name", "owner"]):
                col_mapping[col] = "owner_name"
                
            # Equity
            elif any(x in clean_col for x in ["equity", "estimated_equity"]):
                col_mapping[col] = "equity_score"
                
            # Sale Date (for hold_years calculation)
            elif any(x == clean_col for x in ["saledt", "purchase_date", "sale_date"]):
                col_mapping[col] = "sale_date"

        if col_mapping:
            df = df.rename(columns=col_mapping)
            
        # Ensure minimum required columns exist
        for req in ["owner_name", "address", "parcel_number", "equity_score"]:
            if req not in df.columns:
                df[req] = "UNKNOWN" if req == "equity_score" else ""
                
        # 3. Calculate Hold Years (PRD 5.1)
        current_year = datetime.datetime.now().year
        if 'sale_date' in df.columns:
            def calc_hold(val):
                try:
                    dt = pd.to_datetime(val, errors='coerce')
                    if pd.notna(dt):
                        return current_year - dt.year
                except:
                    pass
                return None
            df['hold_years'] = df['sale_date'].apply(calc_hold)
        else:
            df['hold_years'] = None

        records = df.to_dict('records')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        now = datetime.datetime.now(datetime.UTC).isoformat()
        
        # INSERT OR IGNORE automatically handles deduplication on the parcel_number UNIQUE constraint
        insert_query = """
            INSERT OR IGNORE INTO prospects (
                owner_name, address, parcel_number, equity_score, hold_years,
                pipeline_stage, source, created_at, raw_data
            ) VALUES (?, ?, ?, ?, ?, 'IDENTIFIED', 'csv_import', ?, ?)
        """
        
        import json
        for r in records:
            p_num = str(r.get('parcel_number', '')).strip()
            if not p_num or p_num == 'nan':
                stats["errors"] += 1
                continue
                
            # Basic equity categorization logic
            raw_equity = r.get('equity_score', 'UNKNOWN')
            equity_cat = 'UNKNOWN'
            
            # Hold years can trigger HIGH equity even if % is unknown (Pinneo Logic)
            hold = r.get('hold_years')
            if hold and hold >= 10:
                equity_cat = 'HIGH'
            elif isinstance(raw_equity, str) and raw_equity != 'UNKNOWN':
                if '%' in raw_equity or raw_equity.replace('.','',1).isdigit():
                    try:
                        val = float(raw_equity.replace('%', ''))
                        if val > 40: equity_cat = 'HIGH'
                        elif val < 20: equity_cat = 'LOW'
                    except ValueError:
                        pass
            
            # Serialize the entire raw row (handling NaNs)
            clean_row = {k: (v if pd.notna(v) else None) for k, v in r.items()}
            raw_json = json.dumps(clean_row)
                        
            cursor.execute(insert_query, (
                str(r.get('owner_name', '')), 
                str(r.get('address', '')), 
                p_num, 
                equity_cat,
                hold,
                now,
                raw_json
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