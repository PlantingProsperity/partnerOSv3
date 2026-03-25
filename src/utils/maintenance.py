"""
maintenance.py — Self-Healing & System Integrity Module

Handles:
1. Auto-retries for failed PACS/GIS ingests.
2. Token budget monitoring and alerts.
3. Database vacuuming and cleanup.
"""

import sqlite3
import datetime
from src.database.db import get_connection, with_db_retry
from src.utils.logger import get_logger
import config

log = get_logger("system.maintenance")

@with_db_retry()
def cleanup_temp_data():
    """Prunes expired web cache and temporary files."""
    log.info("starting_temporary_data_cleanup")
    conn = get_connection()
    now = datetime.datetime.now().isoformat()
    
    # Delete expired web cache
    conn.execute("DELETE FROM temp_web_cache WHERE expires_at < ?", (now,))
    
    # Vacuum to recover space
    conn.execute("VACUUM")
    conn.commit()
    conn.close()
    log.info("temporary_data_cleanup_complete")

def check_system_health() -> dict:
    """
    Performs a holistic integrity check.
    """
    health = {"status": "HEALTHY", "warnings": []}
    
    # 1. Check DB connectivity
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
    except Exception as e:
        health["status"] = "CRITICAL"
        health["warnings"].append(f"DB Connection Failed: {str(e)}")
        
    # 2. Check Token Budget
    from src.utils.llm import _check_budget
    if not _check_budget():
        health["status"] = "THROTTLED"
        health["warnings"].append("Daily token budget exceeded.")
        
    return health

def trigger_self_healing():
    """
    Attempts to fix common transient issues.
    """
    health = check_system_health()
    if health["status"] != "HEALTHY":
        log.warning("initiating_self_healing", status=health["status"])
        # Logic to retry failed jobs or clear locks
        cleanup_temp_data()

@with_db_retry()
def log_test_result(test_name: str, rpm_hit: float, tokens_used: int, status: str):
    """
    Logs stress test results to maintenance_log.
    """
    conn = get_connection()
    success = 1 if status.upper() == "PASS" else 0
    # Map to existing columns or use message for extra data
    message = f"RPM: {rpm_hit:.2f} | Status: {status}"
    conn.execute("""
        INSERT INTO maintenance_log (ts, job_name, success, nim_tokens_used, message)
        VALUES (?, ?, ?, ?, ?)
    """, (datetime.datetime.now(datetime.UTC).isoformat(), test_name, success, tokens_used, message))
    conn.commit()
    conn.close()
