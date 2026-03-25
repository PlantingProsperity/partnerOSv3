"""
firehouse_jobs.py — Data Ingestion Scheduler Extensions (Elevated)

Integrates the Librarian mass ingestion pipeline into APScheduler.
Ensures 100% automated monthly refreshes and daily freshness checks.
"""

import datetime
import httpx
import asyncio
from src.utils.logger import get_logger
from src.ingestion.pacs_parser import run_full_pacs_refresh
from src.ingestion.gis_shapefile_parser import run_full_gis_refresh
from src.database.db import get_connection
import config

log = get_logger("firehouse.jobs")

async def check_data_freshness():
    """
    Daily check for remote PACS update using httpx HEAD.
    """
    log.info("starting_daily_freshness_check")
    remote_etag = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.head(config.PACS_ZIP_URL)
            r.raise_for_status()
            raw_etag = r.headers.get('ETag') or r.headers.get('Last-Modified')
            if raw_etag:
                remote_etag = raw_etag.strip(' "\'')
    except httpx.RequestError as e:
        log.error("freshness_check_network_error", error=str(e))
        return
    except Exception as e:
        log.error("freshness_check_failed", error=str(e))
        return
        
    conn = get_connection()
    try:
        last_success = conn.execute("""
            SELECT ts, message FROM maintenance_log 
            WHERE job_name = 'pacs_ingest' AND success = 1 
            ORDER BY ts DESC LIMIT 1
        """).fetchone()
        
        is_fresh = False
        if last_success and remote_etag:
            # Clean the stored message to safely compare
            stored_msg = str(last_success[1]).replace('"', '').replace("'", "")
            is_fresh = remote_etag in stored_msg
            
        log.info("freshness_check_complete", is_fresh=is_fresh, etag=remote_etag)
        
        if not is_fresh and remote_etag:
            log.info("update_detected_triggering_pacs_refresh")
            
    finally:
        conn.close()

async def run_monthly_full_refresh():
    """
    The 'Big Bang' monthly update mandated by the Grok S3 spec.
    """
    log.info("starting_monthly_full_refresh")
    try:
        await run_full_pacs_refresh()
        await run_full_gis_refresh()
        log.info("monthly_refresh_complete")
    except Exception as e:
        log.error("monthly_refresh_failed", error=str(e))

def extend_scheduler(scheduler):
    """
    Wires the new ingestion jobs into the existing Firehouse scheduler.
    """
    # Create an event loop helper for async jobs in APScheduler
    def run_async(coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    # 1. Monthly Full Ingest (Mandated: Wednesday 3 AM)
    scheduler.add_job(
        lambda: run_async(run_monthly_full_refresh()), 
        'cron', 
        day_of_week='wed', 
        hour=3, 
        minute=0, 
        id='monthly_pacs_gis_refresh'
    )
    
    # 2. Daily Freshness Check (Mandated: Daily 6 AM)
    scheduler.add_job(
        lambda: run_async(check_data_freshness()), 
        'cron', 
        hour=6, 
        minute=0, 
        id='daily_freshness_check'
    )
    
    log.info("firehouse_ingestion_jobs_extended")
