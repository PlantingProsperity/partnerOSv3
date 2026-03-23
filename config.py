import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent.resolve()
DATA_DIR       = BASE_DIR / "data"
DB_PATH        = DATA_DIR / "partner_os.db"
CHECKPOINT_DB_PATH = DATA_DIR / "checkpoints.sqlite"
KNOWLEDGE_DIR  = BASE_DIR / "knowledge"
STAGING_DIR    = BASE_DIR / "staging" / "inbox"
INBOX_DIR      = STAGING_DIR
LISTS_DIR      = STAGING_DIR / "lists"
DEALS_DIR      = BASE_DIR / "deals"

# ── LLM Provider (NVIDIA Native Architecture) ─────────────────────────────────
# We have eliminated the generic PRIMARY_PROVIDER toggle.
# Every agent is explicitly mapped to the most capable model for its specific task
# on the NVIDIA API catalog to maximize performance and avoid rate limits.

AGENT_MODELS = {
    # Fast & Efficient Reasoning (Classification & Support)
    "librarian": "nvidia_nim/meta/llama-4-maverick-17b-128e-instruct", # Native multimodal ingestion
    "profiler": "nvidia_nim/nvidia/mistral-nemo-minitron-8b-8k-instruct", # Rapid RAG analysis
    
    # High-Throughput Agentic Reasoning (The "Forensic" & "Firehouse" Tiers)
    "cfo_p1": "nvidia_nim/qwen/qwen3-coder-480b-a35b-instruct", # Rigid JSON adherence
    "prospect_sourcer": "nvidia_nim/meta/llama-4-scout-17b-16e-instruct", # 10M token context window
    "scribe": "nvidia_nim/nvidia/nemotron-3-super-120b-a12b", # Fast agentic prose
    
    # The Frontier Generalists (The "Principal" Tier)
    "manager": "nvidia_nim/deepseek-ai/deepseek-v3.1-terminus" # Deep logic synthesis
}

# Embeddings NEVER change to preserve vector math.
EMBEDDING_MODEL: str = "nvidia_nim/nvidia/llama-nemotron-embed-1b-v2"
EMBEDDING_DIM:   int  = 2048

# Reranking (Second stage retrieval)
RERANK_MODEL:    str  = "nvidia_nim/nvidia/llama-nemotron-rerank-1b-v2"

LOCAL_BASE_URL: str = os.environ.get("LOCAL_BASE_URL", "http://localhost:8080")

# ── Brain / RAG ───────────────────────────────────────────────────────────────
CHUNK_SIZE:           int   = 800   # characters
CHUNK_OVERLAP:        int   = 150   # characters
RAG_TOP_K:            int   = 5     # chunks returned per retrieval query
LOW_CONFIDENCE_FLOOR: float = 0.02  # below this RRF score → low_confidence=True

# ── Financial Thresholds ──────────────────────────────────────────────────────
CFO_DSCR_FLOOR:     float = 1.15  # below this → below_dscr_floor=True
CFO_CAP_RATE_FLOOR: float = 0.06  # below 6% cap rate → below_cap_floor=True

# ── Prospect / Firehouse Cadence ──────────────────────────────────────────────
FOLLOWUP_DAYS:         int = 21  # days between Bird Letter rounds
WORLD_LETTER_DAYS:     int = 90  # days between World Letter cycles
INVESTOR_CONTACT_DAYS: int = 30  # days before investor appears in Morning Brief

# ── Memory Management (tuned for i7-950, 11GB RAM) ───────────────────────────
DB_CACHE_SIZE:           int = -2097152  # 2GB in kibibytes (negative = KiB per SQLite docs)
PLAYWRIGHT_MAX_CONTEXTS: int = 1         # hard cap — one browser context at a time
PLAYWRIGHT_PAGE_TIMEOUT: int = 30_000    # ms — maximum time to wait for page load
PLAYWRIGHT_SELECTOR_TIMEOUT: int = 10_000    # ms — maximum time to wait for element

# ── Database Maintenance ──────────────────────────────────────────────────────
DB_AUTO_VACUUM:       str   = "INCREMENTAL"
DB_VACUUM_SCHEDULE:   str   = "0 3 * * 0"  # cron: weekly Sunday 3 AM
DB_MAX_SIZE_WARN_GB:  float = 8.0          # log warning if partner_os.db exceeds this

# ── Backup ────────────────────────────────────────────────────────────────────
BACKUP_SCHEDULE:       str = "0 2 * * *"  # cron: daily 2 AM
BACKUP_CHECK_SCHEDULE: str = "0 4 1 * *"  # cron: monthly 1st at 4 AM
RESTIC_REPO:           str = str(DATA_DIR / "backups")
RCLONE_SYNC_TIMEOUT:   int = 300           # ms — ADR-H02

# ── Gemini Budget (v3.2) ──────────────────────────────────────────────────────
GEMINI_DAILY_TOKEN_BUDGET:   int = 1_000_000
GEMINI_AUDIO_TOKEN_WARNING:  int = 800_000
