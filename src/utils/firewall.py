import re
import hashlib
import datetime
from src.database.db import get_connection
from src.utils.logger import get_logger

log = get_logger("firewall")

# Forbidden verbs based on LAW 1 — THE FIREWALL
FORBIDDEN_VERBS = [
    r"\bsend\b",
    r"\bsubmit\b",
    r"\bsign\b",
    r"\bexecute\b",
    r"\bemail\b",
    r"\bforward\b",
    r"\btransmit\b"
]

def validate_output(text: str, agent: str = "unknown") -> tuple[bool, str | None]:
    """
    Enforces LAW 1: Partner OS produces draft-only outputs.
    Scans for forbidden action verbs and logs results to firewall_log.
    """
    is_safe = True
    blocked_pattern = None
    
    for pattern in FORBIDDEN_VERBS:
        if re.search(pattern, text, re.IGNORECASE):
            is_safe = False
            blocked_pattern = pattern.strip(r"\b")
            break
            
    # Log to firewall_log table
    _log_firewall_event(agent, is_safe, blocked_pattern, text)
    
    if not is_safe:
        log.warning("firewall_blocked_output", agent=agent, pattern=blocked_pattern)
        
    return is_safe, blocked_pattern

def _log_firewall_event(agent: str, passed: bool, blocked_pattern: str | None, text: str):
    """
    Logs firewall events to the database for audit tracking.
    """
    ts = datetime.datetime.utcnow().isoformat()
    output_hash = hashlib.sha256(text.encode()).hexdigest()
    
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO firewall_log (ts, agent, passed, blocked_pattern, output_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (ts, agent, 1 if passed else 0, blocked_pattern, output_hash))
        conn.commit()
    except Exception as e:
        log.error("firewall_logging_failed", error=str(e))
    finally:
        conn.close()
