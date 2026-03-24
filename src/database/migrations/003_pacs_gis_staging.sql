-- Migration 003: PACS & GIS Staging Tables
-- Date: 2026-03-24

-- 1. Property Abstract (The Master Index)
CREATE TABLE IF NOT EXISTS raw_pacs_abstract (
    prop_id           TEXT PRIMARY KEY,
    geo_id            TEXT,
    prop_type_cd      TEXT,
    prop_status_cd    TEXT,
    tax_area_id       INTEGER,
    tax_area_number   TEXT,
    appraised_val     REAL,
    assessed_val      REAL,
    land_val          REAL,
    imprv_val         REAL,
    total_acres       REAL,
    legal_desc        TEXT,
    neighborhood_cd   TEXT,
    absentee_ind      TEXT,
    year_built        INTEGER,
    living_area       REAL
);

-- 2. Sales History (For hold_years calculation)
CREATE TABLE IF NOT EXISTS raw_pacs_sales (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    prop_id           TEXT,
    sale_date         TEXT,
    sale_price        REAL,
    doc_number        TEXT,
    deed_type         TEXT,
    validity_cd       TEXT,
    neighborhood_cd   TEXT,
    prop_class        TEXT
);
CREATE INDEX IF NOT EXISTS idx_pacs_sales_prop_id ON raw_pacs_sales(prop_id);

-- 3. Improvement Details (Building Forensics)
CREATE TABLE IF NOT EXISTS raw_pacs_imprv (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    prop_id           TEXT,
    bldg_id           TEXT,
    yr_built          INTEGER,
    eff_yr_built      INTEGER,
    bldg_type         TEXT,
    sqft              REAL,
    basement_sf       REAL,
    garage_sqft       REAL,
    bedrooms          INTEGER,
    bathrooms         REAL,
    foundation        TEXT,
    exterior_wall     TEXT,
    roof_type         TEXT,
    heat_type         TEXT
);
CREATE INDEX IF NOT EXISTS idx_pacs_imprv_prop_id ON raw_pacs_imprv(prop_id);

-- 4. Market Values (History/Trends)
CREATE TABLE IF NOT EXISTS raw_pacs_value (
    prop_id           TEXT,
    mkt_val_land      REAL,
    mkt_val_imprv     REAL,
    mkt_val_total     REAL,
    tax_val_land      REAL,
    tax_val_imprv     REAL,
    tax_val_total     REAL,
    appraisal_year    INTEGER,
    tax_year          INTEGER,
    PRIMARY KEY (prop_id, tax_year)
);

-- 5. Centroids (WGS84 Coordinates)
CREATE TABLE IF NOT EXISTS raw_pacs_centroid (
    prop_id           TEXT PRIMARY KEY,
    x_coord           REAL,
    y_coord           REAL,
    area_sqft         REAL,
    area_acres        REAL,
    centroid_lat      REAL, -- WGS84
    centroid_lon      REAL  -- WGS84
);

-- 6. Enrich the main prospects table
ALTER TABLE prospects ADD COLUMN centroid_lat REAL;
ALTER TABLE prospects ADD COLUMN centroid_lon REAL;
ALTER TABLE prospects ADD COLUMN zoning_code TEXT;
ALTER TABLE prospects ADD COLUMN flood_risk TEXT;
ALTER TABLE prospects ADD COLUMN last_pacs_refresh TEXT;
ALTER TABLE prospects ADD COLUMN rest_query_last_hit TEXT;

-- Register migration
INSERT OR IGNORE INTO schema_migrations (migration_id, applied_at) VALUES ('003_pacs_gis_staging', CURRENT_TIMESTAMP);
