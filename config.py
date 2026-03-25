import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent.resolve()
DATA_DIR       = BASE_DIR / "data"
DB_PATH        = DATA_DIR / "partner_os.db"
print(f"DEBUG_CONFIG: DB_PATH resolved to {DB_PATH.absolute()}")
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
    # The Principal Tier (Strategic Orchestration)
    "manager": "nvidia_nim/deepseek-ai/deepseek-v3.1-terminus",

    # The Underwriting Enclave (Rigid JSON Extraction)
    "cfo_p1": "nvidia_nim/qwen/qwen3-coder-480b-a35b-instruct",

    # The Sensory Layer (Multimodal Ingestion)
    "librarian": "nvidia_nim/meta/llama-4-maverick-17b-128e-instruct",

    # The Firehouse Tier (High-Throughput Hunt)
    "prospect_sourcer": "nvidia_nim/meta/llama-4-scout-17b-16e-instruct",
    "profiler": "nvidia_nim/meta/llama-4-scout-17b-16e-instruct",

    # Support & Drafting
    "scribe": "nvidia_nim/nvidia/nemotron-3-super-120b-a12b"
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

# ── AI Budget (v3.2) ──────────────────────────────────────────────────────
DAILY_TOKEN_BUDGET:   int = 1_000_000
AUDIO_TOKEN_WARNING:  int = 800_000

# ── Clark County Data Ingestion (Sprint S3) ──────────────────────────────────
PACS_ZIP_URL = "https://gis.clark.wa.gov/openDataHub/PacsData/PACS_OpenData.zip"
GIS_VOL1_URL = "https://www.arcgis.com/sharing/rest/content/items/aac861841b8041b581cda3f05632e016/data"
GIS_VOL2_URL = "https://www.arcgis.com/sharing/rest/content/items/c31b0716734c4cb19069c390d18e1353/data"
ARCGIS_REST_ROOT = "https://gis.clark.wa.gov/arcgisfed/rest/services"
REFRESH_CRON = "0 3 * * 3"  # First Wednesday 3 AM (matches county monthly cadence)

ARCGIS_LAYERS = {
    "taxlots": f"{ARCGIS_REST_ROOT}/ClarkView_Public/TaxlotsPublic/MapServer/0",
    "centroids": f"{ARCGIS_REST_ROOT}/ClarkView_Public/Centroid/MapServer/0",
    "zoning": f"{ARCGIS_REST_ROOT}/ClarkView_Public/Zoning/MapServer/0",
    "building_footprints": f"{ARCGIS_REST_ROOT}/ClarkView_Public/BuildingFootprints/MapServer/0",
}

