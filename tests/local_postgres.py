"""Disposable loopback-only PostgreSQL for security fixtures.

Unlike pgserver.get_server this transport does not require Unix sockets.
Never opens an existing data directory or accepts an external DSN.
"""
from pathlib import Path
import socket
import pgserver


class LocalPostgres:
    def __init__(self, directory):
        self.directory = Path(directory)
        if self.directory.exists():
            raise ValueError('A new PostgreSQL directory is required')
        pgserver.initdb(['-A', 'trust', '-U', 'security_admin'], pgdata=self.directory)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        pgserver.pg_ctl(['-w', '-l', str(self.directory / 'server.log'), '-o',
                        f"-h 127.0.0.1 -p {self.port} -k ''", 'start'], pgdata=self.directory)

    def get_uri(self, database='postgres'):
        if database not in ('postgres', 'wp_test_capabilities'):
            raise ValueError('Unexpected fixture database')
        return f'postgresql://security_admin@127.0.0.1:{self.port}/{database}'

    def cleanup(self):
        pgserver.pg_ctl(['-w', 'stop'], pgdata=self.directory)
