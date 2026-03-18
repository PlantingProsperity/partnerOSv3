import sqlite3
import sqlite_vec
import shutil
import datetime
from pathlib import Path
from typing import Optional
import config

def get_connection(db_path: Path = config.DB_PATH) -> sqlite3.Connection:
    """
    Returns a SQLite connection with WAL mode, sqlite-vec loaded,
    and all performance/security pragmas applied.
    """
    # Ensure data directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check for pending migrations and auto-backup (ADR-H04)
    # Note: Migration logic will be expanded in Chunk 2 implementation
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    # Load sqlite-vec extension
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    
    # Apply PRAGMAs from v3.2 spec
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Apply hardware-tuned cache size (ADR-M01)
    conn.execute(f"PRAGMA cache_size = {config.DB_CACHE_SIZE}")
    
    return conn

def init_db(schema_path: Path = config.BASE_DIR / "src/database/schema.sql"):
    """
    Initializes the database with the schema.sql DDL.
    """
    db_path = config.DB_PATH
    if db_path.exists():
        db_path.unlink()
        
    conn = get_connection()
    # Must be set before tables are created for a new DB
    conn.execute("PRAGMA auto_vacuum = INCREMENTAL")
    
    with open(schema_path, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"Database initialized at {config.DB_PATH} with auto_vacuum=INCREMENTAL")

def backup_before_migration():
    """
    ADR-H04: Timestamped snapshot before schema changes.
    """
    if config.DB_PATH.exists():
        timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_path = config.DATA_DIR / f"partner_os.db.pre_migration.{timestamp}"
        shutil.copy2(config.DB_PATH, backup_path)
        return backup_path
    return None

if __name__ == "__main__":
    init_db()
