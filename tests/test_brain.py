import pytest
from pathlib import Path
from src.brain.embedder import BrainEmbedder
from src.brain.retriever import retrieve
from src.database.db import get_connection
import config

def test_brain_ingestion_and_retrieval(tmp_path):
    # Setup test knowledge dir
    test_kb = tmp_path / "knowledge" / "pinneo"
    test_kb.mkdir(parents=True)
    test_file = test_kb / "test.md"
    test_file.write_text("The equity screen rule requires 10 years of hold time.")

    # Run embedder
    embedder = BrainEmbedder()
    embedder.walk_and_embed(tmp_path / "knowledge")

    # Verify chunks in DB
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM brain_chunks").fetchone()[0]
    assert count > 0
    conn.close()

    # Test retrieval
    results = retrieve("equity screen rule")
    assert len(results) > 0
    assert "equity screen rule" in results[0].text.lower()
    assert results[0].source_cat == "wisdom"
    assert results[0].low_confidence is False
