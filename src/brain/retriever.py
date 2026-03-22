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
    Hybrid RAG retrieval using sqlite-vec + FTS5 + RRF,
    followed by a second-stage Reranking with Nemotron v2.
    """
    conn = get_connection()
    
    # --- STAGE 1: HYBRID RETRIEVAL (Gather 20 candidates) ---
    
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
        
    # Get top 20 candidate IDs
    candidate_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:20]
    
    if not candidate_ids:
        conn.close()
        return []

    # Fetch candidate texts
    placeholders = ','.join(['?'] * len(candidate_ids))
    candidate_rows = conn.execute(f"""
        SELECT chunk_id, source_path, source_cat, chunk_text
        FROM brain_chunks
        WHERE chunk_id IN ({placeholders})
    """, candidate_ids).fetchall()
    
    # Create map for lookup
    candidates = {r["chunk_id"]: r for r in candidate_rows}
    ordered_candidate_texts = [candidates[cid]["chunk_text"] for cid in candidate_ids if cid in candidates]
    
    # --- STAGE 2: RERANKING (Nemotron Cross-Encoder) ---
    
    log.info("starting_rerank_stage", candidates=len(ordered_candidate_texts))
    try:
        rerank_results = llm.rerank(
            query=query,
            passages=ordered_candidate_texts,
            agent="retriever",
            top_n=top_k
        )
        
        final_chunks = []
        for res in rerank_results:
            idx = res["index"]
            cid = candidate_ids[idx]
            data = candidates[cid]
            
            final_chunks.append(RetrievalChunk(
                chunk_id=data["chunk_id"],
                source_path=data["source_path"],
                source_cat=data["source_cat"],
                text=data["chunk_text"],
                score=res["score"],
                low_confidence=res["score"] < 0.1 # Rerank scores are logits/probs
            ))
            
        conn.close()
        return final_chunks

    except Exception as e:
        log.error("rerank_stage_failed_falling_back_to_rrf", error=str(e))
        # Fallback to RRF results if reranker fails
        results = []
        for cid in candidate_ids[:top_k]:
            data = candidates[cid]
            results.append(RetrievalChunk(
                chunk_id=data["chunk_id"],
                source_path=data["source_path"],
                source_cat=data["source_cat"],
                text=data["chunk_text"],
                score=scores[cid],
                low_confidence=scores[cid] < config.LOW_CONFIDENCE_FLOOR
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
