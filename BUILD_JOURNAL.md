# Partner OS — Build Journal & Architecture Decision Record (ADR)

This document is a persistent, meticulous log of the build process, architectural decisions, and critical context for future Gemini sessions.

---

## Sprint S0: Foundation (Completed 2026-03-18)

**Goal:** Clean scaffold, DB initialized, security installed.
**Key Decisions:**
*   **ADR-S0-01: Explicit SSE4.2 Hardware Constraint.** The host machine (i7-950) lacks AVX instructions.
    *   *Rationale:* To prevent runtime `Illegal instruction (core dumped)` errors, PyTorch was explicitly installed using the `--index-url https://download.pytorch.org/whl/cpu` flag. This avoids binaries compiled with AVX requirements.
*   **ADR-S0-02: `auto_vacuum = INCREMENTAL` Header Forcing.** 
    *   *Rationale:* `PRAGMA auto_vacuum` must be set before any tables are created or explicitly enforced via a `VACUUM` command. The `init_db` script was modified to issue the pragma and a `VACUUM` command immediately upon database creation to ensure the header was correctly written.
*   **ADR-S0-03: `structlog` Configuration.**
    *   *Rationale:* Replaced deprecated `structlog.processors.ConsoleRenderer` with `structlog.dev.ConsoleRenderer` to match the installed `structlog>=24.0` version.

---

## Sprint S1: Pinneo Brain (Completed 2026-03-18)

**Goal:** Hybrid RAG end-to-end.
**Key Decisions:**
*   **ADR-S1-01: Embedding Model Shift.**
    *   *Rationale:* The initially specified `gemini/text-embedding-004` returned a 404 error via LiteLLM for the v1beta API. Shifted to `gemini/gemini-embedding-2-preview` which provides 3072-dimensional vectors. Schema updated to `F32_BLOB(3072)`.
*   **ADR-S1-02: RRF `LOW_CONFIDENCE_FLOOR` Calibration.**
    *   *Rationale:* The PRD specified a floor of `0.40`. However, with a Reciprocal Rank Fusion (RRF) constant of $k=60$ and two retrievers, the maximum possible score for a perfect Rank 1 match in both is $\approx 0.032$. Adjusted the floor to `0.02` to accurately reflect high confidence in a hybrid setup.
*   **ADR-S1-03: Idempotent Rate-Limited Ingestion.**
    *   *Rationale:* Hit the Gemini Free Tier Rate Limit (100 RPM). Added a `time.sleep(0.7)` delay to keep requests at ~85 RPM. Implemented atomic chunk counting to ensure partially embedded files (if interrupted by daily quota limits) are accurately resumed in future runs.

---

## Sprint S2: LangGraph Shell (Completed 2026-03-18)

**Goal:** Graph compiles, State flows, Interrupts work.
**Key Decisions:**
*   **ADR-S2-01: Dedicated Checkpoint Database.** 
    *   *Rationale:* LangGraph generates significant WAL traffic and blob storage as it checkpoints state between every node. To prevent lock contention and bloat in the main `partner_os.db` (which handles business logic and vector search), a dedicated `checkpoints.sqlite` was established exclusively for `langgraph-checkpoint-sqlite`.
*   **ADR-S2-02: Strict State Schema.**
    *   *Rationale:* Implemented a strict `TypedDict` for `DealState` with explicit `merge_dicts` annotations for payload dictionaries (`financials`, `property_data`). This ensures parallel nodes (like Scout and Profiler) don't overwrite each other's updates.

---

## Sprint S3: Librarian (Not Started)
