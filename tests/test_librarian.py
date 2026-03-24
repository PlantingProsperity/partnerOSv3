import pytest
import shutil
import uuid
from pathlib import Path
from unittest.mock import patch
from src.graph.nodes.librarian import Librarian
from src.database.db import get_connection
import config

@patch("src.graph.nodes.librarian.llm.complete")
def test_librarian_sweep_and_deduplication(mock_complete, tmp_path):
    """
    Verifies that the Librarian correctly skips files that have already
    been registered in the database by their original_name.
    """
    # Mock the LLM returning a valid JSON string
    mock_complete.return_value = '{"content_class": "FINANCIAL_DOCUMENT", "deal_id": "test_deal_123"}'
    
    # Setup test environment
    test_inbox = tmp_path / "staging" / "inbox"
    test_inbox.mkdir(parents=True)
    config.INBOX_DIR = test_inbox
    
    # Create a test file with a randomized name to avoid real DB collisions
    unique_id = str(uuid.uuid4())[:8]
    test_file_name = f"test_doc_{unique_id}.txt"
    test_file = test_inbox / test_file_name
    test_file.write_text(f"Unique content for {test_file_name}")
    
    librarian = Librarian()
    
    # 1. First sweep should process the file
    processed_first = librarian._sweep_inbox()
    assert len(processed_first) == 1
    assert processed_first[0]["name"] == test_file_name
    
    # 2. Manually insert into DB to simulate routing/saving (Idempotency Key: original_name)
    file_hash = processed_first[0]["hash"]
    conn = get_connection()
    conn.execute("""
        INSERT INTO files (file_path, original_name, file_type, content_class, content_hash, discovered_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (f"/vault/{test_file_name}", test_file_name, "other", "OTHER", file_hash, "2026-03-24", "PROCESSED"))
    conn.commit()
    conn.close()
    
    # 3. Second sweep should skip the file due to duplicate original_name
    processed_second = librarian._sweep_inbox()
    assert len(processed_second) == 0
    print(f" ✅ Idempotency verified for: {test_file_name}")
