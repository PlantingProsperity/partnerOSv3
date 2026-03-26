# Audit Report: Sentiment HUD (P1_F3)
**Date:** 2026-03-25
**Status:** Hardened

## 1. Critique
- **SCOPE:** "Deception Detection" is too risky; pivot to "Linguistic Variance" or "Veracity Risk."
- **FEASIBILITY:** Llama-3-70B is too slow for 250ms HUD updates. Requires a multi-tier model approach.
- **COMPLEXITY:** LSM is practical but needs a Rolling Baseline to distinguish personality from situational stress.

## 2. Proposed Improvements
- **Sliding Window:** 50-word windows with 25-word overlap to reduce token churn.
- **NIM Minitron 4B:** Use smaller, faster models for high-frequency "Pulse" and sentiment markers.
- **Local-First Triggers:** Instant UI flashes for "Pain Column" keywords using regex/local classifiers.
- **Async Fact-Checking:** Decoupling NLI from the Pulse loop to prevent UI lag.

**Conclusion:** Shift to multi-tier inference to maintain negotiation pace.
