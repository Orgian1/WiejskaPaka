"""The Windows diagnostic distinguishes a valid provider response from HTTP 200."""
import json
import httpx
from scripts.check_photon_demo import classified,failure
from tests.test_issue59_photon import result


def test_status_200_is_not_sufficient_and_optional_nulls_identify_legacy_failure():
    good=classified(httpx.Response(200,json=result()))
    assert good['normalization_ok'] and good['legacy_null_property_failure']
    bad=classified(httpx.Response(200,json={'unexpected':'private-upstream-data'}))
    assert not bad['normalization_ok'] and 'private-upstream-data' not in json.dumps(bad)


def test_language_failure_is_classified_without_copying_upstream_message():
    response=classified(httpx.Response(400,json={'message':'Language is not supported. private-diagnostic-details'}))
    assert response['unsupported_language'] and 'private-diagnostic-details' not in json.dumps(response)


def test_tls_and_proxy_failures_do_not_echo_details():
    assert failure(httpx.ConnectError('SSL certificate verify failed private-ca-path'))=={'error':'TLS_VERIFICATION_FAILED'}
    assert failure(httpx.ProxyError('private-proxy-credentials'))=={'error':'PROXY_OR_NETWORK_POLICY'}
