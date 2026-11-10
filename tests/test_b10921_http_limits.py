"""Request limits before parsing, with and without Content-Length."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.http_limits import MAX_BODY_BYTES, RequestBodyLimitMiddleware


def test_oversized_credentials_are_rejected_before_json_parsing():
    response = TestClient(app).post('/auth/login', content=b'x' * (MAX_BODY_BYTES + 1))
    assert response.status_code == 413
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert 'x' * 100 not in response.text


@pytest.mark.parametrize('headers,chunks,expected', [
    ([], [b'a' * 4, b'b' * 4], 204),
    ([], [b'a' * 4, b'b' * 5], 413),
    ([(b'content-length', b'8')], [b'abcd', b'efgh'], 204),
    ([(b'content-length', b'1')], [b'abcdefghi'], 413),
    ([(b'content-length', b'9')], [], 413),
    ([(b'content-length', b'-1')], [], 400),
    ([(b'content-length', b'1'), (b'content-length', b'2')], [], 400),
    ([(b'content-length', b'9' * 5000)], [], 413),
])
def test_stream_limits_and_exact_replay(headers, chunks, expected):
    sent = []
    body = []
    index = 0

    async def receive():
        nonlocal index
        assert index < len(chunks), 'Rejected requests must not read their bodies'
        chunk = chunks[index]
        index += 1
        return {'type': 'http.request', 'body': chunk, 'more_body': index < len(chunks)}

    async def send(message):
        sent.append(message)

    async def endpoint(scope, receive, send):
        while True:
            message = await receive()
            body.append(message['body'])
            if not message.get('more_body'):
                break
        await send({'type': 'http.response.start', 'status': 204, 'headers': []})
        await send({'type': 'http.response.body', 'body': b''})

    asyncio.run(RequestBodyLimitMiddleware(endpoint, max_bytes=8)(
        {'type': 'http', 'headers': headers}, receive, send))
    assert sent[0]['status'] == expected
    if expected == 204:
        assert b''.join(body) == b''.join(chunks)
    else:
        assert not body


def test_many_tiny_chunks_do_not_accumulate_request_objects():
    import tracemalloc
    index = 0
    consumed = []

    async def receive():
        nonlocal index
        index += 1
        return {'type': 'http.request', 'body': b'x' if index == 30000 else b'',
                'more_body': index < 30000}

    async def endpoint(scope, receive, send):
        while True:
            message = await receive()
            consumed.append(message['body'])
            if not message.get('more_body'):
                break

    async def send(message):
        raise AssertionError('An in-limit request must reach the endpoint')

    tracemalloc.start()
    try:
        asyncio.run(RequestBodyLimitMiddleware(endpoint, max_bytes=8)(
            {'type': 'http', 'headers': []}, receive, send))
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert b''.join(consumed) == b'x'
    assert peak < 1_000_000, f'Chunk metadata retained {peak} bytes for a one-byte request'
