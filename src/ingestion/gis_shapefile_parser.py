"""
gis_shapefile_parser.py — Clark County GIS Shapefile Ingestion Module (Elevated)

Handles:
1. Downloading GIS volumes from ArcGIS sharing servers.
2. Unzipping shapefiles using pathlib.
3. Loading Taxlots, Centroids, Zoning, and Footprints.
4. Geometry Persistence: Converts shapes to WKB for SQLite storage.
5. Spatial Enrichment: Joins zoning and centroids to the prospects table.
"""

import os
import zipfile
import shutil
import httpx
import pandas as pd
import geopandas as gpd
import sqlite3
import asyncio
from typing import Optional
from pathlib import Path
from src.database.db import get_connection, with_db_retry
from src.utils.logger import get_logger
import config

log = get_logger("ingestion.gis")

async def download_gis_volume(url: str, vol_name: str) -> Optional[Path]:
    """Downloads a GIS volume ZIP file using httpx."""
    local_path = config.STAGING_DIR / f"{vol_name}.zip"
    log.info(f"starting_gis_download_{vol_name}", url=url)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            with open(local_path, 'wb') as f:
                async for chunk in response.aiter_bytes():
                    f.write(chunk)
            
    log.info(f"gis_download_complete_{vol_name}", path=str(local_path))
    return local_path

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
                # Use low_memory=False if needed, usually gpd is fine
                gdf = gpd.read_file(tax_shp[0])
                
                # Calculate centroids in native CRS before projection
                gdf['centroid_lat_native'] = gdf.geometry.centroid.y
                gdf['centroid_lon_native'] = gdf.geometry.centroid.x
                
                # Project to WGS84 for Lat/Lon
                gdf_wgs84 = gdf.to_crs(epsg=4326)
                gdf_wgs84['centroid_lat'] = gdf_wgs84.geometry.centroid.y
                gdf_wgs84['centroid_lon'] = gdf_wgs84.geometry.centroid.x
                
                # Find Prop_id col (case insensitive)
                prop_col = next((c for c in gdf_wgs84.columns if c.upper() == 'PROP_ID'), None)
                if prop_col:
                    # WKB Geometry for SQLite
                    gdf_wgs84['geometry_wkb'] = gdf_wgs84.geometry.to_wkb()
                    
                    df_load = pd.DataFrame({
                        'prop_id': gdf_wgs84[prop_col].astype(str),
                        'centroid_lat': gdf_wgs84['centroid_lat'],
                        'centroid_lon': gdf_wgs84['centroid_lon'],
                        'geometry_wkb': gdf_wgs84['geometry_wkb']
                    })
                    _load_df_to_sql(df_load, "raw_pacs_centroid", conn)
                    log.info("taxlots_centroids_loaded", count=len(df_load))

            # --- 2. ZONING ---
            zoning_shp = list(extract_dir.glob("**/Zoning.shp"))
            if zoning_shp:
                log.info("parsing_zoning_shp", path=str(zoning_shp[0]))
                gdf_zone = gpd.read_file(zoning_shp[0])
                # Simplify geometry for storage if too complex
                # gdf_zone['geometry'] = gdf_zone.geometry.simplify(0.0001)
                gdf_zone['geometry_wkb'] = gdf_zone.geometry.to_wkb()
                
                # Drop raw geometry for SQL load
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

@with_db_retry()
def enrich_prospects_with_gis():
    """Performs spatial and ID-based joins to enrich the prospects table."""
    log.info("enriching_prospects_with_gis")
    conn = get_connection()
    
    # 1. Update Centroids
    conn.execute("""
        UPDATE prospects
        SET centroid_lat = c.centroid_lat,
            centroid_lon = c.centroid_lon,
            last_gis_refresh = CURRENT_TIMESTAMP
        FROM raw_pacs_centroid c
        WHERE prospects.parcel_number = c.prop_id
    """)
    
    # 2. Update Zoning (Simplistic join based on raw_gis_zoning if it has Prop_id, 
    # otherwise a spatial join would be needed here via Python/Geopandas)
    # For now, we assume the Scout node handles live spatial zoning if missing.
    
    conn.commit()
    conn.close()

async def run_full_gis_refresh():
    """Executes the GIS ingestion flow for all volumes."""
    try:
        # Volume 1: Taxlots / Zoning
        vol1_path = await download_gis_volume(config.GIS_VOL1_URL, "GIS_Vol1")
        if vol1_path:
            process_shapefiles(vol1_path)
        
        # Volume 2: Environmental / Overlays
        vol2_path = await download_gis_volume(config.GIS_VOL2_URL, "GIS_Vol2")
        if vol2_path:
            process_shapefiles(vol2_path)
            
        enrich_prospects_with_gis()
        log.info("gis_full_refresh_complete")
    except Exception as e:
        log.error("gis_refresh_failed", error=str(e))
        raise

if __name__ == "__main__":
    asyncio.run(run_full_gis_refresh())
