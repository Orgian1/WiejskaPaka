"""Offline SQL access inventory for reviewing future PostgreSQL RLS policies.

This is deliberately conservative: static scanning cannot prove authorization.
No database connection, migration or SQL execution is performed.
"""
import ast
import re
from pathlib import Path

TABLE_PATTERN = re.compile(r'\b(?:FROM|JOIN|INTO|UPDATE|DELETE\s+FROM)\s+(?:public\.)?([a-z_][a-z_0-9]*)\b', re.I)
WRITE_PATTERN = re.compile(r'^\s*(INSERT|UPDATE|DELETE|REPLACE)\b', re.I)
READ_PATTERN = re.compile(r'^\s*(SELECT|WITH)\b', re.I)
SENSITIVE = frozenset({'users', 'sessions', 'orders', 'order_locations', 'delivery_assignments', 'seller_compliance'})


def _sql_fragment(node):
    """Recover literal SQL pieces without pretending dynamic values are safe."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value, False
    if isinstance(node, ast.JoinedStr):
        return ''.join(part.value for part in node.values if isinstance(part, ast.Constant)
                       and isinstance(part.value, str)), True
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        left, _ = _sql_fragment(node.left)
        if isinstance(node.op, ast.Add):
            right, _ = _sql_fragment(node.right)
            return left + ' ' + right, True
        return left, True
    return '', True


def inventory_file(path):
    """Return conservative SQL call-site inventory, including partial dynamic SQL."""
    path = Path(path)
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    entries = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in ('execute', 'executemany') or not node.args:
            continue
        sql, dynamic = _sql_fragment(node.args[0])
        sql = sql.strip()
        tables = sorted(set(m.group(1).lower() for m in TABLE_PATTERN.finditer(sql)))
        operation = ('DYNAMIC' if dynamic else 'WRITE' if WRITE_PATTERN.match(sql)
                     else 'READ' if READ_PATTERN.match(sql) else 'OTHER')
        entries.append({'line': node.lineno, 'operation': operation, 'tables': tables,
                        'requires_manual_review': dynamic or bool(SENSITIVE.intersection(tables))
                        or operation == 'OTHER'})
    return sorted(entries, key=lambda item: item['line'])


def project_inventory(root):
    root = Path(root)
    result = {}
    for path in sorted((root / 'backend').glob('*.py')):
        entries = inventory_file(path)
        if entries:
            result[path.name] = entries
    return result


def summary(inventory):
    sensitive = {}
    dynamic = 0
    for filename, entries in inventory.items():
        for entry in entries:
            dynamic += entry['operation'] == 'DYNAMIC'
            for table in SENSITIVE.intersection(entry['tables']):
                sensitive.setdefault(table, []).append((filename, entry['line'], entry['operation']))
    return {'sensitive': {t: sorted(v) for t, v in sorted(sensitive.items())},
            'dynamic_queries': dynamic,
            'limitations': ['Statyczna analiza nie wykrywa wszystkich zapytań budowanych dynamicznie.',
                            'Wykrycie WHERE ani zależności sesji nie dowodzi autoryzacji.',
                            'Wspólny login SQL i ustawialny GUC nie stanowią samodzielnej granicy bezpieczeństwa.',
                            'Nie uruchamiać RLS bez testów integracyjnych i polityk zapisu.']}
