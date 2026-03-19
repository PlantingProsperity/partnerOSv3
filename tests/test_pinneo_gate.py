import pytest
import config
from src.graph.nodes.pinneo_gate import pinneo_gate_node

def test_pinneo_gate_passes():
    state = {
        "deal_id": "deal_pass",
        "financials": {
            "dscr": config.CFO_DSCR_FLOOR + 0.1,  # Above floor
            "cap_rate": config.CFO_CAP_RATE_FLOOR + 0.02 # Above floor
        }
    }
    
    result = pinneo_gate_node(state)
    assert result["heuristic_flagged"] is False
    assert len(result["heuristic_failures"]) == 0

def test_pinneo_gate_fails_dscr():
    state = {
        "deal_id": "deal_fail_dscr",
        "financials": {
            "dscr": config.CFO_DSCR_FLOOR - 0.1,  # Below floor
            "cap_rate": config.CFO_CAP_RATE_FLOOR + 0.02 # Above floor
        }
    }
    
    result = pinneo_gate_node(state)
    assert result["heuristic_flagged"] is True
    assert len(result["heuristic_failures"]) == 1
    assert "DSCR" in result["heuristic_failures"][0]

def test_pinneo_gate_fails_both():
    state = {
        "deal_id": "deal_fail_both",
        "financials": {
            "dscr": config.CFO_DSCR_FLOOR - 0.1,     # Below floor
            "cap_rate": config.CFO_CAP_RATE_FLOOR - 0.01 # Below floor
        }
    }
    
    result = pinneo_gate_node(state)
    assert result["heuristic_flagged"] is True
    assert len(result["heuristic_failures"]) == 2
