import hashlib
import datetime
from pathlib import Path
from typing import List, Dict
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
            
            # Skip if file already embedded and hash matches
            if self._file_already_embedded(file_path, content_hash):
                # log.debug("skipping_file_no_change", file=str(file_path))
                return

            # Remove old chunks for this file
            self._delete_old_chunks(file_path)

            # Perform chunking
            chunks = self._chunk_text(content)
            
            for i, chunk_text in enumerate(chunks):
                # Call LLM for embedding via our unified gateway
                embedding = llm.embed(chunk_text, agent="brain_embedder")
                
                # Write to brain_chunks (F32_BLOB for sqlite-vec)
                self._insert_chunk(file_path, source_cat, chunk_text, i, content_hash, embedding)
                
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

    def _file_already_embedded(self, path: Path, current_hash: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM brain_chunks WHERE source_path = ? AND content_hash = ? LIMIT 1",
            (str(path), current_hash)
        ).fetchone()
        return row is not None

    def _delete_old_chunks(self, path: Path):
        self.conn.execute("DELETE FROM brain_chunks WHERE source_path = ?", (str(path),))
        self.conn.commit()

    def _get_total_chunks(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM brain_chunks").fetchone()[0]

if __name__ == "__main__":
    embedder = BrainEmbedder()
    embedder.walk_and_embed(config.KNOWLEDGE_DIR)
