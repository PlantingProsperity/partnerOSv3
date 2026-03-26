# PRD: Gentrification Velocity Scraper (P3_F2)

**Status:** Draft | **Version:** 1.0 | **Author:** Gemini CLI | **Date:** March 26, 2026
**Pillar:** Pillar 3: The "Shadow Intelligence" Edge
**Goal:** Detect neighborhood "Path of Progress" using high-frequency social sentiment and commercial permit data before it reflects in lagging property price indices.

---

## 1. Executive Summary
The **Gentrification Velocity Scraper** is an anticipatory intelligence tool designed to identify sub-market price appreciation triggers. By monitoring "Digital Gossip" (Nextdoor/Yelp sentiment) and "Physical Capital" (Coffee Shop permits/Artisanal retail), the system generates a **Gentrification Velocity Score (GVS)**. This score allows Roman to acquire assets in neighborhoods *just as* the tipping point is reached, but *before* the market price-in.

---

## 2. 'Social Sentiment Proximities' (The Digital Vibe)
### 2.1 Lexicon-Based Sentiment Analysis
The system employs a specialized NLP model (Neighborhood-BERT) trained on urban development discourse.

*   **Positive Velocity Signals (Weight: 0.7 - 1.0):**
    *   *Aesthetic Keywords:* "Artisanal," "Third-wave," "Exposed brick," "Minimalist," "Industrial-chic."
    *   *Lifestyle Keywords:* "Yoga studio," "Dog cafe," "Organic market," "Walkability," "Bike-friendly."
    *   *Real Estate Keywords:* "Hidden gem," "Up-and-coming," "Investor special," "Revitalized."
*   **Negative/Stagnation Signals (Weight: -0.5 - -1.0):**
    *   "Liquidation," "Cash only," "Pawn shop," "Boarded-up," "Vacancy."

### 2.2 The 'Nimby-Yimby' Conflict Ratio
Nextdoor and Local Facebook Groups are scraped for sentiment regarding new developments.
*   **Nimby Intensity:** High volume of "Not in my backyard" posts indicates high demand but restricted supply, leading to price spikes.
*   **Yimby Momentum:** High volume of "Yes in my backyard" or pro-transit sentiment indicates a political path of least resistance for redevelopment.
*   **The Conflict Pivot:** A shift from purely Nimby to a mix of Nimby/Yimby debate often precedes a zoning change or major infrastructure project.

---

## 3. The 'Coffee Shop Index' Logic
### 3.1 Permit Correlation Engine
The system tracks the correlation between **Artisanal Business Permits** and **Property Price Spikes**.

*   **The "Double-Shot" Trigger:**
    *   1st Coffee Shop (Independent/Specialty) in a 0.5-mile radius = **+0.5% projected appreciation** within 6 months.
    *   3rd Coffee Shop (Independent/Specialty) = **Inflection Point.** The neighborhood has transitioned from "Emerging" to "Gentrified."
*   **Permit Description NLP (High-Impact Keywords):**
    *   "Outdoor seating," "Facade modernization," "Open-concept conversion," "Luxury finishes," "Tenant improvement for boutique retail."
*   **NAICS Code Allow-list:**
    *   `722513` (Limited-Service Restaurants - specifically filtered for Coffee/Tea).
    *   `445291` (Baked Goods Stores).
    *   `448120` (Women's Clothing Stores - Boutique).

---

## 4. Technical Architecture
### 4.1 Scraper Allow-list
*   **Municipal Data:**
    *   OpenData Portals (NYC OpenData, LA Open Data) for Building Permits and Business Licenses.
    *   Zoning Board of Appeals (ZBA) meeting minutes.
*   **Social/Commercial:**
    *   **Yelp API:** Tracking "Price Level" ($$$) shifts and "Opening Soon" markers.
    *   **Nextdoor/X:** Geotagged sentiment regarding local amenities and safety.
    *   **Instagram:** Density of "Vibe-Check" geotags (aesthetic-focused posts).
*   **Real Estate:**
    *   Zillow/Redfin: Price-per-sqft trends for correlation.

### 4.2 NLP Signal-to-Score Mapping
| Signal Type | NLP Confidence | GVS Impact | Action |
| :--- | :--- | :--- | :--- |
| **New Specialty Coffee Permit** | 95% | +15 pts | High Confidence Growth Signal |
| **Sentiment Shift: "Gentrified"** | 80% | +10 pts | Lagging Indicator (Exit Strategy?) |
| **High Nimby Conflict** | 70% | +5 pts | Supply Constraint Warning |
| **Zoning Application: Multi-Family** | 100% | +20 pts | Major Structural Value Shift |

---

## 5. UI: The 'Progress Velocity' Dashboard
### 5.1 Widget Components
*   **The GVS Speedometer:** 0-100 score indicating the rate of change in the last 90 days.
*   **Heat Map Overlay:** Layers "Coffee Shop Density" over "Median List Price." Areas with high density but low prices are flagged as **"S0 Opportunity Zones."**
*   **The "Vibe" Feed:** A real-time ticker of high-weight sentiment snippets (e.g., *"Just saw a new organic grocer opening on 5th!"*).

---

## 6. Implementation Roadmap
1.  **Phase 1 (Ingestion):** Build adapters for NYC/LA OpenData and Yelp API.
2.  **Phase 2 (NLP):** Fine-tune Llama-3 (or similar) on the gentrification lexicon.
3.  **Phase 3 (Correlation):** Backtest GVS against historical Zillow data (2020-2025).
4.  **Phase 4 (UI):** Integrate the "Progress Velocity" widget into the Command Deck.

---

## 7. Success Metrics
*   **Lead Time:** System detects price movement 4-6 months before Zillow/Redfin indices.
*   **Accuracy:** 80% correlation between High GVS and actual 12-month appreciation > 5%.
*   **Alpha:** Identification of at least 3 "Shadow Neighborhoods" per quarter not yet covered by major real estate publications.
