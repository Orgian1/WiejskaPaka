"""Opt-in public seller handles; authentication still uses private email."""
import os
import re
import sqlite3
from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel, Field
from backend.local_marketplace import search_key
from backend.pg_adapter import PgUniqueViolation

RESERVED = {'admin','administrator','moderator','support','pomoc','system','root','wiejskapaka','pomoc_techniczna'}
SCHEMA_SQLITE = '''CREATE TABLE IF NOT EXISTS seller_public_logins (
 user_id INTEGER PRIMARY KEY REFERENCES users(id),
 login TEXT NOT NULL UNIQUE CHECK(length(login) BETWEEN 3 AND 30 AND login=lower(login)
   AND substr(login,1,1) GLOB '[a-z]' AND login NOT GLOB '*[^a-z0-9_]*'),
 farm_name_key TEXT NOT NULL
);'''


def enabled():
    return os.environ.get('WP_ENABLE_SELLER_SEARCH') == '1'


def normalize_login(value):
    login = value.strip().removeprefix('@').lower()
    if not re.fullmatch(r'[a-z][a-z0-9_]{2,29}', login) or login in RESERVED:
        raise HTTPException(422, 'Login: 3–30 znaków a–z, cyfr lub podkreślenia; pierwszy znak to litera. Wybierz nazwę inną niż zastrzeżone nazwy obsługi.')
    return login


def sync_name(con, user_id, farm_name):
    con.execute('UPDATE seller_public_logins SET farm_name_key=? WHERE user_id=?', (search_key(farm_name.strip()), user_id))


def refresh_index(con, *, postgres=False):
    rows = con.execute('''SELECT s.user_id,s.farm_name_key,COALESCE(f.farm_name,'') AS farm_name
        FROM seller_public_logins s LEFT JOIN farmer_profiles f ON f.user_id=s.user_id'''
        + (' FOR UPDATE OF s' if postgres else '')).fetchall()
    for row in rows:
        if row['farm_name_key'] != search_key(row['farm_name']):
            sync_name(con, row['user_id'], row['farm_name'])


class PublicLoginIn(BaseModel):
    model_config = {'extra': 'forbid'}
    login: str = Field(strict=True, min_length=3, max_length=32)


def register_routes(app, db, write_db, current_user):
    def require_enabled():
        if not enabled():
            raise HTTPException(503, 'Wyszukiwanie sprzedawców nie zostało jeszcze włączone.')

    @app.get('/sellers/config')
    def seller_config():
        return {'enabled': enabled()}

    @app.get('/sellers/me/login')
    def my_public_login(user=Depends(current_user), authorization: str | None = Header(default=None)):
        require_enabled()
        if user['role'] != 'rolnik':
            raise HTTPException(403, 'Login sprzedawcy jest dostępny dla rolnika.')
        with write_db(user, authorization, ('rolnik',)) as con:
            row = con.execute('SELECT login FROM seller_public_logins WHERE user_id=?', (user['id'],)).fetchone()
        return {'login': row['login'] if row else None}

    @app.put('/sellers/me/login')
    def set_public_login(body: PublicLoginIn, user=Depends(current_user), authorization: str | None = Header(default=None)):
        require_enabled()
        if user['role'] != 'rolnik':
            raise HTTPException(403, 'Login sprzedawcy jest dostępny dla rolnika.')
        login = normalize_login(body.login)
        try:
            with write_db(user, authorization, ('rolnik',)) as con:
                profile = con.execute('SELECT farm_name FROM farmer_profiles WHERE user_id=?', (user['id'],)).fetchone()
                con.execute('''INSERT INTO seller_public_logins(user_id,login,farm_name_key) VALUES(?,?,?)
                    ON CONFLICT(user_id) DO UPDATE SET login=excluded.login,farm_name_key=excluded.farm_name_key''',
                    (user['id'], login, search_key(profile['farm_name']) if profile else ''))
        except (sqlite3.IntegrityError, PgUniqueViolation):
            raise HTTPException(409, 'Ten login jest już zajęty. Wybierz inny.') from None
        return {'login': login}

    @app.get('/sellers/search')
    def seller_search(q: str = '', limit: int = 24, offset: int = 0):
        require_enabled()
        if len(q) > 120 or not 1 <= limit <= 100 or not 0 <= offset <= 10000:
            raise HTTPException(422, 'Nieprawidłowe parametry wyszukiwania.')
        raw = q.strip()
        login_only = raw.startswith('@')
        key = search_key(raw.removeprefix('@'))
        escaped = key.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        where = "u.role='rolnik'"
        parameters = []
        if key:
            where += " AND (s.login LIKE ? ESCAPE '\\'" + (')' if login_only else " OR s.farm_name_key LIKE ? ESCAPE '\\')")
            parameters.append('%'+escaped+'%')
            if not login_only:
                parameters.append('%'+escaped+'%')
        elif login_only:
            raise HTTPException(422, 'Wpisz login po znaku @.')
        source = '''seller_public_logins s JOIN users u ON u.id=s.user_id
            LEFT JOIN farmer_profiles f ON f.user_id=s.user_id'''
        with db() as con:
            total = con.execute('SELECT COUNT(*) AS n FROM '+source+' WHERE '+where, tuple(parameters)).fetchone()['n']
            rows = con.execute('''SELECT s.user_id AS farmer_id,s.login,
                COALESCE(f.farm_name,'') AS farm_name,COALESCE(f.city,'') AS city FROM '''+source+' WHERE '+where+'''
                ORDER BY CASE WHEN s.login=? THEN 0 WHEN s.login LIKE ? ESCAPE '\\' THEN 1 ELSE 2 END,s.login,s.user_id LIMIT ? OFFSET ?''',
                (*parameters, key, escaped+'%', limit, offset)).fetchall()
        return {'items': [dict(row) for row in rows], 'total': total, 'limit': limit, 'offset': offset}
