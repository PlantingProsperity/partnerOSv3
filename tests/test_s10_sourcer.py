import pytest
import json
from unittest.mock import patch
from src.firehouse.sourcer import analyze_uncontacted_prospects
from src.database.db import get_connection

@patch("src.firehouse.sourcer.litellm.completion")
def test_prospect_sourcer(mock_completion):
    # Setup mock LLM response matching the SourcerReport schema
    mock_response_json = """
    {
      "top_picks": [
        {
          "parcel_number": "P-TEST-123",
          "owner_name": "Test Owner",
          "address": "123 Test St",
          "reasoning": "High equity, owned for 20 years. Likely wants income stream.",
          "suggested_strategy": "Offer seller financing."
        }
      ]
    }
    """
    mock_completion.return_value.choices = [
        type("obj", (object,), {"message": type("obj", (object,), {"content": mock_response_json})()})
    ]

    # Setup dummy database data
    conn = get_connection()
    # Insert a dummy record. The raw_data must be valid JSON to be parsed by the sourcer.
    dummy_raw = json.dumps({"Estimated Equity": "100%", "Owner Type": "INDIVIDUAL"})
    conn.execute("""
        INSERT OR IGNORE INTO prospects (owner_name, address, parcel_number, equity_score, pipeline_stage, source, created_at, raw_data)
        VALUES ('Test Owner', '123 Test St', 'P-TEST-123', 'HIGH', 'IDENTIFIED', 'test', CURRENT_TIMESTAMP, ?)
    """, (dummy_raw,))
    conn.commit()

    # Execute Sourcer
    report = analyze_uncontacted_prospects()

    # Verify
    assert report is not None
    assert len(report.top_picks) == 1
    assert report.top_picks[0].parcel_number == "P-TEST-123"
    assert "seller financing" in report.top_picks[0].suggested_strategy
    
    # Assert it called Gemini Pro specifically
    called_model = mock_completion.call_args[1].get("model")
    assert "gemini-pro-latest" in called_model

    # Cleanup
    conn.execute("DELETE FROM prospects WHERE parcel_number = 'P-TEST-123'")
    conn.commit()
    conn.close()