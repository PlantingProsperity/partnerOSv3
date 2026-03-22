import struct
from dataclasses import dataclass
from typing import List, Dict
import config
from src.utils import llm
from src.utils.logger import get_logger
from src.database.db import get_connection

log = get_logger("brain_retriever")

@dataclass
class RetrievalChunk:
    chunk_id: int
    source_path: str
    source_cat: str
    text: str
    score: float
    low_confidence: bool

def retrieve(query: str, top_k: int = config.RAG_TOP_K) -> List[RetrievalChunk]:
    """
    Hybrid RAG retrieval using sqlite-vec + FTS5 + RRF.
    """
    conn = get_connection()
    
    # 1. Vector Search (ANN)
    query_vec = llm.embed(query, agent="retriever", input_type="query")
    vec_blob = struct.pack("f" * len(query_vec), *query_vec)
    
    # Cosine similarity via sqlite-vec
    vec_rows = conn.execute("""
        SELECT chunk_id, vec_distance_cosine(embedding, ?) as distance
        FROM brain_chunks
        ORDER BY distance ASC
        LIMIT 20
    """, (vec_blob,)).fetchall()
    
    # 2. Keyword Search (BM25 via FTS5)
    fts_rows = conn.execute("""
        SELECT rowid as chunk_id, bm25(brain_chunks_fts) as score
        FROM brain_chunks_fts
        WHERE brain_chunks_fts MATCH ?
        ORDER BY score ASC
        LIMIT 20
    """, (query,)).fetchall()
    
    # 3. Reciprocal Rank Fusion (RRF)
    # RRF score(d) = sum(1 / (k + rank(d, r)))
    k_rrf = 60
    scores: Dict[int, float] = {}
    
    # Vector ranks
    for i, row in enumerate(vec_rows):
        cid = row["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k_rrf + i + 1)
        
    # FTS ranks
    for i, row in enumerate(fts_rows):
        cid = row["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k_rrf + i + 1)
        
    # Sort by fused score
    top_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]
    
    results = []
    for cid in top_ids:
        chunk_data = conn.execute("""
            SELECT chunk_id, source_path, source_cat, chunk_text
            FROM brain_chunks
            WHERE chunk_id = ?
        """, (cid,)).fetchone()
        
        score = scores[cid]
        # Low confidence if max RRF score < threshold
        low_confidence = score < config.LOW_CONFIDENCE_FLOOR
        
        results.append(RetrievalChunk(
            chunk_id=chunk_data["chunk_id"],
            source_path=chunk_data["source_path"],
            source_cat=chunk_data["source_cat"],
            text=chunk_data["chunk_text"],
            score=score,
            low_confidence=low_confidence
        ))
        
    conn.close()
    return results

if __name__ == "__main__":
    # Test query
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "negotiation"
    res = retrieve(q)
    for r in res:
        print(f"[{r.score:.4f}] {r.source_path} ({r.source_cat})")
        print(f"  {r.text[:100]}...")
