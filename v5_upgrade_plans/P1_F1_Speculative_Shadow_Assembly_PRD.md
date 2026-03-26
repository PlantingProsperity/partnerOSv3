# PartnerOS v5.0 PRD | Pillar 1: Speculative Shadow Assembly
**Feature ID:** P1-F1
**Status:** Draft / Granular Specification
**Date:** 2026-03-27

## 1. Executive Summary
'Speculative Shadow Assembly' (SSA) is a performance-optimization layer that transforms the PartnerOS UI from a reactive dashboard into a predictive workspace. By leveraging early signals from the 'Scout' node (Tier 1 GIS), the system speculatively pre-renders complex UI wireframes (Shadow DOM) for the specific analytical tools a Principal is likely to need, *before* the heavy LLM-driven data ingestion or pro-forma generation is complete.

---

## 2. Technical Research Foundation

### 2.1 Shadow DOM Pre-rendering
To ensure instant visual response, SSA utilizes **Declarative Shadow DOM (DSD)**. This allows the server (or initial Streamlit payload) to send the internal structure of a component before the JavaScript bundle or React hydration completes.
- **Isolation:** CSS styles for pulsing animations and wireframe layouts are encapsulated, preventing interference with Streamlit's global theme.
- **Parsing Speed:** The browser renders the template immediately upon HTML parsing.

### 2.2 Predictive State-Loading
The system uses a **Probability-Weighted UI Registry**. Instead of waiting for a final 'Manager Verdict', the UI speculates based on raw GIS attributes:
- `tax_stat == DELINQUENT` -> 90% probability of needing the 'Distress Sentinel' tool.
- `units > 10` -> 85% probability of needing the 'Multifamily Proforma' tool.

### 2.3 Wireframe Pulsing (Anticipated Data)
Wireframes use CSS `keyframes` to create a "shimmer" or "pulse" effect on grayed-out blocks.
- **Pulsing Logic:** `opacity: 0.5` to `opacity: 1.0` over 1.5 seconds.
- **Spatial Consistency:** Skeletons match the exact pixel dimensions of the final components to prevent "Layout Shift" (CLS).

---

## 3. User Stories

### 3.1 The "Instant Distress" View
**User:** Roman (Principal)
**Action:** Pastes an address with delinquent taxes into the search bar.
**Story:** As a Principal, I want to see the pulsing skeleton of the 'Distress Analysis' tool within 200ms of clicking search, so I can see the system has identified the distress signal even while the 'Scribe' is still drafting the LOI.

### 3.2 The "Anticipated Comps" Flow
**User:** Investment Associate
**Action:** Adjusts a slider in the pro-forma.
**Story:** As a User, I want the Comps table to immediately transition into a pulsing wireframe state when I change the search radius, showing me that the system is speculatively re-fetching data based on my interaction.

---

## 4. Component Lifecycle

1.  **Node Inception (Scout Tier 1):** The Scout node fetches basic GIS data (REST API).
2.  **Speculative Emission:** A side-car `ShadowManager` node evaluates the GIS signals. If a signal meets a threshold, it emits a `shadow_ui_trigger` event with a `TemplateID`.
3.  **Shadow Assembly (Frontend):** 
    - Streamlit/React receives the `TemplateID`.
    - The `ShadowRoot` is injected with the corresponding DSD template.
    - CSS `animate-pulse` starts.
4.  **Data Hydration:** 
    - The 'Manager' or 'Scribe' node completes its task.
    - Final data is pushed to the `DealState`.
    - The React component detects `isReady = true`.
5.  **Transition:** The pulsing skeleton fades out (300ms transition) as the real data components "pop" into place.

---

## 5. Backend Trigger Logic (The Manager Node)

The Manager node is extended with a **Pre-Verdict Heuristic Engine**. This engine runs in parallel with the LLM reasoning:

```python
# Speculative Logic Snippet
def speculative_trigger_logic(gis_signals: dict):
    triggers = []
    
    # Distress Trigger
    if gis_signals.get('tax_status') == 'DELINQUENT':
        triggers.append({"tool": "DistressSentinel", "confidence": 0.95})
        
    # Development Trigger
    if gis_signals.get('vblm_category') == 'VACANT':
        triggers.append({"tool": "EntitlementTracker", "confidence": 0.80})
        
    # Zoning Trigger
    if "H-1" in gis_signals.get('zoning', ''):
        triggers.append({"tool": "HospitalityYield", "confidence": 0.70})
        
    return triggers
```

---

## 6. Performance & Latency Targets

| Metric | Target | Method |
| :--- | :--- | :--- |
| **Trigger Emission** | < 150ms | Parallel Heuristic check (Non-LLM) |
| **Wireframe Paint** | < 50ms | Declarative Shadow DOM (No JS req.) |
| **UI Responsiveness** | < 200ms | Streamlit Fragment-level updates |
| **Full Hydration** | < 2.5s | LLM 'Quality' Tier response time |

---

## 7. Success Criteria
- **Perceived Latency:** User surveys indicate the system feels "instant" despite LLM wait times.
- **Layout Stability:** Cumulative Layout Shift (CLS) score remains below 0.1 during hydration.
- **System Pulse:** The 'Agent Bar' shows active "Shadow Assembly" status during speculative phases.
