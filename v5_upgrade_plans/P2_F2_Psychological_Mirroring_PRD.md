# PartnerOS v5.0 PRD | Pillar 2: Psychological Mirroring
**Feature ID:** P2-F2
**Status:** Granular Specification
**Date:** 2026-03-27

## 1. Executive Summary
'Psychological Mirroring' (PM) is the "Emotional Pro-forma" of PartnerOS. While Pillar 2's Recursive Negotiation Simulation (P2-F1) solves the *math* of a deal, PM solves the *motivation*. By utilizing the **Hierarchical Cognitive Memory (H-MEM)** to classify counterparties into specific CRE-centric psychological archetypes, the system automates **Linguistic Mirroring** and **'Pain Column' Extraction**. The goal is to transition the Principal from a 'Master-Slave' (vendor) dynamic to a 'Partner-Partner' (trusted advisor) relationship, ensuring the "Hole in the Line" is found where the counterparty’s emotional logic meets the deal’s mathematical reality.

---

## 2. Technical Research Foundation

### 2.1 The CRE Power Dynamic (Hegelian Dialectics)
The system is built on the transition from adversarial to consultative negotiation:
- **Master-Slave (Vendor Trap):** The prospect views the Principal as a commodity. The Principal is reactive, "chasing" the deal, and subject to high fee sensitivity.
- **Partner-Partner (Strategic Advisor):** The Principal uses **Inversion Selling** and **Takeaway Techniques** to make the prospect prove their motivation. PM automates the linguistic cues needed to maintain this posture.

### 2.2 Linguistic Mirroring & DISC
PM utilizes the DISC framework (Dominance, Influence, Steadiness, Compliance) as a baseline, then overlays it with **Linguistic Style Matching (LSM)**. The system calculates the match score between the Principal’s communications and the counterparty’s H-MEM baseline to build instant rapport or strategically create distance.

### 2.3 'Pain Column' Extraction
The 'Pain Column' is the hidden driver behind a transaction. PM uses **Natural Language Inference (NLI)** to pivot from surface-level objections (e.g., "Price is too low") to deep-seated pain (e.g., "The capital gains tax will wipe out my retirement").

---

## 3. User Stories

### 3.1 The Legacy Seller
**User:** Roman (Principal)
**Scenario:** Negotiating with a seller who inherited a neglected apartment building.
**Story:** As a Principal, I want the system to flag the "Musty Inheritor" archetype based on H-MEM facts, so I can automatically receive "Stewardship-focused" talking points that emphasize legacy preservation over cold math.

### 3.2 The Institutional Exit
**User:** Investment Associate
**Scenario:** Drafting a follow-up to a REIT asset manager.
**Story:** As a User, I want the 'Scribe' to mirror the "Professional Liquidator" tone—concise, data-heavy, and high-velocity—so my proposal isn't rejected by a committee that values efficiency over relationship.

---

## 4. Archetype Classification Engine (NIM)

The system utilizes **NVIDIA NIM (Llama-3-70B)** to categorize counterparties based on **H-MEM Semantic Facts** and **Episodic Traces**.

| Archetype | H-MEM Signal (Facts) | DISC Profile | Pain Column |
| :--- | :--- | :--- | :--- |
| **The Musty Inheritor** | Owned 30+ years; Legacy name; No recent permits. | S (Steady) | Fear of legacy loss; sibling disputes; tax trap. |
| **The Professional Liquidator** | REIT/LLC owned; Held < 3 years; High-velocity exit. | D (Dominant) | Fund deadline; yield underperformance; reallocation. |
| **The Tired Landlord** | Personal ownership; Multiple code violations; Low rents. | C/S (Cautious) | Operations fatigue; tenant drama; rent control fear. |
| **The Institutional Shadow** | Large portfolio; Committee-based language; Slow response. | C (Analytical) | Career risk; policy compliance; "Check-the-box" logic. |

---

## 5. H-MEM Fact-to-Tactic Cross-Matrix

| H-MEM Semantic Fact | Detected Archetype | Negotiation Tactic | Mirroring Vocab |
| :--- | :--- | :--- | :--- |
| `owner_tenure > 25yr` | Musty Inheritor | **Stewardship Play:** Offer SOS to keep income. | "Legacy," "Heritage," "Stewardship," "Care." |
| `exit_deadline_detected` | Professional Liquidator | **Velocity Play:** Fast close; "As-Is" No-Contingency. | "Certainty," "Velocity," "Clean Exit," "Execution." |
| `rent_control_jurisdiction` | Tired Landlord | **The Relief Valve:** Master Lease / Option to buy. | "Freedom," "Peace of Mind," "Exit the drama." |
| `committee_approval_req` | Institutional Shadow | **The Safe Bet:** Data-backed pro-forma; Case studies. | "Standardized," "Compliant," "Historical Comp." |

---

## 6. Tone-of-Voice (ToV) Specifications

### 6.1 Musty Inheritor (The Steward)
- **Pace:** Slow, deliberate.
- **Focus:** Emotional security, future of the family name.
- **Linguistic Cue:** "I understand this property has been in your family since '92. We aren't just looking at the bricks; we're looking at the legacy you've built."

### 6.2 Professional Liquidator (The High-Velocity Closer)
- **Pace:** High-velocity, blunt.
- **Focus:** IRR, NPV, Certainty of Closing.
- **Linguistic Cue:** "We've audited the pro-forma. We match your $X exit price with a 15-day close. No re-trades. Are we moving?"

---

## 7. NIM Prompt Engineering (Psychological Mirror)

**System Prompt for `mirroring_engine`:**
```text
You are the 'Psychological Mirror' for PartnerOS. 
1. Access H-MEM Facts for [CounterpartyID].
2. Identify Archetype: Musty Inheritor, Professional Liquidator, Tired Landlord, or Institutional Shadow.
3. Apply DISC-aligned LSM (Linguistic Style Matching).
4. If Archetype == 'Musty Inheritor', prioritize 'Legacy' vocabulary and 'SOS' deal structures.
5. If Archetype == 'Professional Liquidator', prioritize 'Velocity' and 'Certainty'.
6. Extract the 'Pain Column' by asking 2 deep-probing questions about their non-monetary exit goals.
```

---

## 8. Success Criteria
- **Archetype Accuracy:** >90% agreement between NIM classification and manual Principal audit.
- **LSM Engagement:** 25% increase in counterparty response rate when mirroring is active.
- **Pain Extraction:** At least one "Non-Price Motivation" (Pain Column) must be identified in H-MEM before a 2nd-round offer is generated.
- **Dynamic Transition:** HUD must visually update Archetype color-coding in real-time as H-MEM facts are confirmed during a live call.
