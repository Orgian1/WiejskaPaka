"""Bound HTTP request memory before JSON validation, including chunked bodies."""
from starlette.responses import JSONResponse

MAX_BODY_BYTES = 1_048_576


class RequestBodyLimitMiddleware:
    def __init__(self, app, max_bytes=MAX_BODY_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        async def reject(status, message):
            response = JSONResponse({'detail': message}, status_code=status,
                                    headers={'Cache-Control': 'no-store'})
            await response(scope, receive, send)

        lengths = [value for name, value in scope.get('headers', []) if name.lower() == b'content-length']
        if lengths:
            if len(lengths) != 1 or not lengths[0].isdigit():
                return await reject(400, 'Nieprawidłowa długość żądania')
            # Compare strings first; do not parse an unbounded integer header.
            length = lengths[0].lstrip(b'0') or b'0'
            maximum = str(self.max_bytes).encode('ascii')
            if len(length) > len(maximum) or (len(length) == len(maximum) and length > maximum):
                return await reject(413, 'Żądanie jest zbyt duże')

        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            if len(body) + len(chunk) > self.max_bytes:
                return await reject(413, 'Żądanie jest zbyt duże')
            body.extend(chunk)
            if not message.get('more_body', False):
                break
        replayed = False

        async def replay():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await receive()

        await self.app(scope, replay, send)
