"""Safe redaction for PayU operational diagnostics."""
import re


_SECRET_KEYS = frozenset({
    "authorization", "client_secret", "second_key", "oauth_token",
    "access_token", "refresh_token", "signature", "openpayu_signature",
    "password", "secret", "api_key",
})
_TOKEN_PATTERN = re.compile(r"(?i)(bearer\s+)[a-z0-9._~+/-]+") 


def redact_payu_diagnostics(value):
    """Recursively redact secrets before emitting structured diagnostics."""
    if isinstance(value, dict):
        return {
            str(key): ("[REDACTED]" if str(key).lower().replace("-", "_") in _SECRET_KEYS
                       else redact_payu_diagnostics(item))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_payu_diagnostics(item) for item in value]
    if isinstance(value, str):
        return _TOKEN_PATTERN.sub(r"\1[REDACTED]", value)
    return value
