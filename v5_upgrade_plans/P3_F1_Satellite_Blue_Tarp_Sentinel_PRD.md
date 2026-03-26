# PartnerOS v5.0 PRD | Pillar 3: Environmental Distress & Physical Signals
**Feature ID:** P3-F1
**Status:** Draft / Granular Specification
**Date:** 2026-03-27

## 1. Executive Summary
'Satellite Blue Tarp Sentinel' (SBTS) is a high-fidelity physical distress detection engine that monitors real estate assets via orbital and aerial imagery. By automating the identification of 'Blue Tarps' (post-disaster roof damage) and 'Vegetation Overgrowth' (NDVI-based neglect signals), SBTS provides the 'Scout' node with empirical evidence of owner distress before it manifests in public records (e.g., code violations or foreclosures). This feature transforms the PartnerOS pipeline from a reactive record-fetcher into a proactive visual intelligence platform.

---

## 2. Technical Research Foundation

### 2.1 Satellite & Aerial Provider Stratification
The system utilizes a multi-tiered ingestion strategy to balance cost, resolution, and latency:
- **Sentinel-2 (Tier 1 - Macro):** Open-source (Free) multispectral data with a 5-day revisit cycle. Used for baseline NDVI (Normalized Difference Vegetation Index) monitoring and detecting large-scale land-use shifts. Resolution: 10m/pixel.
- **SkyFi (Tier 2 - Micro Tasking):** On-demand satellite marketplace. Used for high-resolution verification (30cm - 50cm) when a Tier 1 signal or external distress trigger (tax delinquency) is detected. Latency: <24 hours.
- **Nearmap (Tier 3 - Historical Audit):** High-resolution aerial imagery (5.5cm - 7.5cm) with oblique (45-degree) views. Used for sub-meter physical audits (e.g., identifying individual debris piles or boarded windows) during the 'Deep Due Diligence' phase.

### 2.2 Computer Vision (CV) Model Requirements
SBTS employs a specialized CV pipeline for feature extraction:
- **Blue Tarp Detection:** A Convolutional Neural Network (CNN) based on the **U-Net architecture** (trained on FEMA xBD datasets). It achieves >90% precision in identifying blue spectral signatures on rooftops, acting as a proxy for 'Moderate to Major' storm damage.
- **Vegetation Overgrowth (NDVI):** Automated pixel-level analysis comparing the Near-Infrared (NIR) reflectance to Red light. 
    - **Formula:** $NDVI = (NIR - Red) / (NIR + Red)$
    - **Distress Signal:** Values between 0.2 and 0.5 that persist beyond typical mowing cycles (14–21 days) or deviate significantly from the mown-lawn baseline of neighboring parcels.

---

## 3. User Stories

### 3.1 The "Post-Storm Alpha" Hunter
**User:** Roman (Principal)
**Scenario:** A major hurricane just passed through a target market in Florida.
**Story:** As a Principal, I want the system to scan 5,000 target properties via Sentinel-2 and flag the 50 properties with the highest "Blue Tarp" density within 72 hours of the storm, so I can send "Fast-Cash" LOIs to owners before insurance adjusters arrive.

### 3.2 The "Zombie Foreclosure" Sentinel
**User:** Acquisitions Lead
**Scenario:** Monitoring a portfolio of off-market multifamily leads.
**Story:** As a User, I want to receive an "Escalation Alert" when a property's NDVI score rises by 40% compared to its neighbors over a 90-day period, indicating the property has been abandoned and the landscaping is no longer maintained.

---

## 4. Image Ingestion & Analysis Architecture

### 4.1 Tiered Pipeline Flow
1.  **Macro-Scan (Sentinel-2):** Every 5 days, the system fetches NDVI tiles for all 'Watchlist' properties.
2.  **Anomaly Detection:** A Python-based `DistressAnalyzer` compares the current NDVI/RGB tiles against a 2-year rolling historical baseline.
3.  **High-Res Trigger:** If an anomaly (e.g., Blue Tarp candidate or Overgrowth) is detected, the system automatically tasks a **SkyFi High-Res capture** ($20–$50) for the specific parcel.
4.  **CV Inference:** The High-Res image is passed through the U-Net model (for Tarps) and a ResNet classifier (for Debris/Neglect).
5.  **Evidence Packaging:** The system crops the High-Res image into an 'Evidence Card' for the UI.

### 4.2 API Cost-Benefit Analysis
| Provider | Cost per SQ KM | Resolution | Use Case |
| :--- | :--- | :--- | :--- |
| **Sentinel-2** | $0.00 | 10m | Macro-Trend / Baseline |
| **SkyFi** | $20.00 - $50.00 | 30cm - 50cm | Active Verification |
| **Nearmap** | Subscription | 5.5cm | Pre-LOI Audit |

---

## 5. Distress Trigger Pipeline (Motivation Escalation)

The 'Motivation Score' ($M$) is escalated from 'Market Average' ($M_{avg} = 0$) to 'High Motivation' ($M > 70$) based on visual decay:

| Signal Type | Weight ($W$) | Escalation Condition |
| :--- | :--- | :--- |
| **Blue Tarp** | +40 | Detected via CV (Confidence > 0.85) |
| **NDVI Overgrowth** | +25 | Persistence > 60 days vs. Neighborhood Mean |
| **Debris Accumulation** | +15 | Visible trash/piles in high-res (SkyFi) |
| **Boarded Openings** | +30 | Detected via Nearmap Oblique views |
| **Swimming Pool Decay** | +20 | Transformation from "Cyan" to "Deep Green/Black" |

**Escalation Logic:**
`Final Motivation = Base_GIS_Score + Σ(Satellite_Weights * Confidence_Multiplier)`

---

## 6. UI 'Evidence' Rendering

The PartnerOS Dashboard renders visual distress in a high-impact 'Evidence HUD':
- **Side-by-Side (B/A):** Shows the property 1 year ago vs. Current (highlighting neglect).
- **NDVI Heatmap:** A false-color overlay where red/orange indicates mowed grass and bright green indicates wild overgrowth within the property lines.
- **CV Bounding Boxes:** Bounding boxes around identified Blue Tarps or Debris piles with a "Certainty Badge" (e.g., "92% Certainty: Blue Tarp").
- **Physical Health Bar:** A 0-100% health bar where 100% is "Pristine" and <30% triggers the "Distress Sentinel" alert.

---

## 7. Success Criteria & Metrics
- **Detection Precision:** CV model must maintain >85% precision (minimizing false positives from blue swimming pools).
- **Time-to-Alert:** Notification of a Blue Tarp signal must be delivered to the Principal within 12 hours of image availability.
- **Conversion Lift:** Properties flagged by SBTS should show a 2x higher response rate to LOIs compared to standard GIS-only leads.
