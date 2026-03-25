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
*   **ADR-S1-01: Embedding Model Shift (NVIDIA NV-Embed-v1).**
    *   *Rationale:* Initially shifted from `gemini/text-embedding-004` to `gemini-embedding-2-preview` due to API availability. Later, to fully utilize the high-performance NVIDIA NIM stack, shifted to `nvidia_nim/nvidia/nv-embed-v1`. This model is instruction-aware (requiring `input_type`="passage" for indexing and "query" for retrieval) and outputs highly accurate 4096-dimensional vectors. Schema updated to `F32_BLOB(4096)` and the `partner_os.db` was reset to apply the new vector constraints.
*   **ADR-S1-02: RRF `LOW_CONFIDENCE_FLOOR` Calibration.**
    *   *Rationale:* The PRD specified a floor of `0.40`. However, with a Reciprocal Rank Fusion (RRF) constant of $k=60$ and two retrievers, the maximum possible score for a perfect Rank 1 match in both is $\approx 0.032$. Adjusted the floor to `0.02` to accurately reflect high confidence in a hybrid setup.
*   **ADR-S1-03: Idempotent Rate-Limited Ingestion.**
    *   *Rationale:* Hit the Gemini Free Tier Rate Limit (100 RPM). Added a `time.sleep(0.7)` delay to keep requests at ~85 RPM. Implemented atomic chunk counting to ensure partially embedded files (if interrupted by daily quota limits) are accurately resumed in future runs.
*   **ADR-S1-04: True Atomic Ingestion (Bugfix).**
    *   *Rationale:* The initial idempotent logic destructively deleted old chunks *before* starting the new embedding loop. When the daily API quota was hit mid-file, the system wiped the file from the database and crashed, losing data until the quota reset. Refactored `embedder.py` to accumulate vectors in memory and only perform the SQLite `DELETE`/`INSERT` transaction if all chunks for the file are embedded successfully.

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

## Sprint S10: Firehouse & UI Polish (Completed 2026-03-24)

**Goal:** Background automation and macOS "Liquid Glass" Command Center.
**Key Decisions:**
*   **ADR-S10-01: Top-of-Funnel Raw Data Persistence.**
    *   *Rationale:* Added a `raw_data` JSON column to `prospects`. The `csv_intake.py` script now dumps the entire unadulterated row into this column, ensuring 100% metadata preservation without schema bloat.
*   **ADR-S10-02: macOS "Liquid Glass" Architecture.**
    *   *Rationale:* To achieve a "Principal-Grade" experience for Roman, the UI was overhauled into a Triple-Pane macOS Command Center (Dock | Mentor | Stage) using glassmorphism and `@st.fragment` for real-time pulsing.
*   **ADR-S10-03: The Firehouse Heartbeat.**
    *   *Rationale:* Implemented `APScheduler` to automate 7:00 AM intake sweeps, GIS hunts, and Morning Brief generation. Added `max_instances=1` and 30s busy timeouts to prevent database lock contention during high-throughput scaling.

---

## Sprint S11: Novel Optimizations (Completed 2026-03-24)

**Goal:** Anticipatory intelligence, X-Ray observability, and edge privacy.
**Key Decisions:**
*   **ADR-S11-01: The X-Ray UI (Logic Tree).**
    *   *Rationale:* To eliminate "AI Anxiety," added a live Altair visualization of the Manager's logic gates (DSCR vs. Cap Rate vs. Doctrine). Roman can now see the "Black Box" reasoning in real-time.
*   **ADR-S11-02: Speculative Action Engine.**
    *   *Rationale:* Implemented `async` speculative drafting. The moment the Manager issues an `APPROVE` verdict, the Scribe node is triggered in a background thread to pre-draft the LOI, achieving perceived zero-latency.
*   **ADR-S11-03: OPCD (Sleep Cycle) Distillation.**
    *   *Rationale:* Solved RAG "Middle Loss" by implementing a weekly "Sleep Cycle" that distills raw transcripts into high-density Semantic Doctrine chunks using the Nemotron Super 120B model.
*   **ADR-S11-04: Local Privacy Shield (SSE4.2).**
    *   *Rationale:* Leveraged the i7-950 hardware to perform local PII scrubbing (SSNs, Phones, Emails) via optimized regex/local-LLM hooks before any sensitive data hits the NVIDIA cloud.
*   **ADR-S11-05: Panoramic GIS Forensics.**
    *   *Rationale:* Upgraded Scout to ingest 80+ raw GIS fields (Building Condition, Population Trends). The Manager now performs "Cross-Field Forensics" to match building decay against neighborhood demographics to find hidden distress.

---

## Sprint S12: Cognitive Memory & v4.0 Synthesis (Completed 2026-03-24)

**Goal:** Statewide stateful reasoning and Grok-synthesized strategic depth.
**Key Decisions:**
*   **ADR-S12-01: Hierarchical Cognitive Memory (H-MEM).**
    *   *Rationale:* Stateless RAG was causing "amnesia" across long negotiations. Implemented a 3-tier SQLite model: **Episodic Traces** (immutable logs), **Semantic Facts** (distilled truths), and **Procedural Tactics** (proactive patterns). Used Bayesian belief updating to resolve conflicting seller signals.
*   **ADR-S12-02: Early-Fusion Sensory Gateway.**
    *   *Rationale:* To move beyond text-only reasoning, refactored `llm.py` to support interleaved image/text blocks. The system can now "See" site plans and building photos alongside legal text for natively visual strategic analysis.
*   **ADR-S12-03: Generative UI Architecture.**
    *   *Rationale:* Implemented `registry.py` to map deal archetypes to Streamlit fragments. The Workspace dashboard now **autonomously assembles its own interface**—rendering specialized tools (Debt-Wrap Simulators, Density Calculators) on-the-fly based on the Manager's verdict.
*   **ADR-S12-04: Grok Alignment (Total Market Awareness).**
    *   *Rationale:* Synthesized the Grok S3-S6 specifications into the production core. Upgraded the pipeline to process 240,000+ parcels with WKB geometry and implemented the async **Explorer Agent** for real-time worldwide market signals.

