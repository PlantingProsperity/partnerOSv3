"""
registry.py — Generative UI Component Registry

Maps deal archetypes and strategic signals to specific Streamlit UI modules.
Used by the Workspace to dynamically assemble the dashboard.
"""

import streamlit as st
from typing import List, Callable

def render_debt_wrap_simulator(data: dict):
    st.markdown("### 🧮 Debt-Wrap Simulator")
    st.caption("Strategic Structuring for Subject-To / Wrap deals.")
    # Placeholder for logic
    cols = st.columns(2)
    cols[0].number_input("Existing Loan Balance", value=float(data.get("loan_balance", 500000)))
    cols[1].number_input("New Wrapper Rate", value=6.5)
    st.button("Calculate Wrap Spread")

def render_site_plan_calculator(data: dict):
    st.markdown("### 📐 Site-Plan Density Calculator")
    st.caption("Infill feasibility based on VBLM net buildable acres.")
    # Placeholder for logic
    st.slider("Target Unit Count", 1, 50, value=10)
    st.info(f"VBLM Net Acres: {data.get('vblm_net_acres', 'N/A')}")

# Registry Mapping
UI_COMPONENTS = {
    "SUB_TO": render_debt_wrap_simulator,
    "WRAP": render_debt_wrap_simulator,
    "REDEVELOPMENT": render_site_plan_calculator,
    "INFILL": render_site_plan_calculator
}

def get_recommended_ui(verdict_data: dict) -> List[Callable]:
    """
    Returns a list of UI functions based on the Manager's output.
    """
    modules = verdict_data.get("ui_modules", [])
    # Also infer from archetype
    archetype = verdict_data.get("archetype", "")
    if archetype in UI_COMPONENTS:
        modules.append(archetype)
        
    return [UI_COMPONENTS[m] for f in modules if (m := f.upper()) in UI_COMPONENTS]
