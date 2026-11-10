"""Offline, read-only release audit. No secrets, no external services."""
import ast
import json
from pathlib import Path

HTTP = {"get", "post", "put", "patch", "delete"}

def audit_routes(path):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    found = {}
    duplicates = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call) or not isinstance(deco.func, ast.Attribute):
                continue
            if deco.func.attr not in HTTP or not isinstance(deco.func.value, ast.Name) or deco.func.value.id != "app":
                continue
            if not deco.args or not isinstance(deco.args[0], ast.Constant) or not isinstance(deco.args[0].value, str):
                continue
            key = (deco.func.attr.upper(), deco.args[0].value)
            if key in found:
                duplicates.append({"method": key[0], "path": key[1], "functions": [found[key], node.name]})
            else:
                found[key] = node.name
    return {"route_count": len(found), "duplicate_routes": duplicates}

def audit_project(root):
    root = Path(root)
    route_report = audit_routes(root / "backend" / "app.py")
    required = ["backend/app.py", "backend/money.py", "backend/pg_adapter.py", "database/migrate_all_tables.py", "requirements.txt", "web"]
    missing = [p for p in required if not (root / p).exists()]
    return {**route_report, "missing_components": missing,
            "postgres_integration_verified": False, "real_payments_enabled": False,
            "ready_for_production": False}

def main():
    report = audit_project(Path(__file__).resolve().parents[1])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["duplicate_routes"] or report["missing_components"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
