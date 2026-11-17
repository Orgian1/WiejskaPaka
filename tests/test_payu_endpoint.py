import pytest

from backend.payu_endpoint import validate_payu_api_url


def test_sandbox_endpoint_is_accepted():
    url = "https://secure.snd.payu.com/api/v2_1/orders"
    assert validate_payu_api_url(url,sandbox=True) == url


@pytest.mark.parametrize("url", [
    "http://secure.snd.payu.com/api/v2_1/orders",
    "https://secure.payu.com/api/v2_1/orders",
    "https://secure.snd.payu.com.evil.test/api/v2_1/orders",
    "https://user:password@secure.snd.payu.com/api/v2_1/orders",
    "https://secure.snd.payu.com:443/api/v2_1/orders",
    "https://secure.snd.payu.com/not-api",
    "https://secure.snd.payu.com/api/v2_1/orders#fragment",
])
def test_sandbox_rejects_wrong_host_or_unsafe_url(url):
    with pytest.raises(ValueError):
        validate_payu_api_url(url,sandbox=True)
