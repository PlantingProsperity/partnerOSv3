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

## Sprint S3: Librarian (Completed 2026-03-18)

**Goal:** Multimodal intake, filesystem authority, and knowledge maintenance.
**Key Decisions:**
*   **ADR-S3-01: Generic -latest Aliases.**
    *   *Rationale:* Removed hardcoded "gemini-2.5" references from the codebase and documentation. Configured `config.py` to use `gemini-flash-latest` and `gemini-pro-latest` to ensure the system always defaults to Google's most current stable/preview models without requiring manual code updates.
*   **ADR-S3-02: Dual-Hashing Strategy.**
    *   *Rationale:* Implemented SHA-256 chunked hashing in `src/utils/hashing.py` to handle large audio/video files. The hash is used to query the `files` table for rapid system-wide deduplication during the `staging/inbox/` sweep.
*   **ADR-S3-03: Librarian as Knowledge Maintainer.**
    *   *Rationale:* Added `_maintain_knowledge()` to the Librarian class to trigger the `BrainEmbedder` automatically, ensuring the vector database (`brain_chunks`) stays synchronized with the filesystem `knowledge/` directory during standard system sweeps.

---

## Sprint S4: CFO (Completed 2026-03-18)

**Goal:** Financial extraction, verification gate, and deterministic math.
**Key Decisions:**
*   **ADR-S4-01: CFO Hybrid Parsing Router with Graceful Fallback.**
    *   *Rationale:* Pure AI extraction struggles with structured tables, while traditional parsers (`pdfplumber`) fail on messy scanned PDFs. Implemented a hybrid router: `.csv`/`.xlsx` files are parsed deterministically via `pandas` into Markdown text (fast, 100% accurate layout), while `.pdf`/`.jpg` files are passed directly to the Gemini GenAI File API to leverage its superior multimodal vision capabilities for complex unstructured layouts. For plain text (`.txt`, `.md`), it reads them directly. Crucially, if an unknown binary format is encountered, it returns a graceful string placeholder rather than crashing, allowing the Librarian LLM to explicitly classify it as `OTHER` and route to the `unresolved/` queue for human review.
*   **ADR-S4-02: Missing Citation Handling.**
    *   *Rationale:* If the LLM extracts a value but fails to cite it, the system accepts the value but sets the citation to null. This relies on the Phase 2 (Human Verification) UI to flag the missing citation, forcing the principal to verify the hallucination visually, rather than entering an infinite retry loop.
*   **ADR-S4-03: Pydantic Schema Enforcement.**
    *   *Rationale:* Used Pydantic classes to define the exact `CFOExtraction` schema, which will be passed to LiteLLM's structured output parameter to guarantee the JSON shape of the Phase 1 extraction.

---

## Sprint S5: pinneo_gate (Completed 2026-03-18)

**Goal:** Pure Python heuristics evaluation.
**Key Decisions:**
*   **ADR-S5-01: Pure Python Evaluation.**
    *   *Rationale:* Mathematical thresholds (DSCR < 1.15, Cap Rate < 6%) are deterministic rules, not creative tasks. Offloading this check from the Manager LLM to a pure Python node ensures 100% accuracy, saves token costs, executes in < 1ms, and guarantees the Manager always receives explicitly flagged failures rather than having to discover them.
*   **ADR-S5-02: HARD_FLAG pattern.**
    *   *Rationale:* The node does not short-circuit the graph to a `KILL` state. It merely flags the failure in `DealState`. This allows the parallel Scout/Profiler nodes to continue gathering context so the Manager can synthesize a creative "Pinneo structuring" solution to rescue the deal.

---

## Sprint S6: Scout + Profiler (Completed 2026-03-21)

**Goal:** Parallel analysis of external data and seller psychology.
**Key Decisions:**
*   **ADR-S6-01: Local Data Warehouse (Bypassing CAPTCHA).**
    *   *Rationale:* Clark County `gis.clark.wa.gov` aggressively blocks automated web scrapers via Google reCAPTCHA and IP blocks. Building a Playwright scraper would result in a fragile, broken system. Instead, we shifted to a "Local Data Warehouse" strategy. The `clark_county_sync.py` script ingests the monthly bulk data CSV provided by the county into a local SQLite table (`clark_county_cache`). The Scout agent now performs instantaneous, 100% reliable local database queries based on `parcel_number` rather than fragile web scraping.

---

## Sprint S7: Manager Node (Completed 2026-03-21)

**Goal:** Deal synthesis, decision-making, and delegation.
**Key Decisions:**
*   **ADR-S7-01: Manager/Scribe Decoupling.**
    *   *Rationale:* To prevent LLM "attention dilution," the Manager node is strictly prohibited from formatting final documents (like an LOI). Its sole responsibility is to evaluate the board, issue a verdict (`APPROVE` or `KILL`), and output a dense, structured list of `scribe_instructions`. This enforces the Single Responsibility Principle within the multi-agent graph.

---

## Sprint S8: Scribe Node (Completed 2026-03-21)

**Goal:** Generative drafting of formal communications based strictly on Manager instructions.
**Key Decisions:**
*   **ADR-S8-01: Conditional Routing to Scribe.**
    *   *Rationale:* Updated `deal_graph.py` to add a conditional edge after the `manager_node`. If the Manager's verdict is `APPROVE`, the state flows to the `scribe_node` to draft an LOI. If the verdict is `KILL`, the graph terminates immediately. This ensures we don't waste LLM tokens drafting letters for dead deals, and keeps the Manager's context window purely focused on the analytical verdict.

---

## Sprint S9: Streamlit UI (Completed 2026-03-21)

**Goal:** Human-in-the-loop interaction and Deal Pipeline visibility.
**Key Decisions:**
*   **ADR-S9-01: Shared Checkpointer in Session State.**
    *   *Rationale:* Streamlit reruns its entire script top-to-bottom on every button click. To maintain the connection to the active LangGraph threads (specifically for resuming interrupted graphs), the `SqliteSaver` checkpointer is initialized once in `app.py` and attached to `st.session_state`. This ensures the CFO Verification page can accurately query `state.next` to find paused graphs and use `graph.stream(Command(resume=True))` to wake them up without losing context.

---

## Sprint S10: Firehouse (Not Started)
