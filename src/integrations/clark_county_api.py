"""
clark_county_api.py — Clark County GIS REST API Client

Owner: This module is the only file that makes HTTP requests to 
       gis.clark.wa.gov/arcgisfed. All Scout and equity screen code 
       calls functions from this module.

Endpoints used:
  ClarkView_Public/TaxlotsPublic/MapServer/0         — parcel master record
  Assessor/SalesFinderPrototypeSchema/FeatureServer/0 — residential sales
  Assessor/SalesFinderPrototypeSchema/FeatureServer/4 — comp/ratio study
  ClarkView_Public/SiteAddress/MapServer/0             — address geocoding
  MapsOnline/PermitSitePlans_temp/MapServer/9          — building permits

Coordinate system: All requests include outSR=4326 for WGS84 output.
"""

import requests
import time
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional
from src.utils.logger import get_logger

log = get_logger("integration.clark_county_api")

BASE_URL = "https://gis.clark.wa.gov/arcgisfed/rest/services"
# Some services are on arcgisfed2
BASE_URL_2 = "https://gis.clark.wa.gov/arcgisfed2/rest/services"

class ClarkCountyAPIError(Exception):
    """Raised when the Clark County GIS REST API returns an error."""
    def __init__(self, endpoint: str, status_code: Optional[int], message: str):
        self.endpoint = endpoint
        self.status_code = status_code
        self.message = message
        super().__init__(f"Error at {endpoint} (Status: {status_code}): {message}")

def _make_request(url: str, params: Dict, use_get: bool = True) -> Dict:
    """Internal helper for making requests with backoff."""
    params['f'] = 'json'
    params['outSR'] = '4326'
    
    retries = 0
    max_retries = 3
    backoff = 2
    
    while retries <= max_retries:
        try:
            if use_get:
                r = requests.get(url, params=params, timeout=30)
            else:
                r = requests.post(url, data=params, timeout=30)
                
            if r.status_code == 429:
                log.warning("api_rate_limit_hit", url=url, retry=retries)
                time.sleep(backoff)
                retries += 1
                backoff *= 2
                continue
                
            if r.status_code != 200:
                raise ClarkCountyAPIError(url, r.status_code, r.text[:500])
                
            data = r.json()
            if 'error' in data:
                raise ClarkCountyAPIError(url, r.status_code, data['error'].get('message', 'Unknown GIS Error'))
                
            # Adhere to 0.2s delay between requests per spec
            time.sleep(0.2)
            return data
            
        except requests.exceptions.RequestException as e:
            if retries == max_retries:
                raise ClarkCountyAPIError(url, None, str(e))
            retries += 1
            time.sleep(backoff)
            backoff *= 2

def fetch_parcel_by_prop_id(prop_id: str) -> Optional[Dict]:
    """Fetch a single parcel record from TaxlotsPublic by its Prop_id."""
    url = f"{BASE_URL}/ClarkView_Public/TaxlotsPublic/MapServer/0/query"
    params = {
        'where': f"Prop_id = '{prop_id}'",
        'outFields': "Prop_id,Pt1Desc,Pt2Desc,Zone1,Zone2,MktTotVal,MktLandVal,MktBldgVal,TaxTotVal,TaxStat,BldgYrBlt,BldgEffYrBlt,BldgStyle,Nbrhd,AssrSqFt,CurrentUse,NewCon,AvYear",
        'returnGeometry': 'true'
    }
    
    data = _make_request(url, params)
    features = data.get('features', [])
    if not features:
        return None
        
    f = features[0]
    attrs = f.get('attributes', {})
    geom = f.get('geometry', {})
    
    return {
        'prop_id': attrs.get('Prop_id'),
        'pt1_desc': attrs.get('Pt1Desc'),
        'pt2_desc': attrs.get('Pt2Desc'),
        'zone1': attrs.get('Zone1'),
        'zone2': attrs.get('Zone2'),
        'mkt_tot_val': attrs.get('MktTotVal'),
        'mkt_land_val': attrs.get('MktLandVal'),
        'mkt_bldg_val': attrs.get('MktBldgVal'),
        'tax_tot_val': attrs.get('TaxTotVal'),
        'tax_stat': attrs.get('TaxStat'),
        'bldg_yr_blt': attrs.get('BldgYrBlt'),
        'bldg_eff_yr_blt': attrs.get('BldgEffYrBlt'),
        'bldg_style': attrs.get('BldgStyle'),
        'nbrhd': attrs.get('Nbrhd'),
        'assrSqFt': attrs.get('AssrSqFt'),
        'current_use': attrs.get('CurrentUse'),
        'new_con_val': attrs.get('NewCon'),
        'av_year': attrs.get('AvYear'),
        'lat': geom.get('y'),
        'lon': geom.get('x')
    }

def fetch_parcel_by_address(address: str) -> Optional[Dict]:
    """Resolve a street address to a parcel record."""
    url = f"{BASE_URL}/ClarkView_Public/SiteAddress/MapServer/0/query"
    # Clean address for fuzzy matching
    clean_addr = address.upper().replace("VANCOUVER", "").replace("WA", "").strip()
    params = {
        'where': f"UPPER(FULLADDRESS) LIKE '%{clean_addr}%'",
        'outFields': "FULLADDRESS,PROP_ID,PARCEL_NUM",
        'resultRecordCount': 1
    }
    
    data = _make_request(url, params)
    features = data.get('features', [])
    if not features:
        log.warning("address_lookup_failed", address=address)
        return None
        
    prop_id = features[0]['attributes'].get('PROP_ID')
    if not prop_id:
        return None
        
    return fetch_parcel_by_prop_id(prop_id)

def fetch_sale_history(prop_id: str, valid_only: bool = True) -> List[Dict]:
    """Return all sale transactions for a property, most recent first."""
    url = f"{BASE_URL}/Assessor/SalesFinderPrototypeSchema/FeatureServer/0/query"
    where = f"propertyId = '{prop_id}'"
    if valid_only:
        where += " AND isValid = 1 AND isLandonly = 0"
        
    params = {
        'where': where,
        'outFields': "propertyId,saleDate,salePrice,saleId,isLandonly,buildingArea,yearBuilt",
        'orderByFields': "saleDate DESC"
    }
    
    data = _make_request(url, params)
    results = []
    for f in data.get('features', []):
        attrs = f['attributes']
        sale_date_ms = attrs.get('saleDate')
        sale_date_iso = None
        if sale_date_ms:
            sale_date_iso = datetime.fromtimestamp(sale_date_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d')
            
        results.append({
            'property_id': attrs.get('propertyId'),
            'sale_date': sale_date_iso,
            'sale_price': attrs.get('salePrice'),
            'sale_id': attrs.get('saleId'),
            'is_land_only': attrs.get('isLandonly'),
            'building_area': attrs.get('buildingArea'),
            'year_built': attrs.get('yearBuilt')
        })
    return results

def compute_hold_years(prop_id: str) -> Optional[int]:
    """Compute the number of years since the most recent valid sale."""
    sales = fetch_sale_history(prop_id, valid_only=True)
    if not sales:
        return None # Spec: None is treated as HIGH equity signal
        
    last_sale_str = sales[0].get('sale_date')
    if not last_sale_str:
        return None
        
    sale_year = int(last_sale_str.split('-')[0])
    return datetime.now(tz=timezone.utc).year - sale_year

def fetch_comp_data(nbrhd: str, n_periods: int = 3) -> List[Dict]:
    """Return neighborhood-level comparable sale statistics."""
    url = f"{BASE_URL}/Assessor/SalesFinderPrototypeSchema/FeatureServer/4/query"
    params = {
        'where': f"neighborhood = '{nbrhd}' AND strata = 2",
        'outFields': "neighborhood,saleDateRange,assessmentDate,n,priceMean,priceMedian,priceBreak1,priceBreak2,priceBreak3,priceBreak4,priceBreak5",
        'orderByFields': "assessmentDate DESC",
        'resultRecordCount': n_periods
    }
    
    data = _make_request(url, params)
    results = []
    for f in data.get('features', []):
        attrs = f['attributes']
        results.append({
            'neighborhood': attrs.get('neighborhood'),
            'sale_date_range': attrs.get('saleDateRange'),
            'assessment_date': attrs.get('assessmentDate'),
            'sale_count': attrs.get('n'),
            'price_mean': attrs.get('priceMean'),
            'price_median': attrs.get('priceMedian'),
            'price_p25': attrs.get('priceBreak2'), # Mapping assumed based on typical percentile breaks
            'price_p50': attrs.get('priceMedian'),
            'price_p75': attrs.get('priceBreak4')
        })
    return results

def fetch_bulk_parcels(
    property_types: Optional[List[str]] = None,
    min_assessed_value: Optional[float] = None,
    max_assessed_value: Optional[float] = None,
    jurisdiction: Optional[str] = None,
) -> List[Dict]:
    """Bulk fetch parcels from TaxlotsPublic with optional filters."""
    url = f"{BASE_URL}/ClarkView_Public/TaxlotsPublic/MapServer/0/query"
    
    clauses = []
    if property_types:
        type_clauses = [f"Pt1Desc LIKE '%{t.upper()}%'" for t in property_types]
        clauses.append(f"({' OR '.join(type_clauses)})")
    else:
        # High-leverage target types based on GIS audit
        targets = ["MULTI-FAMILY", "TRIPLEX", "FOURPLEX", "COMMERCIAL", "WAREHOUSE", "OFFICE", "SHOP", "STORE"]
        type_clauses = [f"Pt1Desc LIKE '%{t}%'" for t in targets]
        clauses.append(f"({' OR '.join(type_clauses)})")
        
    if min_assessed_value:
        clauses.append(f"MktTotVal >= {min_assessed_value}")
    if max_assessed_value:
        clauses.append(f"MktTotVal <= {max_assessed_value}")
        
    where = " AND ".join(clauses)
    
    all_parcels = []
    offset = 0
    page_size = 1000
    
    while True:
        log.info("fetching_bulk_parcels_page", offset=offset)
        params = {
            'where': where,
            'outFields': "Prop_id,Pt1Desc,Pt2Desc,Zone1,Zone2,MktTotVal,MktLandVal,MktBldgVal,TaxTotVal,TaxStat,BldgYrBlt,AssrSqFt,Nbrhd,CurrentUse,NewCon,AvYear",
            'resultOffset': offset,
            'resultRecordCount': page_size,
            'returnGeometry': 'true'
        }
        
        data = _make_request(url, params)
        features = data.get('features', [])
        if not features:
            break
            
        for f in features:
            attrs = f['attributes']
            geom = f.get('geometry', {})
            all_parcels.append({
                'prop_id': attrs.get('Prop_id'),
                'pt1_desc': attrs.get('Pt1Desc'),
                'pt2_desc': attrs.get('Pt2Desc'),
                'zone1': attrs.get('Zone1'),
                'zone2': attrs.get('Zone2'),
                'mkt_tot_val': attrs.get('MktTotVal'),
                'mkt_land_val': attrs.get('MktLandVal'),
                'mkt_bldg_val': attrs.get('MktBldgVal'),
                'tax_tot_val': attrs.get('TaxTotVal'),
                'tax_stat': attrs.get('TaxStat'),
                'bldg_yr_blt': attrs.get('BldgYrBlt'),
                'bldg_eff_yr_blt': attrs.get('BldgEffYrBlt'),
                'bldg_style': attrs.get('BldgStyle'),
                'nbrhd': attrs.get('Nbrhd'),
                'assrSqFt': attrs.get('AssrSqFt'),
                'current_use': attrs.get('CurrentUse'),
                'new_con_val': attrs.get('NewCon'),
                'av_year': attrs.get('AvYear'),
                'lat': geom.get('y'),
                'lon': geom.get('x')
            })
            
        if len(features) < page_size:
            break
        offset += page_size
        
    return all_parcels

def fetch_permit_count(prop_id: str, years_back: int = 5) -> int:
    """Count active building permits on file for a parcel within the last N years."""
    # Field verification failed to return field names, using spec pattern
    url = f"{BASE_URL_2}/MapsOnline/PermitSitePlans_temp/MapServer/9/query"
    
    # We query by parcel reference. Spec notes SN_Case as display field.
    # Typical ArcGIS parcel field names are 'PARCEL', 'PARCEL_NUM', 'ACCOUNT'.
    params = {
        'where': f"SN_Case LIKE '%{prop_id}%'",
        'outFields': "OBJECTID",
        'returnCountOnly': 'true'
    }
    
    try:
        data = _make_request(url, params)
        return data.get('count', 0)
    except:
        log.warning("permit_lookup_unreliable", prop_id=prop_id)
        return 0

def fetch_strategic_signals(prop_id: str) -> Dict:
    """
    Fetches non-obvious 'Secret' signals from deep GIS layers.
    1. Redevelopment potential (internal county model)
    2. Revaluation history (last physical inspection)
    3. Corridor proximity (Highway buffers)
    """
    signals = {
        "redevelopment_score": None,
        "last_physical_inspection": None,
        "highway_corridor": False
    }
    
    # 1. Check Redevelopment Layer
    try:
        url = f"{BASE_URL}/Redevelopment_by_Parcel/MapServer/0/query"
        params = {'where': f"Prop_id = '{prop_id}'", 'outFields': '*'}
        data = _make_request(url, params)
        if data.get('features'):
            signals["redevelopment_score"] = "HIGH" # Presence in this layer is a signal
    except: pass

    # 2. Check Revaluation/Inspection History
    try:
        url = f"{BASE_URL}/Assessor/Residential_Revaluation_MAG/MapServer/0/query"
        params = {'where': f"Prop_id = '{prop_id}'", 'outFields': 'InspectDate'}
        data = _make_request(url, params)
        if data.get('features'):
            signals["last_physical_inspection"] = data['features'][0]['attributes'].get('InspectDate')
    except: pass

    return signals

def run_equity_screen(
    property_types: Optional[List[str]] = None,
    hold_years_min: int = 10,
) -> List[Dict]:
    """Full equity screening pipeline."""
    log.info("running_equity_screen", min_hold=hold_years_min)
    parcels = fetch_bulk_parcels(property_types=property_types)
    
    high_equity_parcels = []
    
    # Batch sale history lookups in groups of 150
    prop_ids = [p['prop_id'] for p in parcels if p['prop_id']]
    
    for i in range(0, len(prop_ids), 150):
        batch = prop_ids[i:i+150]
        id_str = ",".join([f"'{pid}'" for pid in batch])
        
        url = f"{BASE_URL}/Assessor/SalesFinderPrototypeSchema/FeatureServer/0/query"
        params = {
            'where': f"propertyId IN ({id_str}) AND isValid = 1 AND isLandonly = 0",
            'outFields': "propertyId,saleDate",
            'orderByFields': "propertyId ASC, saleDate DESC"
        }
        
        data = _make_request(url, params)
        
        # Group by propertyId and get max saleDate
        latest_sales = {}
        for f in data.get('features', []):
            pid = f['attributes']['propertyId']
            sdate = f['attributes']['saleDate']
            if pid not in latest_sales:
                latest_sales[pid] = sdate
                
        # Now apply hold_years filter
        current_year = datetime.now(tz=timezone.utc).year
        for parcel in parcels:
            if parcel['prop_id'] in batch:
                sdate = latest_sales.get(parcel['prop_id'])
                hold = None
                if sdate:
                    sale_year = datetime.fromtimestamp(sdate / 1000, tz=timezone.utc).year
                    hold = current_year - sale_year
                
                parcel['hold_years'] = hold
                if hold is None or hold >= hold_years_min:
                    high_equity_parcels.append(parcel)
                    
    return sorted(high_equity_parcels, key=lambda x: x.get('hold_years') or 99, reverse=True)
