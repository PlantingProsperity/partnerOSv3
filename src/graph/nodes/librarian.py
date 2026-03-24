import os
import json
import datetime
from pathlib import Path
from typing import Tuple, Optional
from pydantic import BaseModel, Field
from google import genai
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
        
    def _transcribe_audio(self, file_path: Path) -> str:
        """
        Hybrid Transcription (ADR-005 Audited Fallback):
        1. Groq Whisper v3 Turbo for lightning STT (The "Ears").
        2. NVIDIA Mistral-Nemo Minitron for synthesis (The "Refiner").
        """
        log.info("starting_hybrid_audio_transcription", file=file_path.name)
        try:
            import litellm
            import subprocess
            
            # 1. Compress to 32k mono for speed (even for Groq)
            cache_dir = config.INBOX_DIR / "processed"
            cache_dir.mkdir(exist_ok=True)
            cached_mp3 = cache_dir / f"{file_path.stem}_32k.mp3"
            
            if not cached_mp3.exists():
                log.info("compressing_audio_for_groq", file=file_path.name)
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(file_path),
                    "-b:a", "32k", "-ac", "1", str(cached_mp3)
                ], capture_output=True, check=True)

            # 2. Lightning STT via Groq
            log.info("calling_groq_whisper_v3")
            with open(cached_mp3, "rb") as f:
                stt_res = litellm.transcription(
                    model="groq/whisper-large-v3-turbo",
                    file=f
                )
            raw_text = stt_res.text
            log.info("stt_complete", length=len(raw_text))

            # 3. Refine & Summarize via NVIDIA (Audited 8B Class)
            prompt = f"""
            You are a Principal Broker analyzing a meeting transcript.
            Provide a 3-sentence 'Doctrine Synthesis' and a clean Markdown transcript.
            
            Transcript:
            {raw_text[:15000]} # Context limited for rapid refinement
            """
            
            log.info("calling_nvidia_minitron_for_refinement")
            response_str = llm.complete(
                prompt=prompt,
                agent="librarian"
            )
            
            # 4. Save to Institutional Memory
            out_name = f"TRANSCRIPT_{file_path.stem}.md"
            out_path = config.KNOWLEDGE_DIR / "reference" / out_name
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(response_str)

            # 5. Register in DB to prevent re-transcription
            file_hash = get_file_hash(file_path)
            self.conn.execute("""
                INSERT INTO files (deal_id, original_name, file_path, file_type, content_class, content_hash, discovered_at, status)
                VALUES (?, ?, ?, 'audio', 'SELLER_CORRESPONDENCE', ?, CURRENT_TIMESTAMP, 'PROCESSED')
            """, (None, file_path.name, str(out_path), file_hash))
            self.conn.commit()

            log.info("transcription_complete", out_path=str(out_path))
            return str(out_path)

        except Exception as e:
            log.error("transcription_failed", file=file_path.name, error=str(e))
            return ""

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
            self._transcribe_audio(file_path)
            return ("SELLER_CORRESPONDENCE", None)

        # 2. Handle Documents & Images via LLM
        try:
            # Re-use the CFO hybrid parser to get a string or Gemini File object
            document_content = _parse_document(file_path)

            prompt = f"Analyze the following document and classify it into one of our taxonomy classes. Also, extract the Deal ID if it is explicitly mentioned (otherwise return null).\n\nDocument:\n{document_content}"

            response_str = llm.complete(
                prompt=prompt,
                tier="fast",
                agent="librarian",
                response_format=LibrarianClassification
            )

            if not response_str:
                return ("OTHER", None)

            import json
            import re

            # Robust JSON Extraction
            json_match = re.search(r"(\{.*\})", response_str, re.DOTALL)
            if json_match:
                response_str = json_match.group(1)

            # Additional cleanup
            response_str = response_str.replace("```json", "").replace("```", "").strip()

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
