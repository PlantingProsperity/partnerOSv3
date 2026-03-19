import pytest
import shutil
from pathlib import Path
from src.graph.nodes.librarian import Librarian
from src.database.db import get_connection
import config

def test_librarian_sweep_and_deduplication(tmp_path):
    # Setup test environment
    test_inbox = tmp_path / "staging" / "inbox"
    test_inbox.mkdir(parents=True)
    config.INBOX_DIR = test_inbox
    
    # Create a test file
    test_file = test_inbox / "test_doc.txt"
    test_file.write_text("This is a test document.")
    
    librarian = Librarian()
    
    # 1. First sweep should process the file
    processed_first = librarian._sweep_inbox()
    assert len(processed_first) == 1
    assert processed_first[0]["name"] == "test_doc.txt"
    
    # Manually insert into DB to simulate routing/saving
    file_hash = processed_first[0]["hash"]
    conn = get_connection()
    conn.execute("""
        INSERT INTO files (file_path, original_name, file_type, content_class, content_hash, discovered_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("/dummy/path", "test_doc.txt", "other", "OTHER", file_hash, "2026-03-18"))
    conn.commit()
    conn.close()
    
    # 2. Second sweep should skip the file due to duplicate hash
    processed_second = librarian._sweep_inbox()
    assert len(processed_second) == 0
