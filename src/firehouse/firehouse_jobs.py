"""
firehouse_jobs.py — Data Ingestion Scheduler Extensions

Integrates the Librarian mass ingestion pipeline into APScheduler.
"""

import datetime
import requests
from src.utils.logger import get_logger
from src.ingestion.pacs_parser import run_full_pacs_refresh
from src.ingestion.gis_parser import run_full_gis_refresh
from src.database.db import get_connection
import config

log = get_logger("firehouse.jobs")

def check_data_freshness():
    """
    Daily check for remote PACS update.
    Issues HEAD request to detect change via ETag/Last-Modified.
    """
    log.info("starting_daily_freshness_check")
    try:
        r = requests.head(config.PACS_ZIP_URL)
        remote_etag = r.headers.get('ETag', r.headers.get('Last-Modified'))
        
        conn = get_connection()
        last_success = conn.execute("""
            SELECT ts FROM maintenance_log 
            WHERE job_name = 'pacs_ingest' AND success = 1 
            ORDER BY ts DESC LIMIT 1
        """).fetchone()
        conn.close()
        
        # If last success was > 24h ago and ETag differs, we could trigger a delta
        # For now, we just log the status for the Morning Brief
        log.info("freshness_check_complete", etag=remote_etag)
        
    except Exception as e:
        log.error("freshness_check_failed", error=str(e))

def run_monthly_full_refresh():
    """
    The 'Big Bang' monthly update mandated by the spec.
    """
    log.info("starting_monthly_full_refresh")
    try:
        run_full_pacs_refresh()
        run_full_gis_refresh()
        log.info("monthly_refresh_complete")
    except Exception as e:
        log.error("monthly_refresh_failed", error=str(e))

def extend_scheduler(scheduler):
    """
    Wires the new ingestion jobs into the existing Firehouse scheduler.
    """
    # 1. Monthly Full Ingest ( mandated: 0 3 * * 3 )
    scheduler.add_job(run_monthly_full_refresh, 'cron', day_of_week='wed', hour=3, minute=0, id='monthly_pacs_gis_refresh')
    
    # 2. Daily Freshness Check
    scheduler.add_job(check_data_freshness, 'cron', hour=6, minute=0, id='daily_freshness_check')
    
    log.info("firehouse_ingestion_jobs_extended")
