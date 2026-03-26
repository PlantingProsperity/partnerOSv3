# Audit Report: Satellite Blue Tarp Sentinel (P3_F1)
**Date:** 2026-03-25
**Status:** Pivot Required

## 1. Critique
- **SCOPE:** $50/parcel tasking for 240k parcels is economically non-viable.
- **FEASIBILITY:** Sentinel-2 (10m/pixel) cannot reliably detect roof tarps without massive false positives.
- **COMPLEXITY:** Multi-tier tasking adds significant logic overhead.

## 2. Proposed Improvements
- **Cluster-Based Tasking:** Amortize high-res costs by scanning 1km blocks only if 5+ macro-signals occur.
- **Shadow Delta Detection:** Focus on temporal change between images rather than static classification.
- **Pool Decay Monitoring:** Use dark pixel clusters (stagnant pools) as a high-confidence 10m signal for abandonment.
- **Municipal Mirroring:** Verify visual overgrowth against existing code violation logs before tasking high-res.

**Conclusion:** Use satellite as high-confidence evidence for pre-filtered leads rather than primary discovery.
