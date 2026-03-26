# PartnerOS v5.0 P1_F3: 'Sentiment HUD' PRD

**Date:** 2026-03-27  
**Status:** Draft / Active Strategy  
**Pillar:** 1 (Hierarchical Cognitive Memory - H-MEM)  
**Author:** Gemini CLI (Autonomous Agent)

---

## 1. Executive Summary
The **'Sentiment HUD' (Heads-Up Display)** is a real-time psychological overlay designed for high-stakes CRE negotiations. It transforms live meeting transcripts into a "Shadow Intelligence" cockpit by cross-referencing streaming NLP signals against the **Hierarchical Cognitive Memory (H-MEM)**. By detecting deception, monitoring alignment, and flagging motivation spikes, the HUD empowers the Principal to identify a "Hole in the Line" (Pinneo Doctrine) before the counterparty even reveals it.

---

## 2. User Stories

| ID | User Story | Acceptance Criteria |
| :--- | :--- | :--- |
| **US.1** | As a Principal, I want to see real-time "Deception Markers" during a call so I can probe areas of hidden pain. | HUD highlights distancing language and non-contracted denials in red-amber gradients. |
| **US.2** | As a Principal, I want to know if a seller's live statements contradict their H-MEM facts. | System triggers a "Fact Conflict" alert when NLI detects a contradiction with stored semantic facts. |
| **US.3** | As a Negotiator, I want a "Negotiation Pulse" wave that spikes when I touch a "Pain Column." | An animated EKG-style wave tracks composite sentiment + H-MEM keyword hits. |
| **US.4** | As a User, I want a high-density, futuristic overlay that doesn't distract from the transcript text. | Styling uses "Liquid Glass" (translucent/blur) and gradient-based HUD panels. |

---

## 3. Negotiation Pulse Logic (H-MEM Cross-Reference)

The 'Negotiation Pulse' is a composite metric derived from the delta between **Live Signals** and **Historical Baselines**.

### 3.1 Input Vector
- **Live Stream:** Real-time transcript chunks (15-30 word windows).
- **H-MEM Context:** 
    - `semantic_facts`: Trait keys like `primary_pain_column`, `psych_archetype`, `exit_timeline`.
    - `episodic_traces`: The last 3-5 interaction summaries to establish a `Linguistic Baseline`.

### 3.2 Logic Flow (NIM-Optimized)
1.  **Linguistic Style Matching (LSM):** Calculate the match score (LSM) between the speaker's current function-word usage and their H-MEM baseline. A drop of >30% triggers a "Strategic Distancing" flag.
2.  **Psychological Marker Extraction:** NIM models (Llama-3-70B-Instruct) scan for:
    - **POS Shifts:** Sudden increase in verbs vs. nouns (storytelling vs. recall).
    - **Cognitive Load:** Detection of pauses, "thinking time" fillers, or over-alignment (parroting).
3.  **H-MEM Fact Validation:** Natural Language Inference (NLI) checks if `live_statement` → `h_mem_fact` is `ENTAILMENT`, `NEUTRAL`, or `CONTRADICTION`.
4.  **Motivation Detection:**
    - `Intensity = Emotional_Magnitude * (Keyword_Match_in_Pain_Column ? 2.5 : 1.0)`.
    - High magnitude near "Pain" keywords (e.g., "taxes", "retirement", "balloon") generates a `Motivation Spike`.

### 3.3 Composite Pulse Score formula
$$Pulse = (LSM \times 0.3) + (1 - Deception\_Prob \times 0.4) + (Intensity \times 0.3)$$
*Values normalized 0.0 to 1.0. High Pulse indicates high alignment and transparency.*

---

## 4. NLP Pipeline Requirements (NVIDIA NIM)

The HUD requires low-latency inference for real-time overlay synchronization.

- **Primary NIM:** `meta/llama-3-70b-instruct` or `nvidia/llama-3-70b-v2` for complex psychological pattern extraction.
- **Sentiment NIM:** `nvidia/sentiment-analysis` for high-velocity polarity and intensity scoring.
- **NLI Engine:** `cross-encoder/nli-deberta-v3-base` (deployed as a NIM-compatible endpoint) for fact-checking.
- **Latency Target:** < 250ms from transcript chunk arrival to HUD render update.

---

## 5. HUD Visual Spec (Design)

### 5.1 Aesthetic: "Shadow Intelligence"
- **Surface:** Glassmorphic panels with `backdrop-filter: blur(12px)`.
- **Gradients (Functional):**
    - `ALIGNMENT`: `linear-gradient(135deg, #00C9FF 0%, #92FE9D 100%)` (Cyan to Mint).
    - `DECEPTION`: `linear-gradient(135deg, #FF9966 0%, #FF5E62 100%)` (Orange to Coral).
    - `SPIKE`: `linear-gradient(135deg, #f093fb 0%, #f5576c 100%)` (Purple to Pink).

### 5.2 Key Components
1.  **The Pulse EKG:** A scrolling SVG path at the bottom of the HUD reflecting the `Pulse Score`.
2.  **Bento Grid Stats (Left Rail):**
    - **Archetype Mirroring:** Percentage match to current H-MEM archetype (Institutional/Legacy/etc).
    - **LSM Stability:** 0-100% stability of linguistic style.
    - **Truth Probability:** Bayesian-updated confidence in the current statement's veracity.
3.  **Annotation Pointers:** Small, gradient-rimmed callouts that point directly to words in the transcript.
    - *Example:* A red underline under "to be perfectly honest" with a tooltip: "Qualifying Language Detected (Distancing Marker)".

---

## 6. Tactical Alert Thresholds

| Alert Type | Trigger | HUD Response |
| :--- | :--- | :--- |
| **CRITICAL CONFLICT** | NLI CONTRADICTION score > 0.85 against H-MEM Fact. | HUD border flashes **Neon Red**; Bento Card shows "FACT CHECK FAILED". |
| **MOTIVATION SPIKE** | Intensity > 0.8 on H-MEM Pain keyword. | EKG wave turns **Golden Gradient**; "HOLE IN THE LINE" alert triggered. |
| **STYLE DRIFT** | LSM Score < 0.5 for 2 consecutive chunks. | HUD background shifts to **Desaturated Amber**; "Possible Strategic Shift" warning. |

---

## 7. H-MEM Integration (Database Updates)

```sql
-- Migration 006: Sentiment HUD (Pillar 1)
ALTER TABLE episodic_traces ADD COLUMN sentiment_payload JSON; 
-- Stores {pulse_score, deception_markers, alignment_delta} for each interaction.

CREATE TABLE IF NOT EXISTS sentiment_benchmarks (
    seller_id       TEXT PRIMARY KEY,
    avg_lsm_score   REAL,
    typical_emotion TEXT,
    pos_distribution JSON, -- {nouns: 0.4, verbs: 0.2, ...}
    last_updated    TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---
*The Sentiment HUD does not lie. It only reveals what is already there.*
