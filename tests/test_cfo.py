import pytest
import pandas as pd
from pathlib import Path
from src.graph.nodes.cfo import _parse_document

def test_hybrid_parser_csv(tmp_path):
    # Create a dummy CSV
    csv_path = tmp_path / "test_financials.csv"
    df = pd.DataFrame({
        "Category": ["Gross Income", "Operating Expenses"],
        "Amount": [120000, 45000]
    })
    df.to_csv(csv_path, index=False)
    
    # Parse the document
    result = _parse_document(csv_path)
    
    # Verify it returns a Markdown string containing the data
    assert isinstance(result, str)
    assert "test_financials.csv" in result
    assert "Gross Income" in result
    assert "120000" in result
    assert "Operating Expenses" in result
