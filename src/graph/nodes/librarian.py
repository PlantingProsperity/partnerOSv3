import os
import json
import datetime
from pathlib import Path
from typing import Tuple, Optional
from pydantic import BaseModel, Field
from src.graph.state import DealState
from src.utils.logger import get_logger
from src.database.db import get_connection
from src.utils.hashing import get_file_hash
from src.utils import llm
from src.graph.nodes.cfo import _parse_document
import config

log = get_logger("agent.librarian")

class LibrarianClassification(BaseModel):
    content_class: str = Field(
        description="One of: FINANCIAL_DOCUMENT, SELLER_CORRESPONDENCE, TITLE_REPORT, INSPECTION_REPORT, FIELD_NOTES, MUNICIPAL_RECORD, OFFERING_MEMORANDUM, LEGAL_DOCUMENT, OTHER",
        validation_alias="taxonomy_class"
    )
    deal_id: Optional[str] = Field(
        None, 
        description="The specific Deal ID if clearly identifiable in the document, else null."
    )

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
        ext = file_path.suffix.lower()
        
        # 1. Handle Audio separately (ADR-005)
        if ext in ['.m4a', '.mp3', '.wav', '.mp4']:
            log.info("audio_file_detected_for_transcription", file=file_path.name)
            # Transcription logic goes here. For now, we return default classification.
            return ("SELLER_CORRESPONDENCE", None)
            
        # 2. Handle Documents & Images via LLM
        try:
            # Re-use the CFO hybrid parser to get a string or Gemini File object
            document_content = _parse_document(file_path)
            
            prompt = f"Analyze the following document and classify it into one of our taxonomy classes. Also, extract the Deal ID if it is explicitly mentioned (otherwise return null).\n\nDocument:\n{document_content}"
            
            import json
            import re
            
            response_str = llm.complete(
                prompt=prompt,
                tier="fast",
                agent="librarian",
                response_format=LibrarianClassification
            )
            
            # Flexible JSON Parsing: NVIDIA models often hallucinate key names
            data = json.loads(response_str)
            
            # Map various possible keys to our internal fields
            content_class = data.get("content_class") or data.get("taxonomy_class") or data.get("taxonomy") or data.get("class") or "OTHER"
            deal_id = data.get("deal_id") or data.get("dealid")
            
            return (str(content_class).upper(), deal_id)
            
        except Exception as e:
            log.error("librarian_classification_failed", file=file_path.name, error=str(e))
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
