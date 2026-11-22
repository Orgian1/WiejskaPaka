"""Create a separate systemd environment file for the public demo notices."""

from datetime import datetime
from getpass import getpass
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo
import sys


CONFIG_PATH = Path('/etc/wiejskapaka/demo-legal.env')


def quote_value(value):
    if not value or any(not char.isprintable() for char in value):
        raise ValueError('Każde pole musi zawierać tekst w jednym wierszu.')
    escaped = value.replace('\\', '\\\\').replace('"', '\\"')
    return '"' + escaped + '"'


def write_environment(path, details):
    content = ''.join(f'{key}={quote_value(value)}\n' for key, value in details.items())
    with NamedTemporaryFile(
        mode='w', encoding='utf-8', dir=path.parent, delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)
        try:
            temp_file.write(content)
            temp_file.close()
            temp_path.replace(path)
        finally:
            temp_path.unlink(missing_ok=True)


def main():
    if not sys.stdin.isatty():
        raise SystemExit('Uruchom konfigurator bezpośrednio w terminalu VPS.')
    print('Wpisane dane będą widoczne w publicznych dokumentach demo.')
    try:
        details = {
            'WP_DEMO_OPERATOR_ADDRESS': getpass('Pełny adres operatora (wpis jest ukryty): ').strip(),
            'WP_DEMO_LEGAL_DATE': datetime.now(ZoneInfo('Europe/Warsaw')).strftime('%d.%m.%Y'),
            'WP_DEMO_DATA_RETENTION': input('Rzeczywisty czas lub zasady przechowywania danych: ').strip(),
            'WP_DEMO_DATA_PROVIDERS': input('Pozostali dostawcy i ich role (hosting netcup jest wpisany): ').strip(),
        }
        write_environment(CONFIG_PATH, details)
    except (EOFError, KeyboardInterrupt):
        raise SystemExit('\nAnulowano konfigurację.') from None
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from None
    print('Zapisano konfigurację dokumentów demo.')


if __name__ == '__main__':
    main()
