"""
memory.py — Hierarchical Cognitive Memory (H-MEM) Manager

Handles:
1. Episodic Trace Logging: Permanent history of interactions.
2. Semantic Fact Distillation: Bayesian belief updates for seller traits.
3. Context Retrieval: Providing stateful history to the Manager agent.
"""

import sqlite3
import datetime
import json
from typing import Dict, List, Optional, Any
from src.database.db import get_connection, with_db_retry
from src.utils.logger import get_logger
import config

log = get_logger("brain.memory")

class MemoryManager:
    """
    Manages the 3-tier memory model (Episodic, Semantic, Procedural).
    """
    def __init__(self):
        self.db_path = config.DB_PATH

    @with_db_retry()
    def add_episode(self, deal_id: str, seller_id: str, trace_type: str, summary: str, date: str = None):
        """Logs a new episodic interaction."""
        if not date:
            date = datetime.datetime.now().isoformat()
            
        log.info("logging_episodic_trace", deal_id=deal_id, type=trace_type)
        conn = get_connection()
        conn.execute("""
            INSERT INTO episodic_traces (deal_id, seller_id, trace_date, trace_type, raw_summary)
            VALUES (?, ?, ?, ?, ?)
        """, (deal_id, seller_id, date, trace_type.upper(), summary))
        conn.commit()
        conn.close()

    @with_db_retry()
    def update_semantic_fact(self, seller_id: str, trait: str, value: str, reliability: float = 0.8):
        """
        Performs a Bayesian belief update on a semantic fact.
        reliability: 0.0 to 1.0 (How much we trust this specific signal).
        """
        log.info("updating_semantic_fact", seller=seller_id, trait=trait, value=value)
        conn = get_connection()
        
        # 1. Fetch current alpha/beta
        row = conn.execute("""
            SELECT alpha, beta, trait_value FROM semantic_facts 
            WHERE seller_id = ? AND trait_key = ?
        """, (seller_id, trait)).fetchone()
        
        if row:
            alpha, beta, current_val = row
            if value == current_val:
                # Evidence supports current value
                alpha += reliability
            else:
                # Evidence conflicts
                # If reliability is high, we start 'doubting' the old value
                beta += reliability
                # If beta outweighs alpha significantly, we might flip the value 
                # (handled in consolidation or here)
                if beta > alpha + 2: # Significant counter-evidence
                    alpha, beta = 1.0 + reliability, 1.0
                    current_val = value
            
            conn.execute("""
                UPDATE semantic_facts 
                SET alpha = ?, beta = ?, trait_value = ?, last_updated = CURRENT_TIMESTAMP
                WHERE seller_id = ? AND trait_key = ?
            """, (alpha, beta, current_val, seller_id, trait))
        else:
            # Initial belief
            conn.execute("""
                INSERT INTO semantic_facts (seller_id, trait_key, trait_value, alpha, beta)
                VALUES (?, ?, ?, ?, ?)
            """, (seller_id, trait, value, 1.0 + reliability, 1.0))
            
        conn.commit()
        conn.close()

    @with_db_retry()
    def get_seller_context(self, seller_id: str) -> Dict[str, Any]:
        """
        Retrieves the 'State of the Relationship'.
        Returns distilled facts and the last 3 episodes.
        """
        conn = get_connection()
        
        # 1. Get Facts (Semantic)
        facts = conn.execute("""
            SELECT trait_key, trait_value, confidence FROM semantic_facts 
            WHERE seller_id = ?
        """, (seller_id,)).fetchall()
        
        # 2. Get Recent History (Episodic)
        episodes = conn.execute("""
            SELECT trace_date, trace_type, raw_summary FROM episodic_traces 
            WHERE seller_id = ? ORDER BY trace_date DESC LIMIT 3
        """, (seller_id,)).fetchall()
        
        conn.close()
        
        return {
            "facts": {f[0]: {"value": f[1], "confidence": f[2]} for f in facts},
            "history": [{"date": e[0], "type": e[1], "summary": e[2]} for e in episodes]
        }
