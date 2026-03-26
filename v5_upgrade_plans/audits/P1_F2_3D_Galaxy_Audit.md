# Audit Report: 3D Deal Galaxy (P1_F2)
**Date:** 2026-03-25
**Status:** Pivot Required

## 1. Critique
- **SCOPE:** Infeasible as a runtime browser process. UMAP on 240k points will exceed browser memory and CPU limits. Lack of AVX on i7-950 will cause significant lag.
- **FEASIBILITY:** High Risk. 3D force-directed physics is impossible at this scale on 11GB RAM.
- **COMPLEXITY:** Strategic value is high, but performance-dependent.

## 2. Proposed Improvements
- **Decoupled UMAP Pipeline:** Perform dimensionality reduction on the Python backend using `pynndescent` (SSE4.2 optimized) and cache results.
- **Binary Streaming:** Deliver coordinates as `Float32Array` blobs instead of JSON.
- **Strategic LOD:** Abandon individual Mesh nodes for a single `THREE.Points` object. Use a GPU Octree to promote interactive spheres only when nearby.
- **Memory-Mapped Buffers:** Store metadata in `SharedArrayBuffer` to keep data outside the heavy V8 heap.

**Conclusion:** Move from dynamic physics to static spatial visualization using pre-computed coordinates and shader-based point clouds.
