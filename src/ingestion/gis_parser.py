"""
gis_parser.py — Clark County GIS Shapefile Ingestion Module

Handles:
1. Downloading GIS volumes from ArcGIS sharing servers.
2. Unzipping shapefiles.
3. Loading Taxlots, Centroids, and Zoning into staging.
4. Calculating WGS84 (Lat/Lon) centroids for all parcels.
"""

import zipfile
import requests
import pandas as pd
import geopandas as gpd
import sqlite3
from pathlib import Path
from src.database.db import get_connection
from src.utils.logger import get_logger
import config

log = get_logger("ingestion.gis")

def download_gis_volume(url: str, vol_name: str) -> Path:
    """Downloads a GIS volume ZIP file."""
    local_path = config.STAGING_DIR / f"{vol_name}.zip"
    log.info(f"starting_gis_download_{vol_name}", url=url)
    
    r = requests.get(url, stream=True)
    r.raise_for_status()
    
    with open(local_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
            
    log.info(f"gis_download_complete_{vol_name}", path=str(local_path))
    return local_path

def process_shapefiles(zip_path: Path):
    """Extracts and parses multiple GIS shapefiles (Taxlots, Zoning, Footprints)."""
    extract_dir = config.STAGING_DIR / "gis_extracted"
    extract_dir.mkdir(exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    conn = get_connection()
    
    # 1. TAXLOTS & CENTROIDS
    tax_shp = list(extract_dir.glob("**/*TaxlotsPublic.shp"))
    if tax_shp:
        log.info("parsing_taxlots_shp", path=str(tax_shp[0]))
        gdf = gpd.read_file(tax_shp[0])
        # Project to WGS84 for Lat/Lon
        gdf_wgs84 = gdf.to_crs(epsg=4326)
        gdf_wgs84['centroid_lat'] = gdf_wgs84.geometry.centroid.y
        gdf_wgs84['centroid_lon'] = gdf_wgs84.geometry.centroid.x
        
        df_load = pd.DataFrame({
            'prop_id': gdf_wgs84['Prop_id'].astype(str),
            'centroid_lat': gdf_wgs84['centroid_lat'],
            'centroid_lon': gdf_wgs84['centroid_lon']
        })
        df_load.to_sql("raw_pacs_centroid", conn, if_exists="replace", index=False)
        log.info("taxlots_centroids_loaded", count=len(df_load))

    # 2. ZONING
    zoning_shp = list(extract_dir.glob("**/Zoning.shp"))
    if zoning_shp:
        log.info("parsing_zoning_shp", path=str(zoning_shp[0]))
        # We store raw zoning boundaries for spatial joins later
        # For now, we load the attribute table
        gdf_zone = gpd.read_file(zoning_shp[0])
        gdf_zone.to_sql("raw_gis_zoning", conn, if_exists="replace", index=False)
        log.info("zoning_data_loaded")

    # 3. BUILDING FOOTPRINTS
    bldg_shp = list(extract_dir.glob("**/BuildingFootprints.shp"))
    if bldg_shp:
        log.info("parsing_footprints_shp", path=str(bldg_shp[0]))
        gdf_bldg = gpd.read_file(bldg_shp[0])
        # Store essential footprint data
        df_bldg = pd.DataFrame(gdf_bldg.drop(columns='geometry'))
        df_bldg.to_sql("raw_gis_footprints", conn, if_exists="replace", index=False)
        log.info("footprint_data_loaded")

    conn.close()

def run_full_gis_refresh():
    """Executes the GIS ingestion flow for all volumes."""
    try:
        # Volume 1: Taxlots / Zoning
        vol1_path = download_gis_volume(config.GIS_VOL1_URL, "GIS_Vol1")
        process_shapefiles(vol1_path)
        
        # Volume 2: Environmental / Overlays
        vol2_path = download_gis_volume(config.GIS_VOL2_URL, "GIS_Vol2")
        process_shapefiles(vol2_path)
        
        log.info("gis_full_refresh_complete")
    except Exception as e:
        log.error("gis_refresh_failed", error=str(e))
        raise

if __name__ == "__main__":
    run_full_gis_refresh()
