"""
risk_sentinel.py — Stress-Testing & Risk Simulation Agent (LangGraph Node)

Uses Numpy-vectorized Monte-Carlo simulations to stress-test deal volatility.
Inputs: Web volatility signals + local historical sales data.
Outputs: Decisive Risk Scores (Green/Yellow/Red).
"""

import numpy as np
import json
from src.graph.state import DealState
from src.utils.logger import get_logger

log = get_logger("agent.risk_sentinel")

def risk_sentinel_node(state: DealState) -> dict:
    """
    LangGraph node for Monte-Carlo risk simulation.
    """
    address = state.get("address")
    financials = state.get("financials", {})
    market_signals = state.get("market_signals", {})
    
    log.info("executing_risk_sentinel", address=address)
    
    # 1. Setup Simulation Parameters
    # Base DSCR from extraction
    base_dscr = financials.get("dscr", 1.0)
    # Market volatility (mocked from signals or static)
    volatility = market_signals.get("market_sentiment_score", 0.15)
    
    # 2. Vectorized Monte-Carlo (10,000 iterations)
    num_sims = 10000
    # Simulate variations in NOI (Net Operating Income)
    # Assumption: DSCR = NOI / DebtService. We simulate NOI variation.
    noi_samples = np.random.normal(1.0, volatility, num_sims)
    dscr_sims = base_dscr * noi_samples
    
    # 3. Calculate Risk Metrics
    prob_failure = np.mean(dscr_sims < 1.0)
    mean_dscr = np.mean(dscr_sims)
    std_dscr = np.std(dscr_sims)
    
    # 4. Decisive Score
    risk_level = "GREEN"
    if prob_failure > 0.20:
        risk_level = "RED"
    elif prob_failure > 0.05:
        risk_level = "YELLOW"
        
    log.info("risk_simulation_complete", prob_failure=f"{prob_failure:.2%}", level=risk_level)
    
    return {
        "risk_monte_carlo": {
            "risk_level": risk_level,
            "probability_of_default": float(prob_failure),
            "simulated_mean_dscr": float(mean_dscr),
            "simulated_std_dev": float(std_dscr),
            "iterations": num_sims
        }
    }
