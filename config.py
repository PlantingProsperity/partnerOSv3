import os
from pathlib import Path

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

# ── LLM Provider ──────────────────────────────────────────────────────────────
PRIMARY_PROVIDER: str = os.environ.get("PRIMARY_PROVIDER", "gemini")

# Fast models (classification, transcription)
GEMINI_FLASH: str = "gemini/gemini-flash-latest"

# Quality models (extraction, reasoning)
GEMINI_PRO:   str = "gemini/gemini-pro-latest"

# Mapping for LiteLLM (unified interface)
FAST_MODEL: str = {
    "gemini":     GEMINI_FLASH,
    "groq":       "groq/llama-3.3-70b-versatile",
    "openrouter": "openrouter/deepseek/deepseek-chat-v3-0324:free",
    "local":      "openai/local-model",
}.get(PRIMARY_PROVIDER, GEMINI_FLASH)

QUALITY_MODEL: str = {
    "gemini":     GEMINI_PRO,
    "groq":       "groq/llama-3.3-70b-versatile",
    "openrouter": "openrouter/deepseek/deepseek-chat-v3-0324:free",
    "local":      "openai/local-model",
}.get(PRIMARY_PROVIDER, GEMINI_PRO)

# Embeddings NEVER change with PRIMARY_PROVIDER.
EMBEDDING_MODEL: str = "gemini/gemini-embedding-2-preview"
EMBEDDING_DIM:   int  = 3072

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
