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
