# Audit Report: Pre-Permit Shadow Pipeline (P3_F3)
**Date:** 2026-03-25
**Status:** Hardened

## 1. Critique
- **SCOPE:** LLC graph is often too sparse for meaningful parent-linking via registration alone.
- **FEASIBILITY:** Accela portals are notorious for bot-blocking and heavy JS obfuscation.
- **COMPLEXITY:** WCC algorithm is too basic; misses the nuance of deal clusters.

## 2. Proposed Improvements
- **Address-First Clustering:** Link LLCs sharing UPS/Registered Agent addresses.
- **Weighted Community Detection:** Use Louvain algorithms to handle "Virtual Office" noise.
- **Incremental Graphing:** Only cluster new daily permits to save i7-950 compute resources.
- **Auditor Cross-Ref:** Use Excise tax records to verify developer purchase patterns.

**Conclusion:** Shift to weighted communities and delta-updates for hardware efficiency.
