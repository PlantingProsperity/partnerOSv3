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
    # Mock the LLM returning a valid JSON string matching the Pydantic schema
    mock_complete.return_value = '{"content_class": "FINANCIAL_DOCUMENT", "deal_id": "test_deal_123"}'
    
    # Setup test environment
    test_inbox = tmp_path / "staging" / "inbox"
    test_inbox.mkdir(parents=True)
    config.INBOX_DIR = test_inbox
    
    # Create a test file with unique content to avoid cross-test hash collisions in the real DB
    unique_content = f"Category,Amount\nTest,{uuid.uuid4()}"
    test_file = test_inbox / "test_doc.csv"
    test_file.write_text(unique_content)
    
    librarian = Librarian()
    
    # 1. First sweep should process the file
    processed_first = librarian._sweep_inbox()
    assert len(processed_first) == 1
    assert processed_first[0]["name"] == "test_doc.csv"
    
    # Manually insert into DB to simulate routing/saving
    file_hash = processed_first[0]["hash"]
    unique_path = f"/dummy/path/{uuid.uuid4()}.csv"
    conn = get_connection()
    conn.execute("""
        INSERT INTO files (file_path, original_name, file_type, content_class, content_hash, discovered_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (unique_path, "test_doc.csv", "other", "OTHER", file_hash, "2026-03-18"))
    conn.commit()
    conn.close()
    
    # 2. Second sweep should skip the file due to duplicate hash
    processed_second = librarian._sweep_inbox()
    assert len(processed_second) == 0
