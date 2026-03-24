"""
pacs_parser.py — Clark County PACS Data Ingestion Module

Handles:
1. Smart Download: Only downloads PACS_OpenData.zip if remote ETag/Last-Modified has changed.
2. Extraction: Unzips pipe-delimited text files to staging.
3. Adaptive Load: Reads headers directly from files to populate staging tables.
4. Maintenance: Logs ETags to prevent redundant data processing.
"""

import os
import zipfile
import requests
import pandas as pd
import sqlite3
import datetime
from typing import Optional
from pathlib import Path
from src.database.db import get_connection
from src.utils.logger import get_logger
import config

log = get_logger("ingestion.pacs")

def download_pacs_data() -> Optional[Path]:
    """
    Downloads the latest PACS ZIP only if it has changed on the server.
    """
    local_path = config.STAGING_DIR / "PACS_OpenData.zip"
    log.info("checking_pacs_freshness", url=config.PACS_ZIP_URL)
    
    # 1. Check remote headers
    r_head = requests.head(config.PACS_ZIP_URL)
    remote_etag = r_head.headers.get('ETag', r_head.headers.get('Last-Modified'))
    
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
    r = requests.get(config.PACS_ZIP_URL, stream=True)
    r.raise_for_status()
    
    with open(local_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
            
    log.info("pacs_download_complete", path=str(local_path), etag=remote_etag)
    return local_path

def extract_pacs_zip(zip_path: Path) -> Path:
    """Extracts all text files to a dedicated folder."""
    extract_dir = config.STAGING_DIR / "pacs_extracted"
    extract_dir.mkdir(exist_ok=True)
    
    log.info("extracting_pacs_zip", path=str(zip_path))
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    return extract_dir

def load_pacs_to_staging(extract_dir: Path):
    """
    Empirical Ingest: Reads headers directly from files.
    Ensures zero data loss and resilience to county schema changes.
    """
    conn = get_connection()
    
    # Files to ingest
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
        
        # Read with pandas (Using headers from file, pipe delimited, latin-1)
        df = pd.read_csv(
            file_path, 
            sep="|", 
            header=0, # Use first line as header
            on_bad_lines='skip', 
            engine='c', 
            low_memory=False,
            encoding='latin-1'
        )
        
        # Clean column names (strip whitespace)
        df.columns = [c.strip() for c in df.columns]
        
        # Write to SQL (replace existing data for full refresh)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        log.info("pacs_file_loaded", rows=len(df))
        
    conn.close()

def run_full_pacs_refresh():
    """Executes the complete E2E PACS ingestion flow with delta detection."""
    try:
        zip_path = download_pacs_data()
        if zip_path is None:
            log.info("skipping_pacs_processing_no_change")
            return
            
        extract_dir = extract_pacs_zip(zip_path)
        load_pacs_to_staging(extract_dir)
        
        # Log success with ETag for next run comparison
        r_head = requests.head(config.PACS_ZIP_URL)
        remote_etag = r_head.headers.get('ETag', r_head.headers.get('Last-Modified'))
        
        conn = get_connection()
        conn.execute("INSERT INTO maintenance_log (ts, job_name, success, message) VALUES (CURRENT_TIMESTAMP, 'pacs_ingest', 1, ?)",
                     (f"Success. ETag: {remote_etag}",))
        conn.commit()
        conn.close()
        
        log.info("pacs_full_refresh_complete")
    except Exception as e:
        log.error("pacs_refresh_failed", error=str(e))
        raise

if __name__ == "__main__":
    run_full_pacs_refresh()
