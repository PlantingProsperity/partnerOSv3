# Nemotron Issue Remediation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the five stability and resilience fixes identified by Nemotron across the API, ingestion, state management, and database layers.

**Architecture:** Targeted surgical updates to existing modules to add error boundaries, deep merging, and robust retry mechanisms without altering the core business logic.

**Tech Stack:** Python 3.12+, httpx, geopandas, sqlite3.

---

## Chunk 1: Database and State Foundation

### Task 1: Database Retry Robustness (`db.py`)

**Files:**
- Modify: `partner_os/src/database/db.py`

- [ ] **Step 1: Write the updated implementation**

Update `with_db_retry` in `src/database/db.py` to add jitter, precise exception checking, and improved logging:

```python
import random

def with_db_retry(max_retries: int = 5, delay: float = 0.1):
    """
    Decorator to retry database operations if the database is locked.
    Includes exponential backoff with jitter to prevent thundering herds.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e).lower():
                        retries += 1
                        current_delay = delay * (2 ** retries) + random.uniform(0, 1)
                        log.warning("db_lock_retry", attempt=retries, delay=round(current_delay, 2), func=func.__name__)
                        time.sleep(current_delay)
                        continue
                    raise e
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

- [ ] **Step 2: Commit**

```bash
cd partner_os
git add src/database/db.py
git commit -m "fix(db): add jitter and precise locking check to with_db_retry"
```

### Task 2: State Merging Accuracy (`state.py`)

**Files:**
- Modify: `partner_os/src/graph/state.py`

- [ ] **Step 1: Write the updated implementation**

Replace the shallow `merge_dicts` with a deep merge function, and add type hints/docstrings:

```python
from typing import TypedDict, Annotated, List, Dict, Any, Optional

def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively deep merges two dictionaries. 
    Nested dictionaries are merged rather than overwritten.
    """
    res = a.copy()
    for k, v in b.items():
        if k in res and isinstance(res[k], dict) and isinstance(v, dict):
            res[k] = merge_dicts(res[k], v)
        else:
            res[k] = v
    return res

def merge_lists(a: List[Any], b: List[Any]) -> List[Any]:
    """Combines two lists via simple concatenation."""
    return a + b
```

- [ ] **Step 2: Commit**

```bash
cd partner_os
git add src/graph/state.py
git commit -m "fix(state): implement deep recursive merge for graph state dicts"
```

---

## Chunk 2: API and Ingestion Resilience

### Task 3: Clark County API Reliability (`clark_county_api.py`)

**Files:**
- Modify: `partner_os/src/integrations/clark_county_api.py`

- [ ] **Step 1: Write the updated implementation**

Apply the 4 fixes to `fetch_parcel_by_prop_id` and other relevant functions:

```python
# Fix 1: Wrap transformer and empty ring guard
    lat, lon = None, None
    rings = geom.get('rings', [])
    if rings and len(rings) > 0 and rings[0] and len(rings[0]) > 0:
        avg_x = sum(pt[0] for pt in rings[0]) / len(rings[0])
        avg_y = sum(pt[1] for pt in rings[0]) / len(rings[0])
        try:
            lon, lat = TRANSFORMER.transform(avg_x, avg_y)
        except Exception as e:
            log.error("coordinate_transform_failed", error=str(e), prop_id=prop_id)
            lat, lon = None, None

# Fix 2: Multiple features guard
    features = data.get('features', [])
    if not features:
        return None
    if len(features) > 1:
        log.warning("multiple_features_returned", prop_id=prop_id, count=len(features))
        
    f = features[0]
    attrs = f.get('attributes', {})
    geom = f.get('geometry', {})
```

Ensure safe dictionary `.get()` accesses are used throughout `fetch_sale_history` and `fetch_bulk_parcels` (e.g., replace `f['attributes']` with `f.get('attributes', {})`).

- [ ] **Step 2: Commit**

```bash
cd partner_os
git add src/integrations/clark_county_api.py
git commit -m "fix(api): harden clark county api parsing and geometry handling"
```

### Task 4: Firehouse Job Resilience (`firehouse_jobs.py`)

**Files:**
- Modify: `partner_os/src/firehouse/firehouse_jobs.py`

- [ ] **Step 1: Write the updated implementation**

Update `check_data_freshness` with timeouts, error catching, ETag normalization, and a `finally` block for the DB connection:

```python
async def check_data_freshness():
    """
    Daily check for remote PACS update using httpx HEAD.
    """
    log.info("starting_daily_freshness_check")
    remote_etag = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.head(config.PACS_ZIP_URL)
            r.raise_for_status()
            raw_etag = r.headers.get('ETag') or r.headers.get('Last-Modified')
            if raw_etag:
                remote_etag = raw_etag.strip(' "\'')
    except httpx.RequestError as e:
        log.error("freshness_check_network_error", error=str(e))
        return
    except Exception as e:
        log.error("freshness_check_failed", error=str(e))
        return
        
    conn = get_connection()
    try:
        last_success = conn.execute("""
            SELECT ts, message FROM maintenance_log 
            WHERE job_name = 'pacs_ingest' AND success = 1 
            ORDER BY ts DESC LIMIT 1
        """).fetchone()
        
        is_fresh = False
        if last_success and remote_etag:
            # Clean the stored message to safely compare
            stored_msg = str(last_success[1]).replace('"', '').replace("'", "")
            is_fresh = remote_etag in stored_msg
            
        log.info("freshness_check_complete", is_fresh=is_fresh, etag=remote_etag)
        
        if not is_fresh and remote_etag:
            log.info("update_detected_triggering_pacs_refresh")
            
    finally:
        conn.close()
```

- [ ] **Step 2: Commit**

```bash
cd partner_os
git add src/firehouse/firehouse_jobs.py
git commit -m "fix(jobs): add timeout, etag normalization, and safe db closing to freshness check"
```

### Task 5: GIS Shapefile Parser Safety (`gis_shapefile_parser.py`)

**Files:**
- Modify: `partner_os/src/ingestion/gis_shapefile_parser.py`

- [ ] **Step 1: Write the updated implementation**

Refactor `process_shapefiles` to remove the broad retry, add explicit cleanup, and use a targeted retry helper:

```python
import shutil

@with_db_retry()
def _load_df_to_sql(df, table_name, conn):
    df.to_sql(table_name, conn, if_exists="replace", index=False)

def process_shapefiles(zip_path: Path):
    """Extracts and parses multiple GIS shapefiles with WKB persistence."""
    extract_dir = config.STAGING_DIR / "gis_extracted"
    
    try:
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            
        conn = get_connection()
        try:
            # --- 1. TAXLOTS & CENTROIDS ---
            tax_shp = list(extract_dir.glob("**/*TaxlotsPublic.shp"))
            if tax_shp:
                log.info("parsing_taxlots_shp", path=str(tax_shp[0]))
                gdf = gpd.read_file(tax_shp[0])
                # ... (existing geometry logic)
                df_load = pd.DataFrame({...})
                _load_df_to_sql(df_load, "raw_pacs_centroid", conn)
                log.info("taxlots_centroids_loaded", count=len(df_load))
            
            # --- 2. ZONING ---
            zoning_shp = list(extract_dir.glob("**/Zoning.shp"))
            if zoning_shp:
                log.info("parsing_zoning_shp", path=str(zoning_shp[0]))
                gdf_zone = gpd.read_file(zoning_shp[0])
                gdf_zone['geometry_wkb'] = gdf_zone.geometry.to_wkb()
                df_zone = pd.DataFrame(gdf_zone.drop(columns='geometry'))
                _load_df_to_sql(df_zone, "raw_gis_zoning", conn)
                log.info("zoning_data_loaded")

            # --- 3. BUILDING FOOTPRINTS ---
            bldg_shp = list(extract_dir.glob("**/BuildingFootprints.shp"))
            if bldg_shp:
                log.info("parsing_footprints_shp", path=str(bldg_shp[0]))
                gdf_bldg = gpd.read_file(bldg_shp[0])
                df_bldg = pd.DataFrame(gdf_bldg.drop(columns='geometry'))
                _load_df_to_sql(df_bldg, "raw_gis_footprints", conn)
                log.info("footprint_data_loaded")
        finally:
            conn.close()
            
    except Exception as e:
        log.error("shapefile_processing_failed", error=str(e), path=str(zip_path))
    finally:
        # Cleanup extraction directory
        if extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)
```
*(Remove `@with_db_retry()` from `process_shapefiles` definition if it's there)*

- [ ] **Step 2: Commit**

```bash
cd partner_os
git add src/ingestion/gis_shapefile_parser.py
git commit -m "fix(ingest): isolate db retries and ensure zip cleanup on failure"
```

### Task 6: Final Verification

- [ ] **Step 1: Run complete test suite**

Run the full battery to ensure no regressions were introduced by these structural hardening fixes.

```bash
cd partner_os
source .venv/bin/activate
export PYTHONPATH=$PYTHONPATH:.
pytest tests/ -v
```
Expected: All tests pass.
