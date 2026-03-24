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

def process_taxlots(zip_path: Path):
    """Extracts and parses the TaxlotsPublic shapefile."""
    extract_dir = config.STAGING_DIR / "gis_extracted"
    extract_dir.mkdir(exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    # Find the .shp file
    shp_files = list(extract_dir.glob("**/*TaxlotsPublic.shp"))
    if not shp_files:
        log.error("taxlots_shp_not_found")
        return
        
    log.info("parsing_taxlots_shp", path=str(shp_files[0]))
    gdf = gpd.read_file(shp_files[0])
    
    # 1. Calculate centroids in the native PROJECTED CRS (for accuracy)
    # Most Clark County GIS files are in State Plane Feet
    gdf['centroid_lat_native'] = gdf.geometry.centroid.y
    gdf['centroid_lon_native'] = gdf.geometry.centroid.x
    
    # 2. Transform to WGS84 for the final Lat/Lon export
    gdf_wgs84 = gdf.to_crs(epsg=4326)
    gdf_wgs84['centroid_lat'] = gdf_wgs84.geometry.centroid.y
    gdf_wgs84['centroid_lon'] = gdf_wgs84.geometry.centroid.x
    
    # 3. Handle case-insensitive Prop_id (GIS fields are often uppercase)
    prop_col = next((c for c in gdf_wgs84.columns if c.upper() == 'PROP_ID'), None)
    if not prop_col:
        prop_col = next((c for c in gdf_wgs84.columns if 'PARCEL' in c.upper()), None)
        
    if not prop_col:
        log.error("property_id_column_not_found_in_shp", columns=list(gdf_wgs84.columns))
        return

    # 4. Load into DB
    conn = get_connection()
    df_load = pd.DataFrame({
        'prop_id': gdf_wgs84[prop_col].astype(str),
        'centroid_lat': gdf_wgs84['centroid_lat'],
        'centroid_lon': gdf_wgs84['centroid_lon']
    })
    
    df_load.to_sql("raw_pacs_centroid", conn, if_exists="replace", index=False)
    conn.close()
    log.info("taxlots_centroids_loaded", count=len(df_load))

def run_full_gis_refresh():
    """Executes the GIS ingestion flow."""
    try:
        vol1_path = download_gis_volume(config.GIS_VOL1_URL, "GIS_Vol1")
        process_taxlots(vol1_path)
        log.info("gis_full_refresh_complete")
    except Exception as e:
        log.error("gis_refresh_failed", error=str(e))
        raise

if __name__ == "__main__":
    run_full_gis_refresh()
