"""Local contact mailbox for the disposable demo; never sends real email."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import threading
import time
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field, StringConstraints, field_validator
from backend.password_reset import prepare_outbox

KEY = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
Text = Annotated[str, StringConstraints(strict=True, strip_whitespace=True)]


class ContactMessage(BaseModel):
    model_config = {'extra': 'forbid'}
    request_key: str = Field(strict=True, pattern=KEY.pattern)
    topic: Literal['contact', 'problem']
    email: Text = Field(min_length=5, max_length=254)
    subject: Text = Field(min_length=3, max_length=160)
    message: Text = Field(min_length=10, max_length=4000)

    @field_validator('email')
    @classmethod
    def email_address(cls, value):
        if any(ord(char) <= 32 or ord(char) == 127 for char in value) or not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', value):
            raise ValueError('Nieprawidłowy adres e-mail')
        return value.lower()

    @field_validator('subject', 'message')
    @classmethod
    def plain_text(cls, value, info):
        allowed = '\n\t' if info.field_name == 'message' else ''
        if any((ord(char) < 32 and char not in allowed) or ord(char) == 127 for char in value):
            raise ValueError('Niedozwolony znak sterujący')
        return value


class Mailbox:
    """Bounded, private files; serialized writes in the single-worker demo."""
    def __init__(self, folder, *, clock=time.monotonic):
        path = Path(folder)
        project = Path(__file__).resolve().parents[1]
        if not path.is_absolute() or path.resolve().is_relative_to(project):
            raise ValueError('Skrzynka kontaktowa musi być poza projektem')
        self.folder = prepare_outbox(path)
        self.clock = clock
        self.lock = threading.RLock()
        self.budgets = {}

    def files(self):
        prepare_outbox(self.folder)
        return [p for p in self.folder.glob('*.json') if KEY.fullmatch(p.stem)]

    def read(self, path):
        if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError('Nieprawidłowy plik skrzynki')
        if path.stat().st_size > 32768:
            raise ValueError('Nieprawidłowy plik skrzynki')
        with path.open(encoding='utf-8') as stream:
            data = json.load(stream)
        if data.get('id') != path.stem or data.get('test_only') is not True:
            raise ValueError('Nieprawidłowy plik skrzynki')
        return data

    def submit(self, payload):
        fields = payload.model_dump(exclude={'request_key'})
        digest = hashlib.sha256(json.dumps(fields, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        path = self.folder / (payload.request_key + '.json')
        with self.lock:
            prepare_outbox(self.folder)
            if path.exists() or path.is_symlink():
                existing = self.read(path)
                if not secrets.compare_digest(existing.get('fingerprint', ''), digest):
                    raise HTTPException(409, 'Ten identyfikator dotyczy innej wiadomości.')
                return {'id': payload.request_key, 'mode': 'local_test', 'stored': True}
            now = self.clock()
            self.budgets = {key: value for key, value in self.budgets.items() if now - value[0] < 3600}
            start, count = self.budgets.get(payload.email, (now, 0))
            if count >= 5:
                raise HTTPException(429, 'Limit 5 wiadomości na godzinę. Spróbuj później.', headers={'Retry-After': str(max(1, int(3600 - (now-start))))})
            if len(self.files()) >= 1000:
                raise HTTPException(503, 'Testowa skrzynka jest pełna.')
            data = {'id': payload.request_key, **fields, 'fingerprint': digest,
                    'created_at': datetime.now(timezone.utc).isoformat(), 'test_only': True}
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                    json.dump(data, stream, ensure_ascii=False)
                    stream.flush()
                    os.fsync(stream.fileno())
            except BaseException:
                path.unlink(missing_ok=True)
                raise
            self.budgets[payload.email] = (start, count + 1)
            return {'id': payload.request_key, 'mode': 'local_test', 'stored': True}

    def listing(self, offset, limit):
        with self.lock:
            records = [self.read(p) for p in self.files()]
            records.sort(key=lambda item: (item['created_at'], item['id']), reverse=True)
            items = [{k: v for k, v in item.items() if k != 'fingerprint'} for item in records[offset:offset+limit]]
            return {'mode': 'local_test', 'items': items, 'total': len(records),
                    'offset': offset, 'limit': limit, 'has_more': offset+limit < len(records)}


def install(app, current_user, environ, database_url):
    mode = environ.get('WP_ENV', 'development').strip().lower()
    other_mode = environ.get('WIEJSKAPAKA_ENV', 'development').strip().lower()
    enabled = (not database_url and environ.get('WP_ENABLE_TEST_CONTACT') == '1'
               and mode in ('development', 'dev', 'test', 'testing')
               and other_mode not in ('prod', 'production', 'live'))
    mailbox = Mailbox(environ.get('WP_TEST_CONTACT_OUTBOX', '')) if enabled else None

    @app.get('/test/contact/options')
    def options():
        return {'enabled': enabled, 'mode': 'local_test' if enabled else None}

    # Keep file-backed test endpoints out of PostgreSQL and non-demo apps.
    if not enabled:
        return

    @app.post('/test/contact/messages', status_code=202)
    def submit(payload: ContactMessage):
        try:
            return mailbox.submit(payload)
        except (OSError, ValueError, TypeError, KeyError):
            raise HTTPException(503, 'Nie można zapisać wiadomości w skrzynce testowej.') from None

    @app.get('/test/admin/contact/messages')
    def listing(offset: int = Query(default=0, ge=0, le=1000),
                limit: int = Query(default=20, ge=1, le=20), user=Depends(current_user)):
        if user['role'] != 'admin':
            raise HTTPException(403, 'Brak uprawnień')
        try:
            return mailbox.listing(offset, limit)
        except (OSError, ValueError, TypeError, KeyError):
            raise HTTPException(503, 'Nie można odczytać skrzynki testowej.') from None
