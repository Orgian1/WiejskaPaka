"""Kontrola gotowości wydania bez modyfikowania danych i bez połączeń sieciowych."""
import json
import os
from pathlib import Path
from backend.schema_audit import audit_schema

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ('backend/app.py', 'web/index.html', 'web/app.js', 'web/dashboard.js',
            'web/style.css', 'database/postgres_schema.sql', 'requirements.txt')


def release_report(root=ROOT, environ=None):
    root = Path(root)
    env = os.environ if environ is None else environ
    checks = []
    def add(name, ok, severity, details):
        checks.append({'name': name, 'passed': bool(ok), 'severity': severity, 'details': details})
    for name in REQUIRED:
        add('plik: ' + name, (root / name).is_file(), 'error', 'Wymagany składnik projektu')
    if (root / 'backend' / 'app.py').exists() and (root / 'database' / 'postgres_schema.sql').exists():
        schema = audit_schema(root)
        add('schemat PostgreSQL', not schema['missing_in_postgres'], 'error',
            'Brakujące tabele: ' + ', '.join(schema['missing_in_postgres']))
    add('płatności testowe wyłączone', env.get('WP_ENABLE_TEST_PAYMENTS') != '1',
        'warning', 'Flaga symulacji płatności musi być wyłączona przy publicznym wdrożeniu')
    add('harmonogram testowy wyłączony', env.get('WP_ENABLE_WEEKLY_JOB') != '1',
        'warning', 'Nie uruchamiaj developerskiego harmonogramu na produkcji')
    # Poniższe punkty wymagają ręcznego potwierdzenia: nie wolno ich uznać za zaliczone automatycznie.
    for name in ('Testy integracyjne na żywym PostgreSQL', 'Testy interfejsu w przeglądarkach i na telefonach',
                 'Audyt bezpieczeństwa i RODO', 'Weryfikacja prawna regulaminów oraz DAC7',
                 'Umowa i testy sandbox operatora płatności', 'Testy backupu i odtwarzania bazy',
                 'Testy obciążeniowe i monitorowanie'):
        add(name, False, 'manual', 'Wymaga osobnego protokołu i potwierdzenia przed startem')
    return {'ready_for_production': False, 'automated_errors': sum(not c['passed'] for c in checks if c['severity']=='error'),
            'checks': checks, 'note': 'To audyt przygotowania, nie certyfikat bezpieczeństwa ani zgoda na wdrożenie.'}


def main():
    print(json.dumps(release_report(), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
