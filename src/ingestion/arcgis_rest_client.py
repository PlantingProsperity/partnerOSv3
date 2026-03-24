"""
arcgis_rest_client.py — The 'Secret Entrance' Engine for PartnerOS (Elevated)

Provides high-performance, async property enrichment via public ArcGIS REST APIs.
Bypasses bulk downloads for real-time scouting and signal detection.
"""

import httpx
import json
import asyncio
from typing import Dict, Optional, List
from src.utils.logger import get_logger
import config

log = get_logger("ingestion.arcgis_rest")

class ArcGISClient:
    """
    High-performance async client for Clark County FeatureServers.
    """
    def __init__(self):
        self.base_url = config.ARCGIS_REST_ROOT
        self.layers = config.ARCGIS_LAYERS
        self.semaphore = asyncio.Semaphore(5) # Limit concurrency to be respectful

    async def _make_query(self, layer_url: str, where: str, out_fields: str = "*") -> Optional[Dict]:
        """Internal helper for async REST queries."""
        url = f"{layer_url}/query"
        params = {
            "where": where,
            "outFields": out_fields,
            "f": "json",
            "returnGeometry": "false"
        }
        
        async with self.semaphore:
            async with httpx.AsyncClient(timeout=15.0) as client:
                try:
                    r = await client.get(url, params=params)
                    r.raise_for_status()
                    data = r.json()
                    if data.get("features"):
                        return data["features"][0].get("attributes")
                    return None
                except Exception as e:
                    log.error("arcgis_rest_query_failed", url=url, error=str(e))
                    return None

    async def get_parcel_details(self, parcel_number: str) -> Optional[Dict]:
        """
        Sub-second enrichment for a specific parcel.
        Used by the Scout and Explorer agents.
        """
        log.info("querying_live_arcgis_parcel", parcel=parcel_number)
        # Search by Prop_id or ParcelNum
        where = f"Prop_id = '{parcel_number}' OR SitusAddrsFull LIKE '{parcel_number}%'"
        return await self._make_query(self.layers["taxlots"], where)

    async def query_custom_layer(self, layer_key: str, where: str) -> Optional[Dict]:
        """Queries any layer defined in config.ARCGIS_LAYERS."""
        layer_url = self.layers.get(layer_key)
        if not layer_url:
            log.error("layer_key_not_found", key=layer_key)
            return None
        return await self._make_query(layer_url, where)

async def query_arcgis(parcel_number: str) -> Optional[Dict]:
    """Helper for standalone usage."""
    client = ArcGISClient()
    return await client.get_parcel_details(parcel_number)

if __name__ == "__main__":
    # Test for 716 E McLoughlin (41550000)
    res = asyncio.run(query_arcgis("41550000"))
    print(json.dumps(res, indent=2))
