"""Isolated gateway context checks; no PostgreSQL connection or RLS activation."""
import unittest

from backend.rls_gateway import database_context, _context, DatabaseContextMiddleware


class GatewayContextTests(unittest.TestCase):
    def test_nested_context_restores_previous_identity(self):
        original = _context.get()
        with database_context('request', 'Bearer client'):
            self.assertEqual(_context.get(), ('request', 'Bearer client'))
            with database_context('auth', 'Bearer login'):
                self.assertEqual(_context.get(), ('auth', 'Bearer login'))
            self.assertEqual(_context.get(), ('request', 'Bearer client'))
        self.assertEqual(_context.get(), original)

    def test_exception_restores_context(self):
        original = _context.get()
        with self.assertRaisesRegex(RuntimeError, 'failure'):
            with database_context('request', 'Bearer secret'):
                raise RuntimeError('failure')
        self.assertEqual(_context.get(), original)

    def test_invalid_scope_is_rejected(self):
        with self.assertRaises(ValueError):
            with database_context('admin', 'Bearer secret'):
                pass

    def test_middleware_passes_request_context_and_restores(self):
        import asyncio
        observed = []
        original = _context.get()

        async def downstream(scope, receive, send):
            observed.append(_context.get())

        middleware = DatabaseContextMiddleware(downstream)

        async def noop():
            return None

        async def exercise():
            await middleware(
                {'type': 'http', 'path': '/orders',
                 'headers': [(b'authorization', b'Bearer customer')]},
                noop, noop)
            await middleware(
                {'type': 'http', 'path': '/auth/login', 'headers': []},
                noop, noop)

        asyncio.run(exercise())
        self.assertEqual(observed, [
            ('request', 'Bearer customer'), ('auth', ''),
        ])
        self.assertEqual(_context.get(), original)


if __name__ == '__main__':
    unittest.main()
