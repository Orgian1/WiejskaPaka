"""Prevent accidental production PayU traffic in development/test deployments."""
from urllib.parse import urlparse


SANDBOX_HOSTS = frozenset({"secure.snd.payu.com"})
PRODUCTION_HOSTS = frozenset({"secure.payu.com"})


def validate_payu_api_url(url: str, *, sandbox: bool) -> str:
    if not isinstance(url, str):
        raise ValueError("PayU API URL must be a string")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
        raise ValueError("PayU requires HTTPS and no URL credentials or custom ports")
    if parsed.hostname not in (SANDBOX_HOSTS if sandbox else PRODUCTION_HOSTS):
        raise ValueError("PayU endpoint is not approved for selected environment")
    if not parsed.path.startswith("/api/"):
        raise ValueError("Unexpected PayU API endpoint")
    if parsed.fragment:
        raise ValueError("PayU API URL cannot include a fragment")
    return url
