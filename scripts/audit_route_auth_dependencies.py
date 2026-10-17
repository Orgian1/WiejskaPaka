"""Read-only structural audit of FastAPI authentication dependencies.

Structural signals are not proof of authorization: manual checks remain required.
"""
import json
import sys
from pathlib import Path
from fastapi.routing import APIRoute
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app import app

PUBLIC_PREFIXES = ('/auth/register', '/auth/login', '/products', '/catalog/', '/health', '/marketplace/accounting-policy')
PUBLIC_EXACT = {'/', '/products', '/health', '/auth/register', '/auth/login', '/marketplace/accounting-policy'}

# These three routes intentionally work without a session: demo opt-in and
# a single-use reset token replace session authentication for confirmation.
RECOVERY_ROUTES = {('GET', '/auth/password-reset-test/options'),
                   ('POST', '/auth/password-reset-test/request'),
                   ('POST', '/auth/password-reset-test/confirm')}

def is_public(method, path):
    if (method, path) in RECOVERY_ROUTES:
        return True
    if method == 'POST' and path == '/marketplace/nearby':
        return True
    return path in PUBLIC_EXACT and (method == 'GET' or path.startswith('/auth/')) or (method == 'GET' and path.startswith('/catalog/')) or (method == 'GET' and path in {'/products/{product_id}', '/farmers/{farmer_id}/pickup-points'})

def audit():
    rows = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        deps = sorted({getattr(d.call, '__name__', repr(d.call)) for d in route.dependant.dependencies})
        params = {p.name for p in route.dependant.header_params}
        for method in sorted(route.methods - {'HEAD', 'OPTIONS'}):
            public = is_public(method, route.path)
            has_user_dep = 'current_user' in deps
            auth_header = 'authorization' in params
            rows.append({'method': method, 'path': route.path, 'endpoint': route.endpoint.__name__, 'dependencies': deps,
                         'auth_header_parameter': auth_header, 'public_candidate': public,
                         'manual_review_required': True,
                         'review_flag': 'RECOVERY_TOKEN_FLOW' if (method, route.path) in RECOVERY_ROUTES else 'NO_DIRECT_AUTH_DEPENDENCY' if not public and not has_user_dep else ('PUBLIC_CANDIDATE' if public else 'DIRECT_AUTH_DEPENDENCY')})
    rows.sort(key=lambda x:(x['path'],x['method']))
    return {'scope': 'Static FastAPI route dependencies; indirect authentication and authorization not determined',
            'routes': rows, 'total': len(rows), 'no_direct_auth_dependency': sum(x['review_flag']=='NO_DIRECT_AUTH_DEPENDENCY' for x in rows),
            'warning': 'NO_DIRECT_AUTH_DEPENDENCY does not establish a vulnerability; handlers may authenticate internally.'}

if __name__ == '__main__':
    result = audit()
    target = ROOT / 'RAPORT_ZALEZNOSCI_AUTORYZACJI_B_6961_7320.json'
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf8')
    print('routes:', result['total'], 'flags for manual review:', result['no_direct_auth_dependency'])
