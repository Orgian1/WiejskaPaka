"""Application integration contract for opt-in RLS request context."""
import unittest
from unittest.mock import patch

from backend.rls_gateway import _context, DatabaseContextMiddleware


class AppGatewayIntegrationTests(unittest.TestCase):
    def test_application_installs_context_middleware(self):
        from backend.app import app
        self.assertTrue(any(m.cls is DatabaseContextMiddleware for m in app.user_middleware))

    def test_http_authorization_and_scope_are_transaction_local(self):
        seen = []

        async def inner(scope, receive, send):
            seen.append(_context.get())

        wrapper = DatabaseContextMiddleware(inner)

        async def invoke(path, headers):
            await wrapper({'type': 'http', 'path': path, 'headers': headers},
                          lambda: None, lambda message: None)

        import asyncio
        asyncio.run(invoke('/orders', [(b'authorization', b'Bearer account-1')]))
        asyncio.run(invoke('/auth/login', []))
        self.assertEqual(seen, [('request', 'Bearer account-1'), ('auth', '')])
        self.assertEqual(_context.get(), ('maintenance', None))

    def test_websocket_and_lifespan_are_not_given_http_identity(self):
        import asyncio
        observed = []

        async def inner(scope, receive, send):
            observed.append((scope['type'], _context.get()))

        wrapper = DatabaseContextMiddleware(inner)

        async def invoke(kind):
            await wrapper({'type': kind, 'path': '/orders',
                           'headers': [(b'authorization', b'Bearer ignored')]},
                          lambda: None, lambda message: None)

        asyncio.run(invoke('websocket'))
        asyncio.run(invoke('lifespan'))
        self.assertEqual(observed, [
            ('websocket', ('maintenance', None)),
            ('lifespan', ('maintenance', None)),
        ])

    def test_context_cleanup_after_cancelled_request(self):
        import asyncio

        async def inner(scope, receive, send):
            self.assertEqual(_context.get(), ('request', 'Bearer transient'))
            raise asyncio.CancelledError()

        wrapper = DatabaseContextMiddleware(inner)

        async def invoke():
            await wrapper({'type': 'http', 'path': '/orders',
                           'headers': [(b'authorization', b'Bearer transient')]},
                          lambda: None, lambda message: None)

        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(invoke())
        self.assertEqual(_context.get(), ('maintenance', None))

    def test_concurrent_requests_keep_distinct_bearer_context(self):
        import asyncio
        seen = {}

        async def inner(scope, receive, send):
            await asyncio.sleep(0)
            seen[scope['path']] = _context.get()

        wrapper = DatabaseContextMiddleware(inner)

        async def invoke(path, token):
            await wrapper({'type': 'http', 'path': path,
                           'headers': [(b'authorization', token.encode('ascii'))]},
                          lambda: None, lambda message: None)

        async def both():
            await asyncio.gather(invoke('/buyer/1', 'Bearer buyer-1'),
                                 invoke('/buyer/2', 'Bearer buyer-2'))

        asyncio.run(both())
        self.assertEqual(seen['/buyer/1'], ('request', 'Bearer buyer-1'))
        self.assertEqual(seen['/buyer/2'], ('request', 'Bearer buyer-2'))
        self.assertEqual(_context.get(), ('maintenance', None))

    def test_exception_cannot_leak_authorization_to_next_request(self):
        async def inner(scope, receive, send):
            self.assertEqual(_context.get(), ('request', 'Bearer secret'))
            raise ValueError('simulated failure')

        wrapper = DatabaseContextMiddleware(inner)
        import asyncio
        async def invoke():
            await wrapper({'type': 'http', 'path': '/orders',
                           'headers': [(b'authorization', b'Bearer secret')]},
                          lambda: None, lambda message: None)

        with self.assertRaisesRegex(ValueError, 'simulated failure'):
            asyncio.run(invoke())
        self.assertEqual(_context.get(), ('maintenance', None))


if __name__ == '__main__':
    unittest.main()
