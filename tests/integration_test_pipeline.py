import pytest
import sqlite3
import json
from unittest.mock import patch, MagicMock
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
import config
from src.graph.deal_graph import build_graph
from src.database.db import get_connection

@patch("src.graph.deal_graph.librarian_node")
@patch("src.graph.nodes.cfo._parse_document")
@patch("src.brain.retriever.retrieve")
@patch("src.utils.llm.complete")
def test_end_to_end_pipeline(
    mock_llm_complete, mock_retrieve, mock_parse_doc, mock_librarian, tmp_path
):
    # --- MOCKS ---
    # Librarian Mock
    mock_librarian.side_effect = lambda state: {"status": "UNDER_REVIEW"}

    # File Parser Mock
    mock_parse_doc.return_value = "Mock Document Content"
    
    # Global LLM Mock
    def mock_llm_router(*args, **kwargs):
        agent = kwargs.get("agent")
        if agent == "cfo_p1":
            return json.dumps({
                "gross_income": {"value": 120000, "citation": {"file": "doc", "verbatim_text": "120k"}},
                "noi": {"value": 75000, "citation": {"file": "doc", "verbatim_text": "75k"}},
                "asking_price": {"value": 1000000, "citation": {"file": "doc", "verbatim_text": "1M"}},
                "annual_debt_service": {"value": 60000, "citation": {"file": "doc", "verbatim_text": "60k"}}
            })
        elif agent == "profiler":
            return '{"archetype": "High-D", "confidence": 90, "pinneo_cites": ["Test"]}'
        elif agent == "manager":
            return '{"verdict": "APPROVE", "confidence": 95, "reasoning_text": "Good math.", "scribe_instructions": "- Draft LOI"}'
        elif agent == "scribe":
            return "# Final LOI\nApproved."
        return "{}"
        
    mock_llm_complete.side_effect = mock_llm_router

    # --- SETUP ---
    deal_id = "test_e2e_123"
    db_path = tmp_path / "checkpoints.sqlite"
    cp_conn = sqlite3.connect(str(db_path), check_same_thread=False)
    memory = SqliteSaver(cp_conn)
    graph = build_graph().compile(checkpointer=memory)
    config_dict = {"configurable": {"thread_id": deal_id}}

    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO deals (deal_id, address, address_slug, jacket_path, thread_id, created_at, updated_at) VALUES (?, 'E2E Ave', 'e2e', '/dummy', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)", (deal_id, deal_id))
    conn.execute("INSERT OR REPLACE INTO clark_county_cache (parcel_number, address, tax_status, last_sale_date, updated_at) VALUES ('E2E-PARCEL', 'E2E Ave', 'CURRENT', '2010-01-01', '2026')")
    conn.commit()

    initial_state = {
        "deal_id": deal_id,
        "address": "E2E Ave",
        "parcel_number": "E2E-PARCEL",
        "status": "INTAKE",
        "cfo_verified": False,
        "heuristic_flagged": False,
        "heuristic_failures": [],
        "financials": {},
        "financial_doc_paths": ["/dummy/doc.pdf"],
        "property_data": {},
        "seller_archetype": "",
        "profiler_confidence": 0,
        "profiler_cites": [],
        "verdict": "",
        "reasoning_text": "",
        "manager_confidence": 0,
        "scribe_instructions": "",
        "loi_draft": ""
    }

    # --- RUN PART 1 (To Interrupt) ---
    result_p1 = graph.invoke(initial_state, config_dict)
    
    # Verify graph stopped at the verify_gate interrupt
    state = graph.get_state(config_dict)
    assert state.next == ()
    assert result_p1["financials"]["extracted"] is True
    
    # Verify Draft Financials in DB
    draft_id = result_p1["financials"]["draft_id"]
    row = conn.execute("SELECT status FROM draft_financials WHERE id = ?", (draft_id,)).fetchone()
    assert row["status"] == "UNVERIFIED"

    # --- SIMULATE UI VERIFICATION ---
    # The UI writes to verified_financials and resumes
    verified_data = {
        "noi": {"value": 75000},
        "asking_price": {"value": 1000000},
        "annual_debt_service": {"value": 60000}
    }
    cursor = conn.cursor()
    cursor.execute("INSERT INTO verified_financials (deal_id, data, verified_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (deal_id, json.dumps(verified_data)))
    verified_id = cursor.lastrowid
    conn.commit()

    # --- RUN PART 2 (Resume) ---
    result_p2 = graph.invoke(
        Command(resume=True, update={"cfo_verified": True, "financials": {"verified_financials_id": verified_id}}, goto="cfo_calculate"),
        config_dict
    )

    # --- FINAL VERIFICATION ---
    # Graph should have reached END
    state = graph.get_state(config_dict)
    assert not state.next
    
    # State checks
    assert result_p2["financials"]["calculated"] is True
    assert result_p2["financials"]["dscr"] == 1.25  # 75k / 60k
    assert result_p2["property_data"]["tax_status"] == "CURRENT"
    assert result_p2["seller_archetype"] == "High-D"
    assert result_p2["verdict"] == "APPROVE"
    assert "Final LOI" in result_p2["loi_draft"]
    
    # DB Checks
    v_row = conn.execute("SELECT * FROM verdicts WHERE deal_id = ?", (deal_id,)).fetchone()
    assert v_row is not None
    assert v_row["verdict"] == "APPROVE"
    
    # Cleanup (Robust)
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("DELETE FROM verdicts WHERE deal_id = ?", (deal_id,))
    conn.execute("DELETE FROM financial_analyses WHERE deal_id = ?", (deal_id,))
    conn.execute("DELETE FROM verified_financials WHERE id = ?", (verified_id,))
    conn.execute("DELETE FROM draft_financials WHERE deal_id = ?", (deal_id,))
    conn.execute("DELETE FROM seller_profiles WHERE deal_id = ?", (deal_id,))
    conn.execute("DELETE FROM property_records WHERE deal_id = ?", (deal_id,))
    conn.execute("DELETE FROM files WHERE deal_id = ?", (deal_id,))
    conn.execute("DELETE FROM llm_calls WHERE deal_id = ?", (deal_id,))
    conn.execute("DELETE FROM gemini_token_usage WHERE deal_id = ?", (deal_id,))
    conn.execute("DELETE FROM deals WHERE deal_id = ?", (deal_id,))
    conn.execute("DELETE FROM clark_county_cache WHERE parcel_number = 'E2E-PARCEL'")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()
    cp_conn.close()
