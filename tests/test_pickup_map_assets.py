"""Pinned local map assets and real country geometry, without network access."""
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'web'


def test_local_vendor_asset_hashes_and_package_integrity_metadata():
    manifest=json.loads((ROOT/'MAP-ASSETS.json').read_text())
    assert {(p['package'],p['version']) for p in manifest['packages']}=={('leaflet','1.9.4'),('world-atlas','2.0.2'),('topojson-client','3.1.0')}
    for name,digest in manifest['assets'].items():assert sha256((ROOT/name).read_bytes()).hexdigest()==digest
    assert all(p['integrity'].startswith('sha512-') for p in manifest['packages'])


def test_local_overview_contains_actual_poland_geometry():
    world=json.loads((ROOT/'map-countries.geojson').read_text())
    assert world['type']=='FeatureCollection' and len(world['features'])>150
    poland=next(f for f in world['features'] if f['properties']['name']=='Poland')
    assert poland['geometry']['type'] in ('Polygon','MultiPolygon')
    assert poland['geometry']['coordinates']
