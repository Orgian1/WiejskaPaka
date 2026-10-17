"""Offline, read-only API route inventory for human authorization review.

Does not contact any database or service and does not imply that a route is secure.
"""
import datetime as dt
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute
from backend.app import app
from backend.release_readiness import default_report

ROOT = Path(__file__).resolve().parents[1]
SENSITIVE = ('admin', 'order', 'shipment', 'delivery', 'payment', 'payout', 'refund', 'address', 'bank', 'account', 'pin', 'profile', 'auth', 'seller', 'farmer', 'courier', 'notification')

def build_report():
    routes = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        path = route.path
        for method in sorted(route.methods - {'HEAD', 'OPTIONS'}):
            sensitive = any(word in path.lower() for word in SENSITIVE)
            routes.append({'method': method, 'path': path,
                           'sensitive_review_priority': 'high' if sensitive else 'normal',
                           'authorization_manually_verified': False})
    routes.sort(key=lambda r: (r['path'], r['method']))
    return {'generated_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'scope': 'Static route inventory only; no live endpoint authorization claims',
            'route_count': len(routes),
            'high_priority_count': sum(r['sensitive_review_priority'] == 'high' for r in routes),
            'routes': routes,
            'production_readiness': default_report(),
            'known_blockers': [
                'Isolated PostgreSQL server integration not executed',
                'Chromium loopback HTTP blocked by environment policy',
                'Physical phone testing not executed',
                'Manual endpoint-by-endpoint authorization audit outstanding',
                'Independent legal/privacy review outstanding',
                'Live payments and production infrastructure deliberately not configured',
            ]}

if __name__ == '__main__':
    report = build_report()
    target = ROOT / 'RAPORT_INWENTARYZACJA_ENDPOINTOW_B_6601_6960.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"API routes: {report['route_count']}; high-priority: {report['high_priority_count']}; output: {target.name}")
