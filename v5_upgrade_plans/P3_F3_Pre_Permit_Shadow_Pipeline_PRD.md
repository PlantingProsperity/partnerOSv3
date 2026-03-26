# PartnerOS v5.0 PRD | Pillar 3: Shadow Intelligence
**Feature ID:** P3-F3
**Status:** Granular Specification / Draft
**Date:** 2026-03-27

## 1. Executive Summary
'Pre-Permit Shadow Pipeline' (P3-F3) is a speculative intelligence layer designed to detect large-scale development intent 3–9 months before a formal permit is filed. By monitoring the "pre-paperwork" phase of land development—specifically 'Early Assistance' meetings and 'Pre-Submittal' conferences—and employing an 'Entity Clustering' engine, the system identifies 'Shadow Assemblies' where major developers accumulate contiguous parcels under multiple anonymous LLCs.

---

## 2. Technical Research Foundation

### 2.1 Clark County (NV) Municipal Ingestion
The system targets the **Clark County Department of Comprehensive Planning** via the **Accela Citizen Access (ACA)** portal.
- **Data Source:** `Pre-Submittal Conference (PSC)` requests. These are mandatory for projects of "Regional Significance" (e.g., 500+ units, resort hotels, or projects requiring RISE reports).
- **Schema Key Fields:**
    - `Record Number:` (e.g., PC-24-XXXX)
    - `Disclosure of Financial Interest (DOFI):` A critical public document listing all individuals/businesses with a >10% stake.
    - `RISE Trigger:` Indicates if a Regional Infrastructure and Services Evaluation is required, signaling high-density impact.
    - `Staff Recommendation Drafts:` Lead time of 3 working days before public hearings.

### 2.2 Developer Entity Clustering
Most major developers (e.g., Howard Hughes, Lennar, Greystar) isolate liability by creating a unique LLC for every parcel acquisition. P3-F3 uses a **Graph-Based Entity Resolution** approach to pierce this veil.
- **Algorithm:** Weakly Connected Components (WCC) via NetworkX/Neo4j.
- **Linkage Logic:**
    - **Hard Link:** Shared 'Registered Agent Address' + Shared 'Principal Office Address'.
    - **Soft Link:** Shared 'Resident Agent Name' (e.g., "John Doe, VP") + Shared Email Domain (extracted from application contact info).
    - **Verification:** Automated Secretary of State (SOS) scraping for 'Statement of Information' updates.

---

## 3. The 'Entity Clustering' Engine Design

### 3.1 'Shadow Footprint' Visual Mapping
The system generates a visual 'Shadow Footprint' in the PartnerOS Command Deck:
- **Ghost Borders:** When the system identifies that Parcels A, B, and C are owned by the same 'Clustered Developer' (despite different LLC names), it renders a dashed 'Ghost Border' around the entire assembly.
- **Intensity Heatmap:** Parcels with active 'Pre-Submittal' conferences are highlighted in pulsing violet ($Intensity \propto Frequency\_of\_Staff\_Contact$).
- **The "Developer Tree":** A modal popup that reveals the 'Ultimate Parent Entity' and the spiderweb of LLCs used to acquire the site.

### 3.2 'Adjacent Leverage' Alerting Logic
The system triggers an `ADJACENT_ASSEMBLY` alert when a cluster expands spatially:
```python
# Pseudo-Logic for Shadow Assembly Detection
if new_acquisition.owner_cluster == existing_parcel.owner_cluster:
    if is_spatially_adjacent(new_acquisition, existing_parcel):
        calculate_assembly_potential(total_area, zoning_delta)
        trigger_alert("Shadow Assembly Detected: Cluster [" + cluster_name + "]")
```

---

## 4. Content & Scraping Specifications

### 4.1 Municipal Scraping Schedule
| Data Type | Source | Frequency | Latency Goal |
| :--- | :--- | :--- | :--- |
| **PSC Requests** | Accela ACA | Daily (02:00 UTC) | <24 Hours |
| **RISE Reports** | Planning Dept | Weekly | <7 Days |
| **DOFI Filings** | Document Image | On-Demand (per PSC) | Instant (OCR) |
| **SOS Updates** | NV Sec of State | Monthly (Rolling) | <30 Days |

### 4.2 Entity Linking Thresholds
The linking confidence score ($C_L$) determines if two LLCs are merged into a 'Shadow Developer' node:
- **Registered Agent Match:** $W = 0.40$
- **Principal Address Match:** $W = 0.50$ (High confidence for non-virtual offices)
- **Officer Name Match:** $W = 0.30$
- **Shared Application Contact:** $W = 0.20$
- **Threshold:** If $C_L > 0.80$, auto-merge. If $0.50 < C_L < 0.80$, flag for 'Manual Audit'.

---

## 5. User Stories

### 5.1 The "Front-Runner" Developer
**User:** Roman (Principal)
**Scenario:** A developer is quietly buying up three 1-acre lots in downtown Las Vegas under "Red Rock 1 LLC", "LV Blue LLC", and "Desert Gold LLC".
**Story:** As a Principal, I want to see these lots outlined in a single 'Ghost Border' on my map the moment the developer requests a 'Pre-Submittal Conference' for a unified 3-acre project, so I can buy the 4th corner lot and force a buyout.

### 5.2 The "Infrastructure Signal" Analyst
**User:** Acquisitions Lead
**Scenario:** Monitoring utility capacity letters (RISE).
**Story:** As a User, I want an alert when a 'RISE Report' is filed for a parcel that currently has no building permit, as this signals the developer is securing water/sewer capacity for a high-density build that hasn't been announced.

---

## 6. Success Criteria & Metrics
- **Early Warning Lead Time:** 120+ days average lead time vs. formal building permit filing.
- **Clustering Accuracy:** >92% precision in linking LLCs to the correct parent entity (measured against SEC Exhibit 21 for public firms).
- **Discovery Rate:** Identify 5+ 'Shadow Assemblies' per quarter in Clark County before they reach the Planning Commission public agenda.
