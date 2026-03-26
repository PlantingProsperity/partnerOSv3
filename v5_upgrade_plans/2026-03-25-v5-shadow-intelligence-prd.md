# PartnerOS v5.0 PRD | Pillar 3: The 'Shadow Intelligence' Edge
**Date:** 2026-03-25
**Status:** Draft / Strategic Design
**Target:** docs/superpowers/specs/2026-03-25-v5-shadow-intelligence-prd.md

## 1. Executive Summary
The 'Shadow Intelligence' Edge (Pillar 3) transforms PartnerOS from a reactive data consumer into a proactive "Submarket Oracle." By fusing low-latency satellite triggers, hyper-local social sentiment, and municipal "pre-permit" data, the system identifies distressed assets and gentrification inflection points 4–6 months before they appear on Zillow, Redfin, or MLS.

---

## 2. Data Source Inventory

### 2.1 Geospatial & Vision Layer
-   **Sentinel-2 (Satellite):** Weekly macro-scans at 10m resolution. Used as a cost-free "Change Trigger" for land clearing and major roof-color shifts.
-   **Nearmap API (Aerial):** On-demand micro-validation at 5.5cm resolution. Used for "Ground Truth" verification of roof condition, pool installation, and unpermitted structures.

### 2.2 Social Sentiment Layer (The Digital Exhaust)
-   **Reddit (PRAW API):** Real-time monitoring of city/neighborhood subreddits for "vibe shift" keywords.
-   **NewsCatcher API:** Hyper-local news scraper (31,000+ sources) for transit announcements, zoning meeting minutes, and boutique business openings.
-   **Nextdoor (Content API):** Search-based tracking of sentiment trends regarding "safety," "new neighbors," and "neighborhood improvement."

### 2.3 Municipal Pipeline
-   **SODA API (Socrata):** Direct ingestion of "Applied" but "Pending" permit status from major city open-data portals (Chicago, Seattle, Austin, etc.).
-   **Custom Scrapers:** Playwright-based automation for legacy Accela/EnerGov portals in smaller jurisdictions.

---

## 3. Ingestion Architecture

### 3.1 The "Trigger & Validate" Loop (Blue Tarp Sentinel)
1.  **Macro-Scan:** Sentinel-2 identifies a spectral shift on a PACS-indexed parcel (e.g., a "Blue" pixel cluster on a residential roof or "Brown" earth-moving on a vacant lot).
2.  **Logic Gate:** If `Confidence > 0.7`, trigger the Nearmap Transactional API.
3.  **Vision Inference:** PartnerOS v4.0 Multimodal Vision (Qwen-VL or similar) analyzes the high-res Nearmap tile to confirm:
    *   **Blue Tarp:** Indicates active roof failure/leak (Distress Signal).
    *   **Foundation Pour:** Indicates new development (Neighborhood Upcycle Signal).
    *   **Debris Pile:** Indicates "Internal Gut" renovation without a permit (Shadow Flip).

### 3.2 The Sentiment Synthesizer (Coffee Shop Index)
1.  **NER Extraction:** Named Entity Recognition extracts new business names and locations from social/news feeds.
2.  **Lexicon Scoring:** A "Gentrification Lexicon" weights mentions:
    *   *Pioneer Terms:* "Artisan," "Roastery," "Industrial-chic," "Yoga."
    *   *Economic Terms:* "Rent hike," "Displacement," "New Whole Foods."
3.  **Aggregation:** Sentiment is mapped to PACS Census Block Groups to create a "Vibe Velocity" score.

---

## 4. Predictive Scoring Heuristics

### 4.1 The 'Blue Tarp' Distress Score (BTDS)
`BTDS = (Blue_Tarp_Pixels * 0.6) + (Days_Since_Storm * 0.3) + (Tax_Delinquency_Status * 0.1)`
-   **Interpretation:** High scores trigger the 'Librarian' to find owner skip-trace data and the 'Scribe' to pre-draft a "We buy roofs" offer.

### 4.2 The 'Coffee Shop' Gentrification Index (CSGI)
`CSGI = (Boutique_Opening_Rate / 12mo) + (Laundromat_Decline_Rate) - (311_Infrastructure_Complaints)`
-   **Lead Indicator:** A 20% increase in CSGI precedes a 5–8% appreciation in median home value within 180 days.

### 4.3 The 'Pending' Pressure Score (PPS)
`PPS = (Sum(Pending_Permit_Valuation) / Neighborhood_Median_Price) * (Average_Pending_Days)`
-   **Interpretation:** High "Pending Pressure" indicates a neighborhood on the verge of a construction explosion. Opportunities for "Subject-To" acquisitions are highest here as owners face rising property taxes.

---

## 5. Success Metrics
-   **Lead Time:** Identify 80% of major renovations 3 months before "Notice of Completion."
-   **Accuracy:** 90% precision in "Blue Tarp" detection vs. manual aerial review.
-   **Alpha:** Outperform ZIP-code average appreciation by 4.5% through "pre-gentrification" selection.

---
*The OS detects the shadow. The principals capture the light.*
