"""
arcgis_rest_client.py — The 'Secret Entrance' Engine for PartnerOS

Provides sub-second, on-demand property enrichment via public ArcGIS REST APIs.
Bypasses bulk ZIP files for daily scouting tasks.
"""

import requests
import json
import time
from typing import Dict, Optional, Any
from src.utils.logger import get_logger
import config

log = get_logger("ingestion.arcgis_rest")

class ArcGISClient:
    """
    Lightweight client for querying Clark County FeatureServers.
    """
    def __init__(self):
        self.base_url = config.ARCGIS_REST_ROOT
        self.layers = config.ARCGIS_LAYERS

    def _make_query(self, layer_url: str, where: str, out_fields: str = "*") -> Optional[Dict]:
        """Internal helper for REST queries."""
        url = f"{layer_url}/query"
        params = {
            "where": where,
            "outFields": out_fields,
            "f": "json",
            "returnGeometry": "false"
        }
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            if data.get("features"):
                return data["features"][0].get("attributes")
            return None
        except Exception as e:
            log.error("arcgis_query_failed", url=url, error=str(e))
            return None

    def get_parcel_details(self, parcel_number: str) -> Optional[Dict]:
        """
        Sub-second enrichment for a specific parcel.
        Used by the Scout agent.
        """
        log.info("querying_live_parcel_data", parcel=parcel_number)
        # Primary lookup in TaxlotsPublic
        where = f"Prop_id = '{parcel_number}'" # Or PARCEL_NUM depending on layer
        return self._make_query(self.layers["taxlots"], where)

    def get_zoning_details(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Spatial query for zoning at a specific coordinate.
        """
        # Note: Requires point-in-polygon spatial query
        # Simplified for now to attribute lookup if we have parcel mapping
        pass

def query_arcgis(parcel_number: str) -> Optional[Dict]:
    """Standalone helper for agent nodes."""
    client = ArcGISClient()
    return client.get_parcel_details(parcel_number)
