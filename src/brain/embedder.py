import hashlib
import datetime
import time
from pathlib import Path
from typing import List, Dict
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import litellm
import config
from src.utils import llm
from src.utils.logger import get_logger
from src.database.db import get_connection

log = get_logger("brain_embedder")

class BrainEmbedder:
    def __init__(self):
        self.conn = get_connection()
        self.chunk_size = config.CHUNK_SIZE
        self.chunk_overlap = config.CHUNK_OVERLAP

    @retry(
        wait=wait_exponential(multiplier=2, min=4, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((litellm.RateLimitError, litellm.APIError, litellm.Timeout)),
        reraise=True
    )
    def _safe_embed(self, chunk_text: str) -> List[float]:
        """Wraps the LLM call with exponential backoff for rate limits."""
        return llm.embed(chunk_text, agent="brain_embedder")

    def walk_and_embed(self, knowledge_path: Path):
        """
        Recursively walks the knowledge directory and embeds all .md files.
        """
        log.info("starting_brain_ingestion", path=str(knowledge_path))
        
        # Mapping subfolders to source_cat (wisdom, reference, learned)
        # Default is 'wisdom' for pinneo, ccim, dorman
        cat_map = {
            "pinneo":   "wisdom",
            "ccim":     "wisdom",
            "dorman":   "wisdom",
            "reference": "reference",
            "outcomes":  "learned"
        }

        files_processed = 0
        chunks_embedded = 0

        for md_file in knowledge_path.rglob("*.md"):
            # Determine source_cat based on the first subdirectory after 'knowledge'
            rel_parts = md_file.relative_to(knowledge_path).parts
            subfolder = rel_parts[0] if rel_parts else "unknown"
            source_cat = cat_map.get(subfolder, "wisdom")
            
            self._process_file(md_file, source_cat)
            files_processed += 1
            
        log.info("brain_ingestion_complete", 
                 files=files_processed, 
                 total_chunks=self._get_total_chunks())

    def _process_file(self, file_path: Path, source_cat: str):
        """
        Chunks and embeds a single file if its content has changed.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            chunks = self._chunk_text(content)
            
            # Skip if file already embedded and hash matches AND chunk count matches
            if self._file_already_embedded(file_path, content_hash, len(chunks)):
                # log.debug("skipping_file_no_change", file=str(file_path))
                return

            log.info("processing_new_file", file=str(file_path), chunks=len(chunks))

            # Store new embeddings in a temporary list first to avoid destructive failures
            import struct
            new_records = []
            
            for i, chunk_text in enumerate(chunks):
                # Call LLM for embedding via our unified gateway, now with retry logic
                embedding = self._safe_embed(chunk_text)
                
                blob = struct.pack("f" * len(embedding), *embedding)
                ts = datetime.datetime.now(datetime.UTC).isoformat()
                
                new_records.append(
                    (str(file_path), source_cat, chunk_text, i, content_hash, ts, blob)
                )
                
                # Rate limit REMOVED for NVIDIA NIM
                
            # If we successfully embedded all chunks, NOW we delete the old ones and insert the new ones atomically
            self._delete_old_chunks(file_path)
            
            for record in new_records:
                self.conn.execute("""
                    INSERT INTO brain_chunks (source_path, source_cat, chunk_text, chunk_index, content_hash, embedded_at, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, record)
            self.conn.commit()
                
            log.info("file_embedded", file=str(file_path), chunks=len(chunks))

        except Exception as e:
            log.error("file_processing_failed", file=str(file_path), error=str(e))

    def _chunk_text(self, text: str) -> List[str]:
        """
        Simple overlap chunking.
        """
        chunks = []
        if not text:
            return chunks
            
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += (self.chunk_size - self.chunk_overlap)
            
        return chunks

    def _insert_chunk(self, path: Path, cat: str, text: str, idx: int, hash: str, vec: List[float]):
        import json
        import struct
        
        # Convert List[float] to F32_BLOB (768 * 4 bytes)
        blob = struct.pack("f" * len(vec), *vec)
        ts = datetime.datetime.now(datetime.UTC).isoformat()
        
        self.conn.execute("""
            INSERT INTO brain_chunks (source_path, source_cat, chunk_text, chunk_index, content_hash, embedded_at, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(path), cat, text, idx, hash, ts, blob))
        self.conn.commit()

    def _file_already_embedded(self, path: Path, current_hash: str, expected_chunks: int) -> bool:
        """
        Only skip if the file exists with the same hash AND the correct number of chunks.
        """
        row = self.conn.execute(
            "SELECT COUNT(*) FROM brain_chunks WHERE source_path = ? AND content_hash = ?",
            (str(path), current_hash)
        ).fetchone()
        return row[0] == expected_chunks

    def _delete_old_chunks(self, path: Path):
        self.conn.execute("DELETE FROM brain_chunks WHERE source_path = ?", (str(path),))
        self.conn.commit()

    def _get_total_chunks(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM brain_chunks").fetchone()[0]

if __name__ == "__main__":
    embedder = BrainEmbedder()
    embedder.walk_and_embed(config.KNOWLEDGE_DIR)
