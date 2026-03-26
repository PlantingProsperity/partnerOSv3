# Nemotron Issue Remediation — Design Specification
**Date:** 2026-03-25

## 1. Executive Summary
This design specification addresses five distinct areas of technical debt and instability identified by Nemotron within the PartnerOS v4.0 architecture. The fixes target API resilience, file I/O safety, state management accuracy, and database concurrency robustness.

---

## 2. Component Designs

### 2.1 Clark County API Reliability (`src/integrations/clark_county_api.py`)
**Problem:** The API client is fragile when handling geometric transformations and assumes dictionary keys always exist.
**Solution:**
*   **Multiple Features Guard:** Add a check `if len(features) > 1` to log a warning when the API returns multiple results for a supposedly unique ID query, ensuring we explicitly fall back to `features[0]`.
*   **Safe Geometry:** Wrap the `TRANSFORMER.transform(avg_x, avg_y)` call in a `try...except Exception as e` block. On failure, log the error and set `lat, lon = None, None`.
*   **Empty Ring Guard:** Update the centroid calculation logic to `if rings and rings[0] and len(rings[0]) > 0:` to prevent `ZeroDivisionError`.
*   **Safe Dictionary Access:** Replace remaining direct index accesses (e.g., `f['attributes']`) with `.get('attributes', {})`.

### 2.2 GIS Shapefile Parser Safety (`src/ingestion/gis_shapefile_parser.py`)
**Problem:** The `@with_db_retry` decorator wraps an entire function performing disk I/O, which is dangerous and can lead to duplicated unzipping operations if a database lock occurs downstream.
**Solution:**
*   Remove `@with_db_retry` from `process_shapefiles`.
*   Create a targeted helper function `@with_db_retry() def _load_df_to_sql(df, table_name, conn)` to handle the specific SQLite insertions.
*   Wrap the `zipfile.ZipFile` and `gpd.read_file` calls in a `try...except Exception as e:` block to catch corrupted shapefiles.
*   Implement a `finally:` block utilizing `shutil.rmtree(extract_dir, ignore_errors=True)` to ensure partial or corrupted ZIP extractions are always purged from the disk.

### 2.3 State Merging Accuracy (`src/graph/state.py`)
**Problem:** `merge_dicts` performs a shallow update. In a LangGraph environment, this means nested dictionaries (like `financials`) overwrite each other instead of merging.
**Solution:**
*   Rewrite `merge_dicts` using recursion:
    ```python
    def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        res = a.copy()
        for k, v in b.items():
            if k in res and isinstance(res[k], dict) and isinstance(v, dict):
                res[k] = merge_dicts(res[k], v)
            else:
                res[k] = v
        return res
    ```
*   Update type hints for both functions to strict `Dict[str, Any]` and `list`.

### 2.4 Firehouse Job Resilience (`src/firehouse/firehouse_jobs.py`)
**Problem:** Background scheduler jobs lack timeouts and connection safety, risking silent hangs.
**Solution:**
*   Update `httpx.AsyncClient` to `httpx.AsyncClient(timeout=10.0)`.
*   Wrap the `await client.head()` call in a `try...except httpx.RequestError` block to catch network failures without crashing the scheduler.
*   Normalize the ETag by stripping quotes: `remote_etag.strip(' "\'')`.
*   Wrap the database connection logic in a `try...finally:` block to guarantee `conn.close()` is called regardless of execution success.

### 2.5 Database Retry Robustness (`src/database/db.py`)
**Problem:** The `@with_db_retry` backoff lacks jitter, leading to "thundering herd" conditions when multiple concurrent agents hit a lock.
**Solution:**
*   Add jitter to the exponential backoff: `time.sleep(delay * (2 ** retries) + random.uniform(0, 1))`.
*   Make the exception check explicitly exact: `if "database is locked" in str(e).lower():`.
*   Update the log warning to include the current delay and function name for better observability in `maintenance_log`.
