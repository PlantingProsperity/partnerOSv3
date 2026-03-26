# PartnerOS v5.0 PRD | Pillar 2: Recursive Negotiation Simulation
**Feature ID:** P2-F1
**Status:** Draft / Granular Specification
**Date:** 2026-03-27

## 1. Executive Summary
'Recursive Negotiation Simulation' (RNS) is an advanced deal-structuring engine that automates the "Lateral Move" philosophy of Greg Pinneo. When a primary deal structure (e.g., a standard cash-on-cash offer) fails to meet a seller's price expectations or an investor's yield requirements, RNS recursively generates and tests 10+ alternative structures. By utilizing Monte-Carlo Tree Search (MCTS) and high-throughput NVIDIA NIM inference, the system explores the "State-Space" of terms (Interest, SOS, Slice and Dice) to find the "Hole in the Line" where math and motivation align.

---

## 2. Technical Research Foundation

### 2.1 Pinneo-Aligned Lateral Structures
The system is encoded with three core "Pinneo-isms" as foundational deal primitives:
- **Substitution of Security (SOS):** A clause allowing the borrower to move the note's collateral to a different property. RNS uses this to maintain low-interest debt across multiple assets, essentially creating a "Bank of You."
- **Hole in the Line:** A heuristic for negotiation agility. If the "Price" line is defended, RNS searches for a "Hole" in terms (e.g., deferred interest, secondary beneficiaries, or solving a non-monetary problem).
- **Substitution of Collateral (The "Tomato"):** Swapping the requested asset (cash) for a desired alternative (e.g., a specific vehicle or payment of a specific debt) to reduce the principal balance.

### 2.2 Monte-Carlo Tree Search (MCTS) for Negotiation
Unlike linear decision trees, RNS uses MCTS to navigate the "Negotiation State-Space":
1.  **Selection:** Identify the most promising "Tactic Archetype" (e.g., "The Income Streamer" vs. "The Cash Out").
2.  **Expansion:** Generate 10+ child nodes representing specific term permutations (Price vs. Interest vs. Duration).
3.  **Simulation (Playout):** Run rapid pro-forma simulations on each node to check IRR/NPV targets.
4.  **Backpropagation:** Rank the structures based on "Yield-to-Friction" scores.

---

## 3. User Stories

### 3.1 The "Impossible" Seller
**User:** Roman (Principal)
**Action:** Inputs a seller's firm "All-Cash" demand that kills the pro-forma.
**Story:** As a Principal, I want the system to automatically trigger a "Recursive Branching" phase that tests SOS and 'Slice and Dice' scenarios, so I can present 3 alternative paths to the seller that achieve their cash goals while preserving my yield.

### 3.2 The "Yield Optimization" Audit
**User:** Investment Associate
**Action:** Reviews a generated LOI.
**Story:** As a User, I want to see a "Strategic Branching Map" showing the 10+ failed structures the system tested and why they were rejected, so I can understand the mathematical boundaries of the deal.

---

## 4. Strategic Branching Logic (The Algorithm)

### 4.1 State-Space Search Parameters
The system explores a multi-dimensional matrix:
- **P (Price):** $X to $Y (±20% of Market).
- **I (Interest):** 0% to 8% (Step: 0.25%).
- **D (Down Payment):** $0 to $Z (Step: $5,000).
- **L (Lettuce & Tomatoes):** [SOS, Right of First Refusal, Slice/Dice, Deferred Interest].

### 4.2 Tactic-Archetype Mapping
| Archetype | Primary Signal | Lateral Move |
| :--- | :--- | :--- |
| **The Income Streamer** | Elderly Seller / Estate Planning | High Price + Low Interest + SOS |
| **The Debt Killer** | High Underlying Debt | Low Down + Wrap Note + SOS |
| **The Portfolio Builder** | Seller wants to stay active | Slice and Dice + Partnership Option |
| **The Tax Shield** | High Capital Gains Concern | Installment Sale + 1031 Integration |

---

## 5. NIM Prompt Engineering (Shadow Negotiator)

The system utilizes **NVIDIA Llama-3-70B-Instruct (NIM)** to behave as a "Shadow Negotiator" during the branching phase.

**System Prompt Snippet:**
```text
You are the 'Shadow Negotiator' for PartnerOS. Your goal is to find the 'Hole in the Line'.
When Price is fixed, move to Terms. 
Specifically, utilize the 'Substitution of Security' (SOS) heuristic. 
If the user's pro-forma fails at 6% interest, recursively test 4% with a 10% higher price, 
then test 2% with SOS privileges.
Output your reasoning in a 'Strategic Branching Map' format.
```

---

## 6. Performance & Latency Targets

| Metric | Target | Method |
| :--- | :--- | :--- |
| **Branch Generation (10+ paths)** | < 800ms | Parallel NIM Inference (Batch) |
| **Pro-forma Simulation** | < 100ms | Vectorized NumPy Math |
| **MCTS Convergence** | < 1.5s | 500 iterations per deal-state |
| **Final LOI Drafting** | < 3s | 'Scribe' node (Llama-3-70B) |

---

## 7. Success Criteria
- **Deal Viability:** At least one "Recursive Branch" must pass the minimum 12% IRR threshold when the primary offer fails.
- **Narrative Depth:** The generated LOI must explicitly mention the "Substitution of Security" benefit to the seller's long-term security.
- **Transparency:** The UI provides a "Shadow Branching" view showing the mathematical win-loss record of each simulated offer.
