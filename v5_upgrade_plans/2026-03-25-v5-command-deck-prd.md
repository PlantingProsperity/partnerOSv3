# PartnerOS v5.0 Pillar 1: The 'Command Deck' Experience
## Product Requirements Document (PRD)

**Date:** March 25, 2026
**Status:** DRAFT

---

## 1. Executive Summary

PartnerOS v4.0 established the "Cognitive Edition," granting the system hierarchical memory and early-fusion sensory architecture. Pillar 1 of v5.0 introduces the **'Command Deck' Experience**, an evolution of the Generative UI into a fully spatial, volumetric environment. 

The Command Deck abandons flat grids in favor of the **Z-Axis Depth Stack** and **Bento-Spatial** patterns. It allows the principals to visualize the entire Clark County prospect database (243,000+ parcels) and active pipeline as a living, breathing **3D Deal Galaxy**. Furthermore, it introduces the **Speculative Shadow Assembly (SSA)**—a spatial workbench where specialized shadow agents autonomously assemble and propose creative financing structures in real-time. This is augmented by a **Real-Time Sentiment HUD** that streams macro and micro market signals directly into the peripheral vision of the interface.

## 2. User Stories

*   **As a Principal**, I want to view my entire prospect database as a 3D cluster map (Deal Galaxy), so I can instantly identify "hot" submarkets or high-equity clusters based on visual density and luminescence.
*   **As a Principal**, when reviewing an active deal, I want the system to seamlessly transition into a focused spatial view (Adaptive GenUI), bringing critical metrics to the foreground while muting background data via depth-of-field.
*   **As a Principal**, when a deal fails conventional underwriting (e.g., low DSCR), I want the Speculative Shadow Assembly to automatically propose alternative structures (e.g., Seller Carry, AITD) as visual "blocks" I can snap into the deal to see the real-time financial impact.
*   **As a Principal**, I want a persistent, low-latency Sentiment HUD that processes news, local economic signals, and order flow, so I can gauge market mood (Fear/Greed) without leaving the Command Deck.

## 3. Feature Specifications

### 3.1. 3D Deal Galaxy
*   **Concept**: A WebGL-powered 3D visualization of the prospect database acting as the primary navigation interface.
*   **Spatial Pattern**: *Vision Arc* and *Z-Axis Depth Stack*.
*   **Mechanics**: 
    *   Prospects are rendered as nodes (stars) within a navigable space.
    *   Node clustering is driven by "Pinneo Similarity" (multidimensional grouping by zoning, equity score, hold years, and archetype).
    *   Z-depth indicates temporal relevance (recent contacts and active negotiations float closer to the camera).
    *   Luminescence/Glow indicates real-time market heat, high motivation, or incoming communications.

### 3.2. Speculative Shadow Assembly (SSA)
*   **Concept**: A volumetric workbench for interactive deal restructuring.
*   **Spatial Pattern**: *Liquid Glass* and *GenUI Adaptive Compression*.
*   **Mechanics**:
    *   When the Manager agent issues a `HARD_FLAG` (from the `pinneo_gate` node), the UI autonomously transitions into SSA mode.
    *   The Deal Galaxy background blurs out (Liquid Glass effect) to reduce cognitive load.
    *   "Shadow Agents" (specialized sub-routines for Terms, Risk, and Exit Strategies) present proposed deal components as 3D geometric blocks.
    *   Principals can interact with these components (drag-and-drop) to "assemble" the final LOI structure, watching live metrics (Cap Rate, DSCR) recalculate instantly based on the visual assembly.

### 3.3. Real-Time Sentiment HUD
*   **Concept**: A non-intrusive peripheral display for actionable market intelligence.
*   **Spatial Pattern**: *Bento-Spatial* floating containers.
*   **Mechanics**:
    *   **Sentiment Gauges**: A Net Sentiment Score (-1 to +1) dial based on hyper-local news and economic feeds.
    *   **Sentiment Heatmaps**: Treemap overlays projected onto the Deal Galaxy showing sector or neighborhood performance.
    *   **Design Principle**: High-signal, low-noise color grading (cool blues/grays for neutral states, bright orange/cyan exclusively for anomalies or extreme sentiment shifts).

## 4. Technical Requirements

### 4.1. Frontend Architecture
*   **Framework**: Streamlit, heavily extended with custom bi-directional components.
*   **3D Engine**: React-Three-Fiber (R3F) and Three.js running inside the Streamlit frontend payload.
*   **Component Bridge**: Utilize `streamlit-component-lib`. 
    *   *Critical:* Implement `Streamlit.setFrameHeight()` dynamically within the React lifecycle to ensure the 3D canvas scales properly and does not collapse to 0px within the iframe.
*   **State Management**: Use `Streamlit.setComponentValue(data)` in React to pass 3D object interactions (e.g., clicking a node in the Galaxy or snapping a block in the SSA) back to the Python backend. This will trigger a re-run of the Streamlit app with the new interaction data, subsequently updating the LangGraph state.

### 4.2. Backend & Data Pipeline
*   **Sentiment Processing**: Implement a low-latency ingestion pipeline. Use an optimized local NLP model like `FinBERT` or batched lightweight calls to `gemini-2.5-flash` to score inbound local news/market data in real-time.
*   **Galaxy Coordinates Engine**: Pre-compute 3D coordinates (X, Y, Z) for the 243k parcels using dimensionality reduction algorithms (e.g., UMAP or t-SNE) on their database feature vectors. Store these coordinates in the `partner_os.db` (`prospects` table) to ensure fast load times.
*   **SSA Agent Output Format**: The `Manager` node in LangGraph must be updated to output structured JSON representing the proposed "blocks" for the SSA (e.g., `[{"type": "AITD", "impact": {"dscr": "+0.15", "cap": "+1.2%"}}]`). The frontend will parse this JSON to render the 3D components.

## 5. Success Metrics

1.  **Rendering Performance**: The 3D Deal Galaxy must maintain a steady 60 FPS while rendering a minimum of 10,000 active nodes concurrently within the Streamlit iframe.
2.  **Interaction Latency**: The bi-directional communication loop (clicking a 3D node -> Streamlit updating the Python state -> UI refresh) must resolve in under 200 milliseconds to preserve the "Command Deck" immersion.
3.  **Strategic Adoption**: Principals utilize the Speculative Shadow Assembly to successfully restructure at least 30% of deals that initially fail the standard `pinneo_gate` heuristics.
4.  **Token Efficiency**: Sentiment HUD processing must utilize aggressive caching and batched LLM calls to remain well within the established 1M daily token budget outlined in v3.2.
