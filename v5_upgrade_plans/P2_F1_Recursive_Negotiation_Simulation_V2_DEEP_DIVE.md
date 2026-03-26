# PartnerOS v5.0 | P2_F1 Recursive Negotiation Simulation (V2 - DEEP DIVE)
**Status:** Advanced Specification / Pillar 2 Phase II
**Lead Architect:** Gemini CLI (Restored)

## 1. Executive Summary & Research Foundation
The Recursive Negotiation Simulation (RNS) is a high-fidelity 'Transaction Engineering' engine. It automates the Greg Pinneo "Lateral Move" philosophy by navigating the 'Negotiation State-Space' through recursive branching.

### 1.1 IS-MCTS for Asymmetric Information
To handle "Hidden Motivation" (Asymmetric Information), RNS utilizes **Information Set Monte-Carlo Tree Search (IS-MCTS)**.
- **Information Sets:** Nodes do not represent single states but "Belief Sets" of the seller's true position (e.g., hidden debt, urgency levels).
- **Determinization:** The system runs multiple "Parallel Realities" of the negotiation, each assuming a different seller "Fact Set," and identifies deal structures that win across the highest probability distributions.

### 1.2 Reinforcement Learning from Play (RLFP)
RNS employs **Reinforcement Learning from Play (RLFP)** using NIM-guided Foundation Priors.
- **Social Priors:** LLM-based "Common Sense" constraints prevent the bot from proposing insulting or illegal structures.
- **Pinneo Priors:** The system is pre-loaded with the "Hole in the Line" heuristic—prioritizing 'Terms' (SOS, Interest) over 'Price' when resistance is encountered.
- **Self-Play:** The 'Shadow Negotiator' agent plays 10,000+ simulated rounds against archetype models to refine its "Strategic Intuition."

---

## 2. Simulation Playground Backend
The 'Simulation Playground' is a sandboxed environment where the system "stress-tests" a deal before it is presented.

### 2.1 Counter-Archetype Engine
The system generates a 'Mock Seller' agent based on H-MEM data (e.g., 'Musty Inheritor' or 'Professional Liquidator').
- **Mirroring Logic:** The 'Mock Seller' uses the counter-archetype's specific 'Pain Column' (e.g., Fear of Tax, Desire for Legacy) to reject offers that don't solve their emotional pro-forma.
- **Stress-Testing:** The system identifies "Break Points" where the seller's math fails, then recursively branches to find a lateral move.

---

## 3. Algorithmic Detail & Hyperparameters

### 3.1 Branching Probability Model
- **Dirichlet Distribution:** Used to weight the search across [Price, Interest, SOS, Duration].
- **UCT (Upper Confidence Bound for Trees):** $Q(s, a) + C \sqrt{\ln(N(s)) / N(s, a)}$. 
  - **Transition Probability:** Probability of a move being accepted is modeled via a Bayesian update of the seller's archetype receptivity.

### 3.2 Legal Logic Validator
- **Wrap/Sos Guardrails:** A hybrid validator combining Regex anchors (for usury/foreclosure compliance) and NIM-based 'Semantic Audits' to ensure the 'SOS' clause is legally enforceable in Clark County, NV.
- **Validation Rule:** "If Structure == 'Wrap', Check Equity Gap > 15% AND Interest Delta >= 1%."

### 3.3 NIM Hyperparameters (Llama-3-70B-Instruct)
- **Creative Branching (Tactical Expansion):** 
  - `Temperature`: 0.75 (Encourages "Lateral" thinking)
- **Heuristic Anchoring (Drafting/Finalization):**
  - `Temperature`: 0.15 (Ensures mathematical and legal precision)

---

## 4. Implementation Success Criteria
- **Simulation Convergence:** MCTS must converge on a "Winning Branch" within 1.5 seconds.
- **Deal Viability:** Recursive structures must show a minimum 3% yield improvement over the base offer.
- **Transparency:** The UI must display the "Shadow Branching Map" showing rejected paths and their associated "Risk of Friction" scores.
