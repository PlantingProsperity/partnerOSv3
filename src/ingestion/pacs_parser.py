"""
pacs_parser.py — Clark County PACS Data Ingestion Module (Elevated)

Handles:
1. Smart Download: Only downloads PACS_OpenData.zip if remote ETag has changed.
2. Extraction: Unzips pipe-delimited text files using pathlib.
3. Adaptive Load: Reads headers directly from files using pandas with explicit dtypes.
4. Normalization: Joins staging tables into the prospects table.
5. Maintenance: Logs ETags and record counts to maintenance_log.
"""

import os
import zipfile
import httpx
import pandas as pd
import sqlite3
import asyncio
from typing import Optional
from pathlib import Path
from src.database.db import get_connection, with_db_retry
from src.utils.logger import get_logger
import config

log = get_logger("ingestion.pacs")

async def download_pacs_data() -> Optional[Path]:
    """
    Downloads the latest PACS ZIP using httpx only if it has changed.
    """
    local_path = config.STAGING_DIR / "PACS_OpenData.zip"
    log.info("checking_pacs_freshness", url=config.PACS_ZIP_URL)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Check remote headers
        try:
            r_head = await client.head(config.PACS_ZIP_URL)
            remote_etag = r_head.headers.get('ETag', r_head.headers.get('Last-Modified'))
        except Exception as e:
            log.error("pacs_head_check_failed", error=str(e))
            return local_path if local_path.exists() else None

        # 2. Check maintenance_log for previous success with same ETag
        conn = get_connection()
        last_log = conn.execute("""
            SELECT message FROM maintenance_log 
            WHERE job_name = 'pacs_ingest' AND success = 1 
            ORDER BY ts DESC LIMIT 1
        """).fetchone()
        conn.close()
        
        if last_log and remote_etag and remote_etag in str(last_log[0]):
            log.info("pacs_data_already_current", etag=remote_etag)
            return None # Signal to skip extraction
            
        log.info("pacs_update_detected", url=config.PACS_ZIP_URL)
        
        # 3. Stream download
        async with client.stream("GET", config.PACS_ZIP_URL) as response:
            if response.status_code != 200:
                log.error("pacs_download_failed", status=response.status_code)
                return None
                
            with open(local_path, "wb") as f:
                async for chunk in response.aiter_bytes():
                    f.write(chunk)
                    
        log.info("pacs_download_complete", path=str(local_path), etag=remote_etag)
        return local_path

def extract_pacs_zip(zip_path: Path) -> Path:
    """Extracts all text files to a dedicated folder using pathlib."""
    extract_dir = config.STAGING_DIR / "pacs_extracted"
    extract_dir.mkdir(exist_ok=True)
    
    log.info("extracting_pacs_zip", path=str(zip_path))
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    return extract_dir

@with_db_retry()
def load_pacs_to_staging(extract_dir: Path):
    """
    Adaptive Ingest with explicit dtypes for performance.
    """
    conn = get_connection()
    
    files = [
        ("PropAbstractVw.txt", "raw_pacs_abstract"),
        ("PropSalesInfoOnlyVw.txt", "raw_pacs_sales"),
        ("PropImprvVw.txt", "raw_pacs_imprv"),
        ("ValueMktTaxVw.txt", "raw_pacs_value"),
        ("Centroid.txt", "raw_pacs_centroid")
    ]
    
    for filename, table_name in files:
        file_path = extract_dir / filename
        if not file_path.exists():
            log.warning("pacs_file_missing", file=filename)
            continue
            
        log.info("loading_pacs_file_adaptive", file=filename, table=table_name)
        
        # Read with pandas (Using headers, pipe delimited, latin-1)
        # Use low_memory=False and specify strings for IDs to preserve leading zeros
        df = pd.read_csv(
            file_path, 
            sep="|", 
            header=0,
            on_bad_lines='skip', 
            engine='c', 
            low_memory=False,
            encoding='latin-1',
            dtype=str # Load everything as string first for safety, cast in SQL
        )
        
        df.columns = [c.strip() for c in df.columns]
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        log.info("pacs_file_loaded", rows=len(df))
        
    conn.close()

@with_db_retry()
def normalize_to_prospects():
    """
    Merges staging data into primary prospects table.
    Enforces 'A+ or Death' hold-year filter.
    """
    log.info("normalizing_pacs_to_prospects")
    conn = get_connection()
    
    # 1. Clear existing PACS_BATCH prospects to avoid duplicates if re-ingesting
    # (Optional: depends on if we want to preserve manual notes)
    
    # 2. Main Normalization Query
    # Join Abstract (Legal/Address) with Max Sales (Hold Years)
    conn.execute("""
        INSERT INTO prospects (
            address, owner_name, parcel_number, hold_years, 
            equity_score, source, pipeline_stage, created_at,
            last_pacs_refresh
        )
        SELECT 
            TRIM(a.Legal), 
            'Redacted (PACS)', 
            TRIM(CAST(a.Prop_ID AS TEXT)),
            (strftime('%Y', 'now') - strftime('%Y', s.max_sale_date)),
            'HIGH',
            'PACS_BATCH',
            'IDENTIFIED',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM raw_pacs_abstract a
        JOIN (
            SELECT prop_id, MAX(SaleDate) as max_sale_date 
            FROM raw_pacs_sales 
            WHERE invalid_sale IS NULL 
            GROUP BY prop_id
        ) s ON TRIM(CAST(a.Prop_ID AS TEXT)) = TRIM(CAST(s.prop_id AS TEXT))
        WHERE (strftime('%Y', 'now') - strftime('%Y', s.max_sale_date)) >= 10
        AND a.Status = 'Active'
        AND a.AcctType = 'Real'
        ON CONFLICT(parcel_number) DO UPDATE SET
            hold_years = excluded.hold_years,
            last_pacs_refresh = excluded.last_pacs_refresh
    """)
    
    # 3. Log counts
    count = conn.execute("SELECT COUNT(*) FROM prospects WHERE source = 'PACS_BATCH'").fetchone()[0]
    log.info("normalization_complete", total_prospects=count)
    
    conn.commit()
    conn.close()
    return count

async def run_full_pacs_refresh():
    """Executes the complete E2E PACS ingestion flow."""
    try:
        zip_path = await download_pacs_data()
        if zip_path is None:
            log.info("skipping_pacs_processing_no_change")
            return
            
        extract_dir = extract_pacs_zip(zip_path)
        load_pacs_to_staging(extract_dir)
        record_count = normalize_to_prospects()
        
        # Log maintenance success with metadata
        r_head = httpx.head(config.PACS_ZIP_URL)
        remote_etag = r_head.headers.get('ETag', 'unknown')
        
        conn = get_connection()
        conn.execute("""
            INSERT INTO maintenance_log 
            (ts, job_name, success, source, record_count, message) 
            VALUES (CURRENT_TIMESTAMP, 'pacs_ingest', 1, 'pacs', ?, ?)
        """, (record_count, f"Success. ETag: {remote_etag}"))
        conn.commit()
        conn.close()
        
        log.info("pacs_full_refresh_complete")
    except Exception as e:
        log.error("pacs_refresh_failed", error=str(e))
        raise

if __name__ == "__main__":
    asyncio.run(run_full_pacs_refresh())
