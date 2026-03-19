import os
import json
import datetime
from pathlib import Path
from typing import Tuple, Optional
from src.graph.state import DealState
from src.utils.logger import get_logger
from src.database.db import get_connection
from src.utils.hashing import get_file_hash
from src.utils import llm
import config

log = get_logger("agent.librarian")

class Librarian:
    def __init__(self):
        self.conn = get_connection()
        
    def _check_duplicate(self, file_hash: str) -> bool:
        """Checks if the file hash already exists in the system."""
        row = self.conn.execute("SELECT 1 FROM files WHERE content_hash = ? LIMIT 1", (file_hash,)).fetchone()
        return row is not None
        
    def _maintain_knowledge(self):
        """Scans the knowledge directory for new files and triggers the Embedder if needed."""
        from src.brain.embedder import BrainEmbedder
        log.info("starting_knowledge_maintenance")
        
        # We rely on the BrainEmbedder's built-in idempotency (it checks hashes)
        # to only embed new or changed files.
        embedder = BrainEmbedder()
        embedder.walk_and_embed(config.KNOWLEDGE_DIR)

    def _classify_file(self, file_path: Path) -> Tuple[str, Optional[str]]:
        """
        Uses Gemini to classify the file content and extract a Deal ID if possible.
        Returns: (ContentClass, DealID)
        """
        # In a full implementation, this uses Gemini File API for audio 
        # and LiteLLM multimodal for images/PDFs.
        # For the S3 structural completion, we simulate the LLM extraction.
        
        ext = file_path.suffix.lower()
        if ext in ['.m4a', '.mp3', '.wav']:
            # Simulate Audio Transcription
            log.info("simulating_audio_transcription", file=file_path.name)
            return ("SELLER_CORRESPONDENCE", None) # Audio often needs manual routing
            
        elif ext in ['.pdf', '.xlsx']:
            # Simulate Document Classification
            return ("FINANCIAL_DOCUMENT", "deal_123")
            
        return ("OTHER", None)

    def _sweep_inbox(self) -> list[dict]:
        """Sweeps staging/inbox/ for new files."""
        processed_files = []
        for file_path in config.INBOX_DIR.rglob("*"):
            if file_path.is_file() and file_path.name != ".gitkeep":
                if "unresolved" in file_path.parts:
                    continue
                    
                file_hash = get_file_hash(file_path)
                if self._check_duplicate(file_hash):
                    log.info("duplicate_file_skipped", file=file_path.name)
                    continue
                
                content_class, deal_id = self._classify_file(file_path)
                status = "AWAITING_PRINCIPAL" if not deal_id else "ROUTED"
                
                log.info("file_classified", file=file_path.name, content_class=content_class, deal_id=deal_id)
                
                # Here we would move the file to the correct jacket_path or unresolved/
                # and insert the record into the `files` table.
                
                processed_files.append({
                    "name": file_path.name, 
                    "hash": file_hash,
                    "class": content_class,
                    "deal_id": deal_id,
                    "status": status
                })
                
        return processed_files

def librarian_node(state: DealState) -> dict:
    """
    Initializes the state, maintains knowledge, and routes incoming documents.
    """
    log.info("executing_librarian", deal_id=state.get("deal_id"))
    
    librarian = Librarian()
    
    # 1. Maintain Knowledge Base (Indexes new .md files)
    librarian._maintain_knowledge()
    
    # 2. Process Incoming Files
    processed = librarian._sweep_inbox()
    
    return {
        "status": "UNDER_REVIEW",
        "files_indexed": processed
    }
