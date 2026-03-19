import os
import json
import datetime
from pathlib import Path
from src.graph.state import DealState
from src.utils.logger import get_logger
from src.database.db import get_connection
from src.utils.hashing import get_file_hash
import config

log = get_logger("agent.librarian")

class Librarian:
    def __init__(self):
        self.conn = get_connection()
        
    def _check_duplicate(self, file_hash: str) -> bool:
        """Checks if the file hash already exists in the system."""
        row = self.conn.execute("SELECT 1 FROM files WHERE content_hash = ? LIMIT 1", (file_hash,)).fetchone()
        return row is not None
        
    def _sweep_inbox(self) -> list[dict]:
        """Sweeps staging/inbox/ for new files."""
        processed_files = []
        for file_path in config.INBOX_DIR.rglob("*"):
            if file_path.is_file() and file_path.name != ".gitkeep":
                # Ensure we don't process files in unresolved/ again unless forced
                if "unresolved" in file_path.parts:
                    continue
                    
                file_hash = get_file_hash(file_path)
                if self._check_duplicate(file_hash):
                    log.info("duplicate_file_skipped", file=file_path.name)
                    # Optionally delete or archive the duplicate from inbox
                    continue
                
                # ... Classify and route logic goes here ...
                # For S2/S3 stubbing, we will just log it
                log.info("processing_new_file", file=file_path.name)
                processed_files.append({"name": file_path.name, "hash": file_hash})
                
        return processed_files

def librarian_node(state: DealState) -> dict:
    """
    Initializes the state and routes incoming documents.
    """
    log.info("executing_librarian", deal_id=state.get("deal_id"))
    
    librarian = Librarian()
    processed = librarian._sweep_inbox()
    
    return {
        "status": "UNDER_REVIEW",
        "files_indexed": processed
    }
