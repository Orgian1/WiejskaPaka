"""Guard against SQLite-only BEGIN IMMEDIATE leaking into PostgreSQL paths."""
import ast
from pathlib import Path


def test_sqlite_immediate_transactions_are_guarded():
    source = Path(__file__).resolve().parents[1] / 'backend' / 'app.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    guarded = []
    unguarded = []

    def visit(node, under_sqlite_guard=False):
        if isinstance(node, ast.If):
            condition = ast.unparse(node.test)
            sqlite_only = condition in ('not DATABASE_URL', 'DATABASE_URL == False', "DATABASE_URL == ''")
            for child in node.body:
                visit(child, under_sqlite_guard or sqlite_only)
            for child in node.orelse:
                visit(child, under_sqlite_guard)
            return
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'execute':
            if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'BEGIN IMMEDIATE':
                (guarded if under_sqlite_guard else unguarded).append(node.lineno)
        for child in ast.iter_child_nodes(node):
            visit(child, under_sqlite_guard)

    visit(tree)
    assert guarded, 'Expected SQLite transaction statements to exist'
    assert not unguarded, f'Unprotected SQLite-only SQL at lines {unguarded}'
