# PRD: P1_F2_3D_Deal_Galaxy

**Status:** Draft | **Version:** 1.0 | **Owner:** Gemini CLI
**Target:** PartnerOS v5.0 (Command Deck Pillar)

---

## 1. Executive Summary
The **3D Deal Galaxy** is a high-fidelity strategic visualization engine built on Three.js. It transforms a flat list of potential deals into a navigable "Galaxy" where spatial proximity represents strategic similarity. By mapping deal metadata (DISC archetypes, Redevelopment Scores, and SOS receptivity) into 3D coordinates, it allows principals to "fly through" deal constellations to identify clusters of high-probability targets.

---

## 2. User Stories
- **As a Principal (Roman/Daniil),** I want to see how my current deal pipeline clusters by seller psychology so I can apply the same negotiation "playbook" to multiple targets in one session.
- **As a Strategic Architect,** I want to visualize "Holes in the Line" across my entire territory to see where the market is ignoring specific Pinneo-aligned opportunities.
- **As a User,** I want a cinematic "Fly-Through" experience to navigate large datasets without the friction of paginated tables.

---

## 3. 3D Engine Requirements
- **Framework:** [3d-force-graph](https://github.com/vasturiano/3d-force-graph) (Three.js base).
- **Rendering Optimization:** 
    - Use `InstancedMesh` for deal nodes (spheres/stars) to support 10,000+ entities at 60 FPS.
    - Use `LineSegments` for "Strategic Threads" (links between related deals).
    - Post-processing: **Bloom Pass** for "glowing" high-score deals.
- **Navigation:** 
    - **Default:** `OrbitControls` for overview.
    - **Fly-Mode:** `FlyControls` for immersive navigation (WASD + Mouse).
- **Interaction:**
    - **Raycasting:** Hovering over a "star" reveals a Sentiment HUD overlay (Motivation Spikes, DISC Archetype).
    - **Warp Drive:** Clicking a deal triggers a camera tween (GSAP) to focus the view on that node.

---

## 4. Coordinate Mapping Heuristics (The "Constellation" Logic)
To place deals in 3D space, the system uses a 3-axis strategic vector mapped via **UMAP (Uniform Manifold Approximation and Projection)**.

### 4.1 Input Vectors (Feature Space)
| Dimension | Data Source | Weight |
| :--- | :--- | :--- |
| **X: Psychology Cluster** | DISC Archetype (D, I, S, C) + Pinneo Pain Column | 40% |
| **Y: Strategy Alignment** | SOS Receptivity Score + Redevelopment Score | 40% |
| **Z: Financial Gravity** | Debt-to-Equity Ratio + Cash-on-Cash Potential | 20% |

### 4.2 Clustering Heuristics
- **The "Redevelopment Nebula":** High-density clusters where `redevelopment_score > 80`. Nodes glow Red.
- **The "SOS System":** Deals with high `sos_receptivity` (identified by Scribe/Architect) cluster around a central "White Dwarf" representing the ideal Pinneo pivot.
- **The "DISC Quadrants":** The galaxy is loosely divided into four quadrants based on the primary DISC archetype of the seller.

---

## 5. Navigation & UI Integration
- **The Mini-Map:** A 2D orthographic projection in the corner for orientation.
- **Strategic Filters:** Sidebar toggles to "Dim" or "Brighten" deals based on specific criteria (e.g., "Show only SOS targets").
- **Telemetry HUD:** A transparent overlay showing current coordinates and the "Strategic Density" of the local cluster.

---

## 6. Technical Stack
- **Frontend:** Streamlit (Host) + React/Three.js Component.
- **Coordinate Engine:** `umap-js` for dimensionality reduction.
- **Physics:** `d3-force-3d` (integrated into 3d-force-graph).
- **Data Pipeline:** SQL query to `partner_os.db` → JSON → UMAP → 3D Render.

---

## 7. Success Metrics
- **Discovery Velocity:** Time to identify 3 similar deals reduced by 50%.
- **Pattern Recognition:** Principals report identifying "clusters" that were invisible in the 2D dashboard.
- **Frame Rate:** Consistent 60 FPS on v4.0 hardware baseline (i7-950).

---
*End of PRD.*
