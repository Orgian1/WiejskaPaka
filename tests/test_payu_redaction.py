from backend.payu_redaction import redact_payu_diagnostics


def test_sensitive_provider_fields_are_removed_recursively():
    raw = {"client_secret":"secret-123", "headers":{"Authorization":"Bearer abc.123",
           "OpenPayU-Signature":"sha384=abcdef"}, "rows":[{"access_token":"token-1"}]}
    clean = redact_payu_diagnostics(raw)
    assert "secret-123" not in str(clean)
    assert "abc.123" not in str(clean)
    assert "abcdef" not in str(clean)
    assert "token-1" not in str(clean)
    assert clean["headers"]["Authorization"] == "[REDACTED]"


def test_nonsensitive_payment_reference_preserved():
    assert redact_payu_diagnostics({"order_id":"abc","amount_grosze":100}) == {
        "order_id":"abc","amount_grosze":100
    }
