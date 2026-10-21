"""WiejskaPaka API - local development, no real payments."""
import hashlib
import json
import re
import os
import secrets
import sqlite3
from contextlib import contextmanager, asynccontextmanager
from backend.pg_adapter import postgres_db, init_postgres, PgUniqueViolation
from backend.delivery_access import courier_may_see_address
from backend.order_lifecycle import require_transition
from backend.time_safety import is_future
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Annotated, Literal
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

# Blokada przypadkowego wdrożenia developerskiej aplikacji do produkcji.
from backend.deployment_guard import assert_safe_environment
assert_safe_environment()

DB_PATH = os.environ.get('WIEJSKAPAKA_DB', str(Path(__file__).with_name('wiejskapaka.sqlite3')))
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
from backend.inventory_reservations import add_hold, payment_deadline_passed, expire_due, has_hold_capacity
from backend import product_unit_storage


def run_reservation_expiry(*, now=None):
    with db() as con:
        if not DATABASE_URL:
            con.execute('BEGIN IMMEDIATE')
        return expire_due(con, now=now or datetime.now(timezone.utc), postgres=bool(DATABASE_URL),
                          record_event=record_order_event)


@asynccontextmanager
async def application_lifespan(application):
    import asyncio
    import logging
    if product_unit_storage.enabled():
        with db() as con:
            con.execute('SELECT product_id,unit,content_json FROM product_sale_units LIMIT 0')
            con.execute('SELECT order_id,unit,content_json FROM order_sale_units LIMIT 0')
    else:
        with db() as con:
            if DATABASE_URL:
                present = con.execute("SELECT to_regclass('public.product_sale_units') AS name").fetchone()['name'] is not None
            else:
                present = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product_sale_units'").fetchone() is not None
            if present and con.execute("SELECT product_id FROM product_sale_units WHERE unit<>'szt' OR content_json IS NOT NULL LIMIT 1").fetchone():
                raise RuntimeError('Nie można wyłączyć jednostek przy istniejących produktach z jednostkami')
    # A missing PostgreSQL migration must block startup, not silently disable holds.
    with db() as con:
        con.execute('SELECT order_id,expires_at,released_at FROM inventory_reservations LIMIT 0')
    with db() as con:
        con.execute('SELECT order_id FROM order_purchase_records LIMIT 0')
        if os.environ.get('WP_ENABLE_TEST_PAYMENTS') == '1':
            con.execute('SELECT id,revision FROM support_cases LIMIT 0')
            con.execute('SELECT case_id,revision FROM support_case_events LIMIT 0')
    with db() as con:
        con.execute('SELECT point_id FROM pickup_point_coordinates LIMIT 0')
        from backend.local_marketplace import refresh_product_index
        refresh_product_index(con, postgres=bool(DATABASE_URL))
    async def sweep():
        while True:
            try:
                await asyncio.to_thread(run_reservation_expiry)
            except Exception:
                # Never log addresses, credentials, DSNs or exception payloads.
                logging.getLogger(__name__).error('Inventory reservation sweep failed; retry in 30 seconds')
            try:
                await asyncio.to_thread(run_checkout_retention)
            except Exception:
                logging.getLogger(__name__).error('Checkout PIN retention sweep failed; retry in 30 seconds')
            await asyncio.sleep(30)
    task = asyncio.create_task(sweep())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


ph = PasswordHasher()
# A non-account hash gives unknown emails the same password verification work.
DUMMY_PASSWORD_HASH = '$argon2id$v=19$m=65536,t=3,p=4$FuCEYNBvEI5vPMxnciLIcg$/sXtzHuVlnbMmS0yL5rz+AXOzTNf8GTCQV+98Q6U2zo'
CleanText = Annotated[str, StringConstraints(strip_whitespace=True)]
app = FastAPI(title='WiejskaPaka API', version='0.3.0', description='Środowisko testowe. Brak prawdziwych płatności.', lifespan=application_lifespan)
SECURITY_RESPONSE_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'no-referrer',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=(self), payment=()',
    'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; form-action 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
}


@app.exception_handler(Exception)
async def private_server_error(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={'detail': 'Błąd serwera. Spróbuj ponownie później.'},
                        headers={**SECURITY_RESPONSE_HEADERS, 'Cache-Control': 'no-store', 'Pragma': 'no-cache'})

@app.exception_handler(RequestValidationError)
async def private_validation_error(request: Request, exc: RequestValidationError):
    # Pydantic's input/context can contain credentials, PINs or full addresses.
    return JSONResponse(status_code=422, content={'detail': [
        {key: error[key] for key in ('loc', 'msg', 'type') if key in error}
        for error in exc.errors()
    ]})

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.update(SECURITY_RESPONSE_HEADERS)
        # Bezpieczna reguła domyślna: nowe endpointy nie mogą przypadkowo
        # udostępnić danych prywatnych pamięci podręcznej przeglądarki.
        public_get_paths = {'/', '/health', '/products', '/marketplace/accounting-policy'}
        is_public = request.method in ('GET', 'HEAD') and (
            request.url.path in public_get_paths or
            request.url.path.startswith('/assets/')
        )
        response.headers['Cache-Control'] = 'no-cache' if is_public else 'no-store'
        if not is_public:
            response.headers['Pragma'] = 'no-cache'
        return response

from backend.http_limits import RequestBodyLimitMiddleware
app.add_middleware(RequestBodyLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

@contextmanager
def db():
    if DATABASE_URL:
        with postgres_db(DATABASE_URL) as con:
            yield con
        return
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def init_db():
    if DATABASE_URL:
        init_postgres(DATABASE_URL)
        return
    with db() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('klient','rolnik','dostawca','admin')));
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, farmer_id INTEGER NOT NULL REFERENCES users(id), name TEXT NOT NULL, price_grosze INTEGER NOT NULL CHECK(price_grosze>=1), delivery_grosze INTEGER NOT NULL CHECK(delivery_grosze>=0), stock INTEGER NOT NULL CHECK(stock>=0));
        CREATE TABLE IF NOT EXISTS login_attempts(email TEXT PRIMARY KEY, failures INTEGER NOT NULL DEFAULT 0, locked_until TEXT);
        CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, buyer_id INTEGER NOT NULL REFERENCES users(id), farmer_id INTEGER NOT NULL REFERENCES users(id), product_id INTEGER NOT NULL REFERENCES products(id), quantity INTEGER NOT NULL CHECK(quantity>0), subtotal_grosze INTEGER NOT NULL, delivery_grosze INTEGER NOT NULL, total_grosze INTEGER NOT NULL, fulfillment TEXT NOT NULL, status TEXT NOT NULL, pickup_code TEXT UNIQUE NOT NULL, pin_hash TEXT NOT NULL, pin_attempts INTEGER NOT NULL DEFAULT 0, pin_used INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, confirmed_at TEXT);
        ''')
init_db()

def migrate_stage3():
    if DATABASE_URL:
        return  # PostgreSQL schema v1 includes these tables
    # Migracja lokalnej bazy SQLite
    with db() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS farmer_profiles(
            user_id INTEGER PRIMARY KEY REFERENCES users(id), farm_name TEXT NOT NULL,
            city TEXT NOT NULL, description TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS pickup_points(
            id INTEGER PRIMARY KEY, farmer_id INTEGER NOT NULL REFERENCES users(id),
            name TEXT NOT NULL, city TEXT NOT NULL, street TEXT NOT NULL,
            opening_hours TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS order_locations(
            order_id INTEGER PRIMARY KEY REFERENCES orders(id),
            pickup_point_id INTEGER REFERENCES pickup_points(id),
            delivery_city TEXT, delivery_street TEXT, delivery_postal_code TEXT,
            CHECK ((pickup_point_id IS NOT NULL AND delivery_city IS NULL AND delivery_street IS NULL AND delivery_postal_code IS NULL)
                OR (pickup_point_id IS NULL AND delivery_city IS NOT NULL AND delivery_street IS NOT NULL AND delivery_postal_code IS NOT NULL)));
        ''')
migrate_stage3()

def migrate_stage9():
    """Idempotent local upgrade. PostgreSQL upgrade SQL is in database/upgrade_09.sql."""
    if DATABASE_URL:
        return
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS delivery_assignments (
          order_id INTEGER PRIMARY KEY REFERENCES orders(id),
          courier_id INTEGER NOT NULL REFERENCES users(id),
          assigned_by INTEGER NOT NULL REFERENCES users(id),
          assigned_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_events (
          id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id),
          actor_id INTEGER REFERENCES users(id), event_type TEXT NOT NULL,
          previous_status TEXT, new_status TEXT, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS order_events_order_idx ON order_events(order_id,id);
        """)
migrate_stage9()

def migrate_stage10():
    """Local inbox migration; PostgreSQL upgrade in database/upgrade_10.sql."""
    if DATABASE_URL:
        return
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS notifications (
          id INTEGER PRIMARY KEY,
          user_id INTEGER NOT NULL REFERENCES users(id),
          order_id INTEGER NOT NULL REFERENCES orders(id),
          event_type TEXT NOT NULL,
          title TEXT NOT NULL,
          body TEXT NOT NULL,
          created_at TEXT NOT NULL,
          read_at TEXT,
          UNIQUE(user_id,order_id,event_type,created_at)
        );
        CREATE INDEX IF NOT EXISTS notifications_user_idx ON notifications(user_id,id);
        """)
migrate_stage10()

class Register(BaseModel):
    email: CleanText = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=256)
    role: Literal['klient','rolnik','dostawca']
class Login(BaseModel):
    email: CleanText = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=256)
class ProductIn(BaseModel):
    name: CleanText = Field(min_length=2, max_length=120)
    price_grosze: int = Field(strict=True, ge=1, le=100_000_000)
    delivery_grosze: int = Field(strict=True, ge=0, le=10_000_000)
    stock: int = Field(strict=True, ge=0, le=1_000_000)
    sale_unit: Literal['szt','kg','g','l','ml','opak','peczek','sloik','butelka','worek','skrzynka','tacka'] = 'szt'
    content_amount: str | None = Field(default=None, max_length=32)
    content_unit: Literal['szt','kg','g','l','ml'] | None = None

    @model_validator(mode='after')
    def validate_sale_unit(self):
        from backend.product_units import package_content
        package_content(self.sale_unit, self.content_amount, self.content_unit)
        return self
class OrderIn(BaseModel):
    pickup_point_id: int | None = Field(strict=True, default=None, ge=1)
    delivery_city: CleanText | None = Field(default=None, min_length=2, max_length=120)
    delivery_street: CleanText | None = Field(default=None, min_length=3, max_length=180)
    delivery_postal_code: CleanText | None = Field(default=None, pattern=r'^\d{2}-\d{3}$')
    product_id: int = Field(strict=True, ge=1)
    quantity: int = Field(strict=True, ge=1, le=1000)
    fulfillment: Literal['odbior','dostawa']
class ConfirmIn(BaseModel):
    pin: str = Field(pattern=r'^\d{6}$')
    checked_goods: bool = Field(strict=True)

def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()

def current_user(authorization: str | None = Header(default=None)):
    from backend.neon_session_bridge import parse_bearer, AuthenticationFailed
    from backend.neon_auth_policy import active_session
    try:
        token = parse_bearer(authorization)
    except AuthenticationFailed:
        raise HTTPException(401, 'Wymagane logowanie')
    with db() as con:
        row = con.execute('SELECT u.id,u.role,u.email,s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?', (token_hash(token),)).fetchone()
    if not row or not active_session(row['id'], row['expires_at'], datetime.now(timezone.utc)):
        raise HTTPException(401, 'Sesja nieważna')
    return {key: row[key] for key in ('id', 'role', 'email')}

@contextmanager
def order_write_db(user, authorization, allowed_roles):
    """Reauthenticate the actor in the same transaction as every mutation."""
    if DATABASE_URL:
        from backend.verified_writes import verified_order_write, WriteAuthorizationError
        from backend.neon_session_bridge import AuthenticationFailed
        try:
            with verified_order_write(DATABASE_URL, authorization, user, allowed_roles) as con:
                yield con
        except AuthenticationFailed:
            raise HTTPException(401, 'Sesja nieważna')
        except WriteAuthorizationError:
            raise HTTPException(403, 'Brak uprawnień')
    else:
        with db() as con:
            if not DATABASE_URL:
                con.execute('BEGIN IMMEDIATE')
            authorize_transaction(con,user,authorization,allowed_roles)
            yield con

def require(user, role):
    if user['role'] != role:
        raise HTTPException(403, 'Brak uprawnień')

def authorize_local_transaction(con,user,authorization,allowed_roles):
    if not DATABASE_URL:authorize_transaction(con,user,authorization,allowed_roles)


def authorize_transaction(con,user,authorization,allowed_roles):
    from backend.neon_session_bridge import parse_bearer, AuthenticationFailed
    from backend.neon_auth_policy import active_session
    try:session_token=parse_bearer(authorization)
    except AuthenticationFailed:raise HTTPException(401,'Sesja nieważna')
    actor=con.execute('SELECT u.id,u.role,s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?',
                      (token_hash(session_token),)).fetchone()
    if not actor or not active_session(actor['id'],actor['expires_at'],datetime.now(timezone.utc)):
        raise HTTPException(401,'Sesja nieważna')
    if actor['id']!=user['id'] or actor['role']!=user['role'] or actor['role'] not in allowed_roles:
        raise HTTPException(403,'Brak uprawnień')


def lock_buyer_operation(con, buyer_id):
    """Serialize cart changes and checkout retries before reading request keys."""
    if DATABASE_URL:
        con.execute('SELECT pg_advisory_xact_lock(hashtextextended(?,0))',
                    (f'wp:buyer:{buyer_id}',))

@app.get('/health')
def health():
    return {'status':'ok', 'mode':'test'}

@app.post('/auth/register', status_code=201)
def register(payload: Register):
    email = payload.email.strip().lower()
    if '@' not in email or email.startswith('@') or email.endswith('@'):
        raise HTTPException(422, 'Nieprawidłowy adres e-mail')
    with db() as con:
        try:
            cur = con.execute('INSERT INTO users(email,password_hash,role) VALUES(?,?,?)', (email,ph.hash(payload.password),payload.role))
        except (sqlite3.IntegrityError, PgUniqueViolation):
            raise HTTPException(409, 'Adres e-mail jest już używany')
        return {'id':cur.lastrowid, 'role':payload.role}

@app.post('/auth/login')
def login(payload: Login):
    email = payload.email.strip().lower()
    now = datetime.now(timezone.utc)
    with db() as con:
        if not DATABASE_URL:
            con.execute('BEGIN IMMEDIATE')
        if DATABASE_URL:
            con.execute('SELECT pg_advisory_xact_lock(hashtext(?))', (email,))
        attempt = con.execute('SELECT failures,locked_until FROM login_attempts WHERE email=?', (email,)).fetchone()
        if attempt and attempt['locked_until'] and is_future(attempt['locked_until'], now):
            raise HTTPException(429, 'Zbyt wiele prób logowania. Spróbuj ponownie później.')
        if attempt and attempt['locked_until']:
            # The previous window ended; five new failures are allowed.
            attempt = None
        row = con.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        valid = False
        try:
            verified = ph.verify(row['password_hash'] if row else DUMMY_PASSWORD_HASH, payload.password)
            valid = bool(row and verified)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            pass
        if not valid:
            failures = (attempt['failures'] if attempt else 0) + 1
            locked_until = (now + timedelta(minutes=15)).isoformat() if failures >= 5 else None
            con.execute('INSERT INTO login_attempts(email,failures,locked_until) VALUES(?,?,?) ON CONFLICT(email) DO UPDATE SET failures=excluded.failures,locked_until=excluded.locked_until',
                (email, failures, locked_until))
            # Do not raise inside db context: otherwise failed-attempt counter rolls back.
            result = None
        else:
            con.execute('DELETE FROM login_attempts WHERE email=?', (email,))
            token = secrets.token_urlsafe(32)
            expires = (now + timedelta(hours=12)).isoformat()
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                        (token_hash(token), row['id'], expires))
            result = {'access_token':token,'token_type':'bearer','expires_at':expires}
    if result is None:
        raise HTTPException(401, 'Nieprawidłowe dane logowania')
    return result

@contextmanager
def account_session_db(user,authorization):
    """Lock with login/password changes, then recheck the actual session."""
    roles=('klient','rolnik','dostawca','admin')
    with order_write_db(user,authorization,roles) as con:
        if DATABASE_URL:con.execute('SELECT pg_advisory_xact_lock(hashtext(?))',(user['email'].strip().lower(),))
        authorize_transaction(con,user,authorization,roles)
        yield con


@app.get('/auth/sessions')
def my_sessions(user=Depends(current_user),authorization: str | None=Header(default=None)):
    from backend.session_security import session_overview,SessionInactiveError
    with account_session_db(user,authorization) as con:
        try:return session_overview(con,user['id'],token_hash(authorization[7:]))
        except SessionInactiveError:raise HTTPException(401,'Sesja nieważna')


@app.post('/auth/logout-others')
def logout_other_sessions(user=Depends(current_user),authorization: str | None=Header(default=None)):
    from backend.session_security import revoke_other_sessions
    with account_session_db(user,authorization) as con:
        return revoke_other_sessions(con,user['id'],token_hash(authorization[7:]))


@app.post('/auth/logout')
def logout(authorization: str | None = Header(default=None), user=Depends(current_user)):
    with account_session_db(user,authorization) as con:
        con.execute('DELETE FROM sessions WHERE token_hash=?',(token_hash(authorization[7:]),))
    return {'ok':True}

@app.post('/products',status_code=201)
def create_product(payload: ProductIn, user=Depends(current_user), authorization: str | None = Header(default=None)):
    require(user,'rolnik')
    if not product_unit_storage.enabled() and (payload.sale_unit != 'szt' or payload.content_amount is not None or payload.content_unit is not None):
        raise HTTPException(503, 'Jednostki sprzedaży nie zostały jeszcze włączone')
    with order_write_db(user, authorization, ('rolnik',)) as con:
        cur = con.execute('INSERT INTO products(farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?)',(user['id'],payload.name,payload.price_grosze,payload.delivery_grosze,payload.stock))
        from backend.local_marketplace import index_product
        index_product(con, cur.lastrowid, payload.name)
        if product_unit_storage.enabled():
            product_unit_storage.insert_product_unit(con, cur.lastrowid, payload.sale_unit, payload.content_amount, payload.content_unit)
        return {'id':cur.lastrowid}


@app.get('/product-units')
def product_units_configuration():
    from backend.product_units import UNITS
    return {'enabled': product_unit_storage.enabled(), 'fractional_quantities': False,
            'units': [{'code': code, 'label': unit.label, 'packaged': unit.packaged}
                      for code, unit in UNITS.items()]}

@app.get('/products')
def products():
    with db() as con:
        return [product_unit_storage.enrich_product(con,r) for r in con.execute('SELECT id,farmer_id,name,price_grosze,delivery_grosze,stock FROM products WHERE stock>0 ORDER BY id DESC')]

@app.get('/catalog/search')
def catalog_search(q: str = '', min_price_grosze: int | None = None,
                   max_price_grosze: int | None = None, limit: int = 24,
                   offset: int = 0):
    """Public product search with bounded pagination; amounts are integer grosze."""
    if len(q) > 120 or not (1 <= limit <= 100) or not (0 <= offset <= 10000):
        raise HTTPException(422, 'Nieprawidłowe parametry wyszukiwania')
    if any(v is not None and (v < 0 or v > 9_000_000_000_000_000_000)
           for v in (min_price_grosze, max_price_grosze)):
        raise HTTPException(422, 'Nieprawidłowy zakres cen')
    if min_price_grosze is not None and max_price_grosze is not None and min_price_grosze > max_price_grosze:
        raise HTTPException(422, 'Nieprawidłowy zakres cen')
    clauses = ['stock > 0']
    params = []
    if q.strip():
        # Escape SQL LIKE wildcards: a customer search is literal, not a pattern.
        from backend.local_marketplace import search_key
        escaped = search_key(q.strip()).replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        clauses.append("COALESCE(s.name_key,LOWER(p.name)) LIKE ? ESCAPE '\\'")
        params.append('%' + escaped + '%')
    if min_price_grosze is not None:
        clauses.append('price_grosze >= ?')
        params.append(min_price_grosze)
    if max_price_grosze is not None:
        clauses.append('price_grosze <= ?')
        params.append(max_price_grosze)
    where = ' AND '.join(clauses)
    with db() as con:
        source = 'products p LEFT JOIN product_search_names s ON s.product_id=p.id'
        total = con.execute('SELECT COUNT(*) AS n FROM ' + source + ' WHERE ' + where, tuple(params)).fetchone()['n']
        rows = con.execute('SELECT id,farmer_id,name,price_grosze,delivery_grosze,stock FROM ' + source + ' WHERE '
                           + where + ' ORDER BY id DESC LIMIT ? OFFSET ?', tuple(params + [limit, offset])).fetchall()
        items = [product_unit_storage.enrich_product(con,row) for row in rows]
    return {'items': items, 'total': total, 'limit': limit, 'offset': offset}

@app.get('/products/mine')
def my_products(user=Depends(current_user), authorization: str | None = Header(default=None)):
    require(user, 'rolnik')
    with order_write_db(user, authorization, ('rolnik',)) as con:
        return [product_unit_storage.enrich_product(con,r) for r in con.execute('SELECT id,name,price_grosze,delivery_grosze,stock FROM products WHERE farmer_id=? ORDER BY id DESC', (user['id'],))]

@app.get('/products/{product_id}')
def product_details(product_id: int):
    """Public listing details; unavailable products are not exposed as purchasable."""
    if product_id < 1:
        raise HTTPException(404, 'Nie znaleziono produktu')
    with db() as con:
        row = con.execute(
            'SELECT id,farmer_id,name,price_grosze,delivery_grosze,stock '
            'FROM products WHERE id=? AND stock>0', (product_id,)
        ).fetchone()
        if row is not None:
            row = product_unit_storage.enrich_product(con,row)
    if row is None:
        raise HTTPException(404, 'Produkt niedostępny')
    return dict(row)

class CartItemIn(BaseModel):
    product_id: int = Field(strict=True, ge=1)
    quantity: int = Field(strict=True, ge=1, le=1000)

class CartQuoteIn(BaseModel):
    items: list[CartItemIn] = Field(min_length=1, max_length=500)
    fulfillment: Literal['odbior', 'dostawa']

# B/371-400: persisted basket, no payment and no inventory reservation.
def migrate_saved_cart():
    if DATABASE_URL:
        return  # Apply database/upgrade_b371_saved_cart.sql manually first.
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS saved_cart_items (
            buyer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 1000),
            PRIMARY KEY(buyer_id,product_id))""")

migrate_saved_cart()

class SavedCartItemIn(BaseModel):
    product_id: int = Field(strict=True, ge=1)
    quantity: int = Field(strict=True, ge=1, le=1000)

@app.get('/cart/items')
def saved_cart_get(user=Depends(current_user)):
    require(user, 'klient')
    with db() as con:
        rows = con.execute("""SELECT c.product_id,c.quantity,p.name,p.price_grosze,
            p.delivery_grosze,p.stock,p.farmer_id FROM saved_cart_items c
            LEFT JOIN products p ON p.id=c.product_id WHERE c.buyer_id=?
            ORDER BY c.product_id""", (user['id'],)).fetchall()
        items = [product_unit_storage.enrich_product(con,r) for r in rows]
    return {'items': items, 'payment_mode': 'test',
            'notice': 'Koszyk nie rezerwuje towaru ani nie gwarantuje ceny.'}

@app.put('/cart/items')
def saved_cart_put(payload: SavedCartItemIn, user=Depends(current_user), authorization: str | None = Header(default=None)):
    require(user, 'klient')
    with order_write_db(user, authorization, ('klient',)) as con:
        lock_buyer_operation(con, user['id'])
        product = con.execute('SELECT stock FROM products WHERE id=?', (payload.product_id,)).fetchone()
        if product is None or product['stock'] < payload.quantity:
            raise HTTPException(409, 'Produkt niedostępny lub niewystarczający stan')
        # Each farmer is a separate shipment: enforce the limit per seller,
        # not across unrelated shipments in the same buyer basket.
        farmer_id = con.execute('SELECT farmer_id FROM products WHERE id=?',
                                (payload.product_id,)).fetchone()['farmer_id']
        count = con.execute('''SELECT COUNT(*) AS n FROM saved_cart_items c
            JOIN products p ON p.id=c.product_id
            WHERE c.buyer_id=? AND p.farmer_id=?''',
            (user['id'], farmer_id)).fetchone()['n']
        exists = con.execute('SELECT 1 FROM saved_cart_items WHERE buyer_id=? AND product_id=?',
                             (user['id'], payload.product_id)).fetchone()
        if count >= 50 and not exists:
            raise HTTPException(422, 'Przesyłka jednego rolnika może zawierać maksymalnie 50 produktów')
        con.execute("""INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)
            ON CONFLICT(buyer_id,product_id) DO UPDATE SET quantity=excluded.quantity""",
            (user['id'],payload.product_id,payload.quantity))
    return {'saved': True, 'product_id': payload.product_id, 'quantity': payload.quantity}

@app.delete('/cart/items/{product_id}')
def saved_cart_delete(product_id: int, user=Depends(current_user), authorization: str | None = Header(default=None)):
    require(user, 'klient')
    if product_id < 1:
        raise HTTPException(422, 'Nieprawidłowy produkt')
    with order_write_db(user, authorization, ('klient',)) as con:
        lock_buyer_operation(con, user['id'])
        con.execute('DELETE FROM saved_cart_items WHERE buyer_id=? AND product_id=?',
                    (user['id'],product_id))
    return {'deleted': True}

@app.delete('/cart/items')
def saved_cart_clear(user=Depends(current_user), authorization: str | None = Header(default=None)):
    require(user, 'klient')
    with order_write_db(user, authorization, ('klient',)) as con:
        lock_buyer_operation(con, user['id'])
        con.execute('DELETE FROM saved_cart_items WHERE buyer_id=?', (user['id'],))
    return {'cleared': True}

@app.post('/cart/quote')
def cart_quote(payload: CartQuoteIn, user=Depends(current_user)):
    """Read-only indicative basket; checkout rechecks price/stock in a transaction.

    Delivery is charged per seller (maximum of listed delivery prices per seller),
    never per line item. Pickup is free in this estimate. No funds are collected.
    """
    require(user, 'klient')
    from backend.order_amount_limits import checked_order_total, MAX_DB_INTEGER
    ids = [item.product_id for item in payload.items]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, 'Połącz powtarzające się produkty w jedną pozycję')
    with db() as con:
        rows = {}
        for product_id in ids:
            row = con.execute('SELECT id,farmer_id,name,price_grosze,delivery_grosze,stock '
                              'FROM products WHERE id=?', (product_id,)).fetchone()
            if row is None:
                raise HTTPException(409, 'Produkt niedostępny')
            rows[product_id] = product_unit_storage.enrich_product(con,row)
    from collections import Counter
    per_farmer = Counter(rows[item.product_id]['farmer_id'] for item in payload.items)
    if any(count > 50 for count in per_farmer.values()):
        raise HTTPException(422, 'Przesyłka jednego rolnika może zawierać maksymalnie 50 produktów')
    subtotal = 0
    subtotals_by_farmer = {}
    result = []
    for item in payload.items:
        product = rows[item.product_id]
        if product['stock'] < item.quantity:
            raise HTTPException(409, 'Niewystarczający stan magazynowy')
        try:
            line, _ = checked_order_total(product['price_grosze'], item.quantity, 0)
        except ValueError:
            raise HTTPException(422, 'Nieprawidłowa kwota')
        if subtotal > MAX_DB_INTEGER - line:
            raise HTTPException(422, 'Przekroczono limit kwoty')
        subtotal += line
        farmer_id = product['farmer_id']
        subtotals_by_farmer[farmer_id] = subtotals_by_farmer.get(farmer_id, 0) + line
        result.append({'product_id': item.product_id, 'name': product['name'],
                       'quantity': item.quantity, 'unit_price_grosze': product['price_grosze'],
                       'line_total_grosze': line, 'farmer_id': farmer_id})
        if product_unit_storage.enabled():
            result[-1].update(sale_unit=product['sale_unit'], package_content=product['package_content'])
    from backend.shipping_policy import shipment_fees
    try:
        shipment_costs = shipment_fees(
            [rows[item.product_id] for item in payload.items], payload.fulfillment)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    delivery = sum(shipment_costs.values())
    if delivery > MAX_DB_INTEGER - subtotal:
        raise HTTPException(422, 'Przekroczono limit kwoty')
    return {'items': result, 'subtotal_grosze': subtotal, 'delivery_grosze': delivery,
            'total_grosze': subtotal + delivery, 'currency': 'PLN',
            'indicative': True, 'payment_mode': 'test',
            'shipment_fees_grosze': [{'farmer_id': seller, 'delivery_grosze': fee}
                                     for seller, fee in sorted(shipment_costs.items())],
            'shipments': [{'farmer_id': seller,
                           'items_count': per_farmer[seller],
                           'subtotal_grosze': subtotals_by_farmer[seller],
                           'delivery_grosze': shipment_costs[seller],
                           'total_grosze': subtotals_by_farmer[seller] + shipment_costs[seller]}
                          for seller in sorted(shipment_costs)],
            'notice': 'Wycena orientacyjna. Każde zamówienie jest weryfikowane ponownie przed zapisem.'}

# B/401-430: atomic checkout for a single seller; one order per basket line.
# No real payment. Existing order fulfilment and PIN flow are reused.
class SavedCartCheckoutIn(BaseModel):
    farmer_id: int | None = Field(strict=True, default=None, ge=1)
    fulfillment: Literal['odbior', 'dostawa']
    pickup_point_id: int | None = Field(strict=True, default=None, ge=1)
    delivery_city: CleanText | None = Field(default=None, min_length=2, max_length=120)
    delivery_street: CleanText | None = Field(default=None, min_length=3, max_length=180)
    delivery_postal_code: CleanText | None = Field(default=None, pattern=r'^\d{2}-\d{3}$')

def migrate_shipment_links():
    """Local-only, idempotent shipment grouping schema."""
    if DATABASE_URL:
        return  # Apply database/upgrade_b561_shipments.sql manually on PostgreSQL.
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS shipment_groups (
            id TEXT PRIMARY KEY, buyer_id INTEGER NOT NULL REFERENCES users(id),
            farmer_id INTEGER NOT NULL REFERENCES users(id),
            fulfillment TEXT NOT NULL CHECK(fulfillment IN ('odbior','dostawa')),
            delivery_grosze INTEGER NOT NULL CHECK(delivery_grosze>=0),
            created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS shipment_order_links (
            order_id INTEGER PRIMARY KEY REFERENCES orders(id),
            shipment_id TEXT NOT NULL REFERENCES shipment_groups(id))""")
        con.execute('CREATE INDEX IF NOT EXISTS shipment_order_links_group_idx ON shipment_order_links(shipment_id)')

migrate_shipment_links()

def migrate_checkout_idempotency():
    """SQLite-only migration; PostgreSQL uses the checked-in SQL migration."""
    if DATABASE_URL:
        return
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS checkout_idempotency (
            buyer_id INTEGER NOT NULL REFERENCES users(id),
            request_key TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            response_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(buyer_id, request_key))""")

migrate_checkout_idempotency()

from backend.checkout_vault import initialize as initialize_checkout_vault, CheckoutStorageError, PIN_RETENTION
from backend.pin_recovery import SCHEMA_SQLITE as PIN_RECOVERY_SCHEMA, backfill_links, link_reply
if not DATABASE_URL:
    with db() as _pin_con:_pin_con.executescript(PIN_RECOVERY_SCHEMA)
with db() as _vault_con:
    if not DATABASE_URL:_vault_con.execute('BEGIN IMMEDIATE')
    _vault_con.execute('SELECT order_id,buyer_id,request_key FROM checkout_pin_links LIMIT 0')
    _vault_con.execute('SELECT buyer_id,attempts,window_started_at FROM checkout_pin_access LIMIT 0')
    CHECKOUT_VAULT,_sealed_replies=initialize_checkout_vault(_vault_con,DB_PATH,postgres=bool(DATABASE_URL),key_path=os.environ.get('WP_CHECKOUT_KEY_FILE'))
    _linked_replies=backfill_links(_vault_con,CHECKOUT_VAULT)


def run_checkout_retention(*,now=None):
    from backend.checkout_vault import sweep
    with db() as con:
        if not DATABASE_URL:con.execute('BEGIN IMMEDIATE')
        return sweep(con,CHECKOUT_VAULT,now=now,postgres=bool(DATABASE_URL))


def cached_checkout_reply(row,buyer_id,request_key,*,expose_pin=True):
    try:return CHECKOUT_VAULT.open(row['response_json'],buyer_id,request_key,row['payload_hash'],expose_pin=expose_pin)
    except CheckoutStorageError as exc:raise HTTPException(409,str(exc)) from exc


def seal_checkout_reply(response,buyer_id,request_key,payload_hash):
    return CHECKOUT_VAULT.seal(response,buyer_id,request_key,payload_hash,
                              pin_until=(datetime.now(timezone.utc)+PIN_RETENTION).isoformat())


@app.get('/shipments/mine')
def my_shipments(user=Depends(current_user)):
    require(user, 'klient')
    with db() as con:
        rows = con.execute("""SELECT s.id,s.farmer_id,s.fulfillment,s.delivery_grosze,
            s.created_at,COUNT(l.order_id) AS item_count,COALESCE(SUM(o.total_grosze),0) AS total_grosze
            FROM shipment_groups s JOIN shipment_order_links l ON l.shipment_id=s.id
            JOIN orders o ON o.id=l.order_id
            WHERE s.buyer_id=? AND o.buyer_id=s.buyer_id
            GROUP BY s.id,s.farmer_id,s.fulfillment,s.delivery_grosze,s.created_at
            ORDER BY s.created_at DESC,s.id DESC""", (user['id'],)).fetchall()
        return {'shipments':[dict(row) for row in rows]}

@app.get('/shipments/farmer/mine')
def farmer_shipments(user=Depends(current_user)):
    require(user, 'rolnik')
    with db() as con:
        rows = con.execute("""SELECT s.id,s.fulfillment,s.delivery_grosze,s.created_at,
            COUNT(l.order_id) AS item_count,COALESCE(SUM(o.total_grosze),0) AS total_grosze
            FROM shipment_groups s JOIN shipment_order_links l ON l.shipment_id=s.id
            JOIN orders o ON o.id=l.order_id
            WHERE s.farmer_id=? AND o.farmer_id=s.farmer_id
            GROUP BY s.id,s.fulfillment,s.delivery_grosze,s.created_at
            ORDER BY s.created_at DESC,s.id DESC""", (user['id'],)).fetchall()
        return {'shipments':[dict(row) for row in rows]}

@app.get('/shipments/{shipment_id}/details')
def shipment_details(shipment_id: str, user=Depends(current_user)):
    # Authorized shipment view with item statuses and simulated refund summary.

    # Does not expose addresses, PIN hashes, or phone numbers.
    #
    if user['role'] not in ('klient', 'rolnik', 'dostawca'):
        raise HTTPException(403, 'Brak uprawnień')
    with db() as con:
        shipment = con.execute('SELECT id,buyer_id,farmer_id,fulfillment,delivery_grosze,created_at FROM shipment_groups WHERE id=?', (shipment_id,)).fetchone()
        if not shipment:
            raise HTTPException(404, 'Nie znaleziono przesyłki')
        if user['role'] == 'klient' and shipment['buyer_id'] != user['id']:
            raise HTTPException(404, 'Nie znaleziono przesyłki')
        if user['role'] == 'rolnik' and shipment['farmer_id'] != user['id']:
            raise HTTPException(404, 'Nie znaleziono przesyłki')
        orders = con.execute('''SELECT o.id,o.product_id,o.quantity,o.subtotal_grosze,
            o.delivery_grosze,o.total_grosze,o.status
            FROM orders o JOIN shipment_order_links l ON l.order_id=o.id
            WHERE l.shipment_id=? AND o.buyer_id=? AND o.farmer_id=? ORDER BY o.id''',
            (shipment_id,shipment['buyer_id'],shipment['farmer_id'])).fetchall()
        if not orders:
            raise HTTPException(409, 'Przesyłka bez zamówień')
        if user['role'] == 'dostawca':
            if shipment['fulfillment'] != 'dostawa':
                raise HTTPException(404, 'Nie znaleziono przesyłki')
            assigned = con.execute('''SELECT COUNT(*) AS n FROM delivery_assignments d
                JOIN shipment_order_links l ON l.order_id=d.order_id
                WHERE l.shipment_id=? AND d.courier_id=?''', (shipment_id,user['id'])).fetchone()['n']
            if assigned != len(orders):
                raise HTTPException(404, 'Nie znaleziono przesyłki')
        items = [dict(o) for o in orders]
        total = sum(o['total_grosze'] for o in orders)
        refunded = 0
        if user['role'] != 'dostawca':
            from backend.payment_store import get_payment
            for o in orders:
                payment = get_payment(con,o['id'])
                if payment:
                    refunded += payment.refund_grosze
        return {'shipment_id':shipment_id,'fulfillment':shipment['fulfillment'],
                'created_at':shipment['created_at'], 'delivery_grosze':shipment['delivery_grosze'],
                'total_grosze':total,'refund_test_grosze':refunded if user['role'] != 'dostawca' else None,
                'items':items,'payment_mode':'test'}

@app.get('/shipments/{shipment_id}/financial-history-test')
def shipment_financial_history_test(shipment_id: str, user=Depends(current_user)):
    """Private read-only financial history for the buyer."""
    require(user, 'klient')
    from backend.payment_store import get_payment
    with db() as con:
        shipment = con.execute('SELECT buyer_id,delivery_grosze FROM shipment_groups WHERE id=?', (shipment_id,)).fetchone()
        if not shipment or shipment['buyer_id'] != user['id']:
            raise HTTPException(404, 'Nie znaleziono przesyłki')
        orders = con.execute('''SELECT o.id,o.status,o.total_grosze,o.subtotal_grosze,o.delivery_grosze
            FROM orders o JOIN shipment_order_links l ON l.order_id=o.id
            WHERE l.shipment_id=? AND o.buyer_id=? ORDER BY o.id''', (shipment_id,user['id'])).fetchall()
        if not orders:
            raise HTTPException(409, 'Przesyłka bez zamówień')
        entries = []
        for order in orders:
            payment = get_payment(con, order['id'])
            events = con.execute('''SELECT event_type,previous_status,new_status,created_at
                FROM order_events WHERE order_id=? ORDER BY id''', (order['id'],)).fetchall()
            entries.append({'order_id':order['id'], 'status':order['status'],
                'products_grosze':order['subtotal_grosze'], 'delivery_grosze':order['delivery_grosze'],
                'total_grosze':order['total_grosze'],
                'payment_state_test':payment.state if payment else 'not_initialized_test',
                'refund_grosze':payment.refund_grosze if payment else 0,
                'events':[dict(event) for event in events]})
        delivery = sum(entry['delivery_grosze'] for entry in entries)
        return {'shipment_id':shipment_id, 'mode':'test', 'orders':entries,
            'products_grosze':sum(e['products_grosze'] for e in entries),
            'delivery_grosze':delivery, 'total_grosze':sum(e['total_grosze'] for e in entries),
            'refund_grosze':sum(e['refund_grosze'] for e in entries),
            'delivery_consistent':delivery == shipment['delivery_grosze'],
            'notice':'Płatności i zwroty są wyłącznie symulowane.'}

@app.post('/cart/checkout-test', status_code=201)
def checkout_saved_cart(payload: SavedCartCheckoutIn, user=Depends(current_user),
                        authorization: str | None = Header(default=None),
                        idempotency_key: str | None = Header(default=None, alias='Idempotency-Key')):
    require(user, 'klient')
    from backend.order_amount_limits import checked_order_total
    if idempotency_key is not None and not re.fullmatch(r'[A-Za-z0-9_-]{12,100}', idempotency_key):
        raise HTTPException(422, 'Nieprawidłowy klucz Idempotency-Key (12–100 znaków)')
    payload_hash = hashlib.sha256(payload.model_dump_json(exclude_none=False).encode('utf-8')).hexdigest()
    with order_write_db(user, authorization, ('klient',)) as con:
        lock_buyer_operation(con, user['id'])
        authorize_local_transaction(con,user,authorization,('klient',))
        if idempotency_key:
            previous = con.execute('''SELECT payload_hash,response_json FROM checkout_idempotency
                WHERE buyer_id=? AND request_key=?''', (user['id'], idempotency_key)).fetchone()
            if previous:
                if previous['payload_hash'] != payload_hash:
                    raise HTTPException(409, 'Klucz został już użyty z innymi danymi zamówienia')
                return cached_checkout_reply(previous,user['id'],idempotency_key)
        if not has_hold_capacity(con, user['id']):
            raise HTTPException(409, 'Limit 10 nieopłaconych zakupów. Opłać lub anuluj wcześniejsze zamówienia.')
        lines = con.execute('''SELECT c.product_id,c.quantity,p.farmer_id,p.stock,
                           p.price_grosze,p.delivery_grosze
                           FROM saved_cart_items c JOIN products p ON p.id=c.product_id
                           WHERE c.buyer_id=? ORDER BY c.product_id''' +
                           (' FOR UPDATE OF c,p' if DATABASE_URL else ''),
                           (user['id'],)).fetchall()
        if not lines:
            raise HTTPException(409, 'Koszyk jest pusty')
        if payload.farmer_id is not None:
            lines = [r for r in lines if r['farmer_id'] == payload.farmer_id]
            if not lines:
                raise HTTPException(409, 'Brak produktów wybranego rolnika w koszyku')
        # The 50-line limit applies to the shipment being purchased, not to
        # unrelated products from other farmers left in the saved cart.
        if len(lines) > 50:
            raise HTTPException(422, 'Zbyt wiele pozycji w przesyłce')
        farmers = {r['farmer_id'] for r in lines}
        if len(farmers) != 1:
            raise HTTPException(422, 'Na tym etapie zamówienia należy składać osobno u każdego rolnika')
        farmer_id = next(iter(farmers))
        if payload.fulfillment == 'odbior':
            if payload.pickup_point_id is None or any((payload.delivery_city,payload.delivery_street,payload.delivery_postal_code)):
                raise HTTPException(422, 'Wybierz punkt odbioru bez adresu dostawy')
            point = con.execute('SELECT id FROM pickup_points WHERE id=? AND farmer_id=? AND active=1' + (' FOR UPDATE' if DATABASE_URL else ''),
                                (payload.pickup_point_id,farmer_id)).fetchone()
            if not point:
                raise HTTPException(422, 'Punkt odbioru jest niedostępny')
        else:
            if payload.pickup_point_id is not None or not all((payload.delivery_city,payload.delivery_street,payload.delivery_postal_code)):
                raise HTTPException(422, 'Podaj pełny adres dostawy')
        # One delivery charge per seller and checkout, assigned to the first
        # order for compatibility with the existing per-order schema.
        # Use the maximum configured product delivery fee (same as /cart/quote).
        from backend.shipping_policy import shipment_fees
        try:
            shared_delivery = shipment_fees(lines, payload.fulfillment)[farmer_id]
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        totals = []
        grand_total = 0
        for index, r in enumerate(lines):
            if r['quantity'] < 1 or r['quantity'] > 1000 or r['stock'] < r['quantity']:
                raise HTTPException(409, 'Zmieniła się dostępność produktu')
            delivery = shared_delivery if index == 0 else 0
            try:
                subtotal, total = checked_order_total(r['price_grosze'], r['quantity'], delivery)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            if grand_total > 9223372036854775807 - total:
                raise HTTPException(422, 'Przekroczono limit kwoty')
            grand_total += total
            totals.append((r, subtotal, delivery, total))
        shipment_id = 'WPS-' + secrets.token_hex(12).upper()
        con.execute('''INSERT INTO shipment_groups(id,buyer_id,farmer_id,fulfillment,delivery_grosze,created_at)
            VALUES(?,?,?,?,?,?)''', (shipment_id,user['id'],farmer_id,payload.fulfillment,
            shared_delivery,datetime.now(timezone.utc).isoformat()))
        created = []
        reservation_started = datetime.now(timezone.utc)
        shipment_pin = f'{secrets.randbelow(1_000_000):06d}'
        shipment_pin_hash = ph.hash(shipment_pin)
        for r,subtotal,delivery,total in totals:
            code = 'WP-' + secrets.token_hex(5).upper()
            cur = con.execute('''INSERT INTO orders(buyer_id,farmer_id,product_id,quantity,
                subtotal_grosze,delivery_grosze,total_grosze,fulfillment,status,pickup_code,pin_hash,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                (user['id'],farmer_id,r['product_id'],r['quantity'],subtotal,delivery,total,
                 payload.fulfillment,'oczekuje_na_platnosc_testowa',code,shipment_pin_hash,
                 datetime.now(timezone.utc).isoformat()))
            order_id = cur.lastrowid
            reservation_expires_at = add_hold(con, order_id, now=reservation_started)
            con.execute('INSERT INTO shipment_order_links(order_id,shipment_id) VALUES(?,?)', (order_id,shipment_id))
            con.execute('''INSERT INTO order_locations(order_id,pickup_point_id,delivery_city,
                delivery_street,delivery_postal_code) VALUES(?,?,?,?,?)''',
                (order_id,payload.pickup_point_id if payload.fulfillment == 'odbior' else None,
                 payload.delivery_city.strip() if payload.fulfillment == 'dostawa' else None,
                 payload.delivery_street.strip() if payload.fulfillment == 'dostawa' else None,
                 payload.delivery_postal_code if payload.fulfillment == 'dostawa' else None))
            updated = con.execute('UPDATE products SET stock=stock-? WHERE id=? AND stock>=?',
                                  (r['quantity'],r['product_id'],r['quantity']))
            if updated.rowcount != 1:
                raise HTTPException(409, 'Stan magazynowy zmienił się; spróbuj ponownie')
            from backend.purchase_records import capture_purchase
            capture_purchase(con,order_id)
            record_order_event(con,order_id,user['id'],'order_created',None,'oczekuje_na_platnosc_testowa')
            created.append({'id':order_id,'pickup_code':code,
                            'total_grosze':total})
        if payload.farmer_id is None:
            con.execute('DELETE FROM saved_cart_items WHERE buyer_id=?',(user['id'],))
        else:
            for r in lines:
                con.execute('DELETE FROM saved_cart_items WHERE buyer_id=? AND product_id=?', (user['id'],r['product_id']))
        response = {'orders':created,'shipment_id':shipment_id,'shipment_pin_test_only':shipment_pin,
                    'total_grosze':grand_total,'payment_mode':'test',
                    'delivery_grosze':shared_delivery,
                    'reservation_expires_at':reservation_expires_at,
                    'notice':'Brak pobrania płatności. Jedna opłata za dostawę dla wybranego rolnika.'}
        idempotency_key = idempotency_key or ('internal_' + secrets.token_hex(16))
        if idempotency_key:
            con.execute('''INSERT INTO checkout_idempotency
                (buyer_id,request_key,payload_hash,response_json,created_at) VALUES(?,?,?,?,?)''',
                (user['id'],idempotency_key,payload_hash,seal_checkout_reply(response,user['id'],idempotency_key,payload_hash),
                 datetime.now(timezone.utc).isoformat()))
            link_reply(con,user['id'],idempotency_key,response)
    return response

@app.get('/orders/idempotency-status/{request_key}')
def direct_order_idempotency_status(request_key: str, user=Depends(current_user),
                                    authorization: str | None = Header(default=None)):
    """Read-only reconciliation after a lost response; never expose stored PIN."""
    require(user, 'klient')
    if not re.fullmatch(r'[A-Za-z0-9_-]{12,100}', request_key):
        raise HTTPException(422, 'Nieprawidłowy identyfikator operacji')
    with purchase_record_read_db(user, authorization, ('klient',)) as con:
        row = con.execute("""SELECT payload_hash,response_json FROM checkout_idempotency
            WHERE buyer_id=? AND request_key=?""",
            (user['id'], 'direct:' + request_key)).fetchone()
    if not row:
        return {'completed': False}
    result = cached_checkout_reply(row,user['id'],'direct:' + request_key,expose_pin=False)
    return {'completed': True, 'order_id': result['id']}

@app.post('/orders',status_code=201)
def create_order(payload: OrderIn, user=Depends(current_user), authorization: str | None = Header(default=None),
                 idempotency_key: str | None = Header(default=None, alias='Idempotency-Key')):
    require(user,'klient')
    if idempotency_key is not None and not re.fullmatch(r'[A-Za-z0-9_-]{12,100}', idempotency_key):
        raise HTTPException(422, 'Nieprawidłowy klucz Idempotency-Key (12–100 znaków)')
    # Namespace avoids collisions with keys used for multi-product checkout.
    request_key = 'direct:' + idempotency_key if idempotency_key else None
    payload_hash = hashlib.sha256(payload.model_dump_json(exclude_none=False).encode('utf-8')).hexdigest()
    with order_write_db(user, authorization, ('klient',)) as con:
        lock_buyer_operation(con, user['id'])
        authorize_local_transaction(con,user,authorization,('klient',))
        if request_key:
            previous = con.execute('''SELECT payload_hash,response_json FROM checkout_idempotency
                WHERE buyer_id=? AND request_key=?''', (user['id'], request_key)).fetchone()
            if previous:
                if previous['payload_hash'] != payload_hash:
                    raise HTTPException(409, 'Klucz został już użyty z innymi danymi zamówienia')
                return cached_checkout_reply(previous,user['id'],request_key)
        if not has_hold_capacity(con, user['id']):
            raise HTTPException(409, 'Limit 10 nieopłaconych zakupów. Opłać lub anuluj wcześniejsze zamówienia.')
        p=con.execute('SELECT * FROM products WHERE id=?' + (' FOR UPDATE' if DATABASE_URL else ''),(payload.product_id,)).fetchone()
        if not p or p['stock']<payload.quantity:
            raise HTTPException(409,'Produkt niedostępny lub niewystarczający stan')
        if payload.fulfillment == 'odbior':
            if payload.pickup_point_id is None or any([payload.delivery_city, payload.delivery_street, payload.delivery_postal_code]):
                raise HTTPException(422,'Wybierz punkt odbioru, bez adresu dostawy')
            point = con.execute('SELECT id FROM pickup_points WHERE id=? AND farmer_id=? AND active=1' + (' FOR UPDATE' if DATABASE_URL else ''),
                                (payload.pickup_point_id,p['farmer_id'])).fetchone()
            if not point:
                raise HTTPException(422,'Punkt odbioru nie należy do sprzedawcy lub jest nieaktywny')
        else:
            if payload.pickup_point_id is not None or not all([payload.delivery_city, payload.delivery_street, payload.delivery_postal_code]):
                raise HTTPException(422,'Dostawa wymaga pełnego adresu, bez punktu odbioru')
        from backend.order_amount_limits import checked_order_total
        delivery = p['delivery_grosze'] if payload.fulfillment=='dostawa' else 0
        if payload.fulfillment == 'dostawa' and delivery <= 0:
            raise HTTPException(422, 'Sprzedawca musi ustalić dodatnią opłatę za dostawę na adres')
        try:
            subtotal, total = checked_order_total(p['price_grosze'], payload.quantity, delivery)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        code='WP-'+secrets.token_hex(5).upper()
        pin=f'{secrets.randbelow(1_000_000):06d}'
        cur=con.execute('INSERT INTO orders(buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,total_grosze,fulfillment,status,pickup_code,pin_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', (user['id'],p['farmer_id'],p['id'],payload.quantity,subtotal,delivery,total,payload.fulfillment,'oczekuje_na_platnosc_testowa',code,ph.hash(pin),datetime.now(timezone.utc).isoformat()))
        con.execute('INSERT INTO order_locations(order_id,pickup_point_id,delivery_city,delivery_street,delivery_postal_code) VALUES(?,?,?,?,?)',
                    (cur.lastrowid, payload.pickup_point_id if payload.fulfillment=='odbior' else None,
                     payload.delivery_city.strip() if payload.fulfillment=='dostawa' else None,
                     payload.delivery_street.strip() if payload.fulfillment=='dostawa' else None,
                     payload.delivery_postal_code if payload.fulfillment=='dostawa' else None))
        updated=con.execute('UPDATE products SET stock=stock-? WHERE id=? AND stock>=?',(payload.quantity,p['id'],payload.quantity))
        if updated.rowcount != 1:
            raise HTTPException(409,'Stan magazynowy zmienił się; ponów zamówienie')
        reservation_expires_at = add_hold(con, cur.lastrowid, now=datetime.now(timezone.utc))
        from backend.purchase_records import capture_purchase
        capture_purchase(con,cur.lastrowid)
        record_order_event(con,cur.lastrowid,user['id'],'order_created',None,'oczekuje_na_platnosc_testowa')
        # PIN is returned to buyer only at creation in test mode; in production use separate secure delivery flow.
        response = {'id':cur.lastrowid,'pickup_code':code,'pin_test_only':pin,'total_grosze':total,'reservation_expires_at':reservation_expires_at,'status':'oczekuje_na_platnosc_testowa'}
        request_key = request_key or ('internal_direct_' + secrets.token_hex(16))
        if request_key:
            con.execute('''INSERT INTO checkout_idempotency
                (buyer_id,request_key,payload_hash,response_json,created_at) VALUES(?,?,?,?,?)''',
                (user['id'],request_key,payload_hash,seal_checkout_reply(response,user['id'],request_key,payload_hash),datetime.now(timezone.utc).isoformat()))
            link_reply(con,user['id'],request_key,response)
        return response

@app.get('/orders/me')
def my_orders(user=Depends(current_user), authorization: str | None = Header(default=None)):
    # PostgreSQL: re-verify the bearer token inside the SAME transaction as
    # the protected query; never trust a request-provided actor identifier.
    if DATABASE_URL:
        from backend.pg_adapter import postgres_verified_db
        from backend.neon_order_access import buyer_orders, farmer_orders
        from backend.neon_session_bridge import AuthenticationFailed
        try:
            with postgres_verified_db(DATABASE_URL, authorization) as (con, actor_id):
                from backend.neon_auth_policy import actor_role
                role = actor_role(con, actor_id, ('klient', 'rolnik'))
                if not role:
                    raise HTTPException(403, 'Brak uprawnień')
                rows = (buyer_orders(con, actor_id) if role == 'klient'
                        else farmer_orders(con, actor_id))
                return [dict(row) for row in rows]
        except AuthenticationFailed:
            raise HTTPException(401, 'Sesja nieważna')
    with db() as con:
        if user['role']=='klient':
            rows=con.execute('SELECT id,pickup_code,total_grosze,fulfillment,status,created_at,(SELECT expires_at FROM inventory_reservations WHERE order_id=orders.id) AS reservation_expires_at FROM orders WHERE buyer_id=? ORDER BY id DESC',(user['id'],))
        elif user['role']=='rolnik':
            rows=con.execute('SELECT id,pickup_code,total_grosze,fulfillment,status,created_at,(SELECT expires_at FROM inventory_reservations WHERE order_id=orders.id) AS reservation_expires_at FROM orders WHERE farmer_id=? ORDER BY id DESC',(user['id'],))
        else:
            raise HTTPException(403,'Brak uprawnień')
        return [dict(r) for r in rows]

def require_shipment_membership(shipment, orders):
    """Call on locked rows before granting authority through shipment links."""
    if any(order[key] != shipment[key]
           for order in orders for key in ('buyer_id', 'farmer_id', 'fulfillment')):
        raise HTTPException(409, 'Niespójne zamówienia przesyłki; wymagana weryfikacja')


@app.post('/shipments/{shipment_id}/confirm')
def confirm_shipment(shipment_id: str, payload: ConfirmIn, user=Depends(current_user), authorization: str | None = Header(default=None)):
    # Confirm all shipment orders atomically using one PIN.
    if user['role'] not in ('rolnik', 'dostawca'):
        raise HTTPException(403, 'Brak uprawnień')
    if not payload.checked_goods:
        raise HTTPException(422, 'Klient musi najpierw sprawdzić towar')
    with order_write_db(user, authorization, ('rolnik', 'dostawca')) as con:
        shipment = con.execute('SELECT * FROM shipment_groups WHERE id=?' + (' FOR UPDATE' if DATABASE_URL else ''), (shipment_id,)).fetchone()
        if not shipment:
            raise HTTPException(404, 'Brak przesyłki')
        if user['role'] == 'rolnik' and (shipment['farmer_id'] != user['id'] or shipment['fulfillment'] != 'odbior'):
            raise HTTPException(403, 'Brak uprawnień do przesyłki')
        orders = con.execute('SELECT o.* FROM orders o JOIN shipment_order_links l ON l.order_id=o.id WHERE l.shipment_id=? ORDER BY o.id' + (' FOR UPDATE OF o' if DATABASE_URL else ''), (shipment_id,)).fetchall()
        require_shipment_membership(shipment, orders)
        if not orders:
            raise HTTPException(409, 'Przesyłka nie ma zamówień')
        if user['role'] == 'dostawca':
            if shipment['fulfillment'] != 'dostawa':
                raise HTTPException(403, 'Brak uprawnień do odbioru')
            for o in orders:
                assignment = con.execute('SELECT courier_id FROM delivery_assignments WHERE order_id=?', (o['id'],)).fetchone()
                if not assignment or assignment['courier_id'] != user['id']:
                    raise HTTPException(403, 'Dostawca nie jest przypisany do całej przesyłki')
        expected = 'gotowe_do_odbioru_testowo' if shipment['fulfillment'] == 'odbior' else 'w_drodze_testowo'
        if any(o['status'] != expected or o['pin_used'] or o['pin_attempts'] >= 5 for o in orders):
            raise HTTPException(409, 'Przesyłka nie jest gotowa lub PIN został zablokowany')
        try:
            # Every linked order must authorize the same PIN, including after
            # persisted corruption or an interrupted external repair.
            correct = all(ph.verify(o['pin_hash'], payload.pin) for o in orders)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            correct = False
        if not correct:
            for o in orders:
                con.execute('UPDATE orders SET pin_attempts=pin_attempts+1 WHERE id=?', (o['id'],))
            return {'confirmed': False, 'remaining_attempts': 4 - max(o['pin_attempts'] for o in orders)}
        now = datetime.now(timezone.utc).isoformat()
        for o in orders:
            require_transition(o['fulfillment'], o['status'], 'odebrane')
            con.execute('UPDATE orders SET pin_used=1,status=?,confirmed_at=? WHERE id=?', ('odebrane', now, o['id']))
            record_order_event(con, o['id'], user['id'], 'pin_confirmed', o['status'], 'odebrane')
        return {'confirmed': True, 'shipment_id': shipment_id, 'confirmed_orders': len(orders)}

@app.post('/orders/{order_id}/confirm')
def confirm_order(order_id:int,payload:ConfirmIn,user=Depends(current_user), authorization: str | None = Header(default=None)):
    if user['role'] not in ('rolnik','dostawca'):
        raise HTTPException(403,'Brak uprawnień')
    if not payload.checked_goods:
        raise HTTPException(422,'Klient musi najpierw sprawdzić towar')
    with order_write_db(user, authorization, ('rolnik', 'dostawca')) as con:
        o=con.execute('SELECT * FROM orders WHERE id=?' + (' FOR UPDATE' if DATABASE_URL else ''),(order_id,)).fetchone()
        if not o:
            raise HTTPException(404,'Brak zamówienia')
        linked = con.execute('SELECT shipment_id FROM shipment_order_links WHERE order_id=?', (order_id,)).fetchone()
        if linked:
            raise HTTPException(409, 'Potwierdź całą przesyłkę jednym PIN-em')
        if user['role']=='rolnik' and (o['farmer_id']!=user['id'] or o['fulfillment']!='odbior'):
            raise HTTPException(403,'To nie Twoje zamówienie')
        # Delivery personnel assignment and payment confirmation are not yet implemented.
        if user['role']=='dostawca':
            assignment=con.execute('SELECT courier_id FROM delivery_assignments WHERE order_id=?',(order_id,)).fetchone()
            if o['fulfillment']!='dostawa' or not assignment or assignment['courier_id']!=user['id']:
                raise HTTPException(403,'Nie jesteś przypisanym dostawcą')
        if o['pin_used'] or o['pin_attempts']>=5:
            raise HTTPException(409,'PIN wykorzystany lub zablokowany')
        expected_status = ('gotowe_do_odbioru_testowo' if o['fulfillment'] == 'odbior'
                           else 'w_drodze_testowo')
        if o['status'] != expected_status:
            raise HTTPException(409,'Zamówienie nie jest gotowe do odbioru')
        try:
            correct=ph.verify(o['pin_hash'],payload.pin)
        except (VerifyMismatchError,VerificationError,InvalidHashError):
            correct=False
        if not correct:
            con.execute('UPDATE orders SET pin_attempts=pin_attempts+1 WHERE id=?',(order_id,))
            return {'confirmed':False,'remaining_attempts':4-o['pin_attempts']}
        require_transition(o['fulfillment'], o['status'], 'odebrane')
        con.execute('UPDATE orders SET pin_used=1,status=?,confirmed_at=? WHERE id=?',('odebrane',datetime.now(timezone.utc).isoformat(),order_id))
        record_order_event(con,order_id,user['id'],'pin_confirmed',o['status'],'odebrane')
        return {'confirmed':True}

def require_unexpired_unpaid_reservation(con, order_id):
    if payment_deadline_passed(con, order_id, now=datetime.now(timezone.utc)):
        payment = get_payment(con, order_id)
        if payment is None or payment.state in ('awaiting_payment', 'failed_test'):
            raise HTTPException(409, 'Upłynął termin nieopłaconej rezerwacji')


@app.post('/test/orders/{order_id}/ready')
def mark_ready_test(order_id:int,user=Depends(current_user), authorization: str | None = Header(default=None)):
    require(user,'rolnik')
    with order_write_db(user, authorization, ('rolnik',)) as con:
        o=con.execute('SELECT farmer_id,status,fulfillment FROM orders WHERE id=?' + (' FOR UPDATE' if DATABASE_URL else ''),(order_id,)).fetchone()
        if not o or o['farmer_id']!=user['id']:
            raise HTTPException(404,'Brak zamówienia')
        if o['status']!='oczekuje_na_platnosc_testowa':
            raise HTTPException(409,'Niewłaściwy status')
        if o['fulfillment'] != 'odbior':
            raise HTTPException(409,'Dostawa wymaga osobnego procesu i przypisania dostawcy')
        require_unexpired_unpaid_reservation(con, order_id)
        require_transition(o['fulfillment'], o['status'], 'gotowe_do_odbioru_testowo')
        con.execute('UPDATE orders SET status=? WHERE id=?',('gotowe_do_odbioru_testowo',order_id))
        record_order_event(con,order_id,user['id'],'pickup_ready',o['status'],'gotowe_do_odbioru_testowo')
    return {'status':'gotowe_do_odbioru_testowo','warning':'Tylko test: bez rzeczywistej płatności'}


# Same-origin developer UI: no public deployment without hardening.
WEB_DIR = Path(__file__).resolve().parent.parent / 'web'
app.mount('/assets', StaticFiles(directory=str(WEB_DIR)), name='assets')

@app.get('/', include_in_schema=False)
def index():
    return FileResponse(WEB_DIR / 'index.html')

@app.get('/auth/me')
def auth_me(user=Depends(current_user)):
    return user

class ProductUpdateIn(BaseModel):
    model_config = {'extra': 'forbid'}
    name: CleanText | None = Field(default=None, min_length=2, max_length=120)
    price_grosze: int | None = Field(strict=True, default=None, ge=1, le=100_000_000)
    delivery_grosze: int | None = Field(strict=True, default=None, ge=0, le=10_000_000)
    stock: int | None = Field(strict=True, default=None, ge=0, le=1_000_000)

@app.patch('/products/mine/{product_id}')
def update_my_product(product_id: int, payload: ProductUpdateIn,
                      user=Depends(current_user), authorization: str | None = Header(default=None)):
    """Only the owner can edit a listing; stock is an absolute quantity, not a delta."""
    require(user, 'rolnik')
    fields = payload.model_dump(exclude_unset=True)
    if not fields or any(value is None for value in fields.values()):
        raise HTTPException(422, 'Podaj poprawne pola produktu')
    with order_write_db(user, authorization, ('rolnik',)) as con:
        assignments = ', '.join(f'{field}=?' for field in fields)
        cur = con.execute(f'UPDATE products SET {assignments} WHERE id=? AND farmer_id=?',
                          (*fields.values(), product_id, user['id']))
        if cur.rowcount != 1:
            raise HTTPException(404, 'Nie znaleziono produktu')
        row = con.execute('SELECT id,name,price_grosze,delivery_grosze,stock FROM products WHERE id=? AND farmer_id=?',
                          (product_id, user['id'])).fetchone()
        from backend.local_marketplace import index_product
        index_product(con, product_id, row['name'])
        return dict(row)

@app.post('/shipments/{shipment_id}/cancel-test')
def cancel_shipment_test(shipment_id: str, user=Depends(current_user), authorization: str | None = Header(default=None)):
    require(user, 'klient')
    with order_write_db(user, authorization, ('klient',)) as con:
        shipment = con.execute('SELECT * FROM shipment_groups WHERE id=?' + (' FOR UPDATE' if DATABASE_URL else ''), (shipment_id,)).fetchone()
        if not shipment or shipment['buyer_id'] != user['id']:
            raise HTTPException(404, 'Nie znaleziono przesyłki')
        orders = con.execute('SELECT o.* FROM orders o JOIN shipment_order_links l ON l.order_id=o.id WHERE l.shipment_id=? ORDER BY o.id' + (' FOR UPDATE OF o' if DATABASE_URL else ''), (shipment_id,)).fetchall()
        require_shipment_membership(shipment, orders)
        if not orders or any(o['status'] != 'oczekuje_na_platnosc_testowa' for o in orders):
            raise HTTPException(409, 'Nie można anulować przesyłki na tym etapie')
        # Nie przywracaj towaru i nie anuluj przesyłki z opłaconą symulacją.
        # Taki przypadek wymaga osobnego, atomowego procesu zwrotu.
        if any((payment := get_payment(con, o['id'])) is not None
               and payment.state not in ('awaiting_payment', 'failed_test') for o in orders):
            raise HTTPException(409, 'Przesyłka ma zarejestrowaną płatność; wymagany proces zwrotu')
        for o in orders:
            require_transition(o['fulfillment'], o['status'], 'anulowane_testowo')
            changed = con.execute('UPDATE orders SET status=? WHERE id=? AND status=?', ('anulowane_testowo', o['id'], 'oczekuje_na_platnosc_testowa'))
            if changed.rowcount != 1:
                raise HTTPException(409, 'Status przesyłki zmienił się')
            con.execute('UPDATE products SET stock=stock+? WHERE id=?', (o['quantity'], o['product_id']))
            record_order_event(con, o['id'], user['id'], 'shipment_cancel_test', o['status'], 'anulowane_testowo')
        return {'shipment_id': shipment_id, 'status': 'anulowane_testowo', 'cancelled_orders': len(orders), 'refund_grosze': 0, 'warning': 'Brak rzeczywistej płatności i zwrotu'}

def checked_refund_payment(con, order):
    from backend.payment_store import validate_order_payment, validate_payment_history, validate_order_refund
    payment = get_payment(con, order['id'])
    if payment is not None:
        try:
            validate_order_payment(payment, order)
            validate_payment_history(con, payment)
            validate_order_refund(con, payment, order)
        except ValueError as exc:
            raise HTTPException(409, 'Niespójne rozliczenie; wymagana weryfikacja') from exc
    return payment


@app.post('/shipments/{shipment_id}/cancel-paid-test')
def cancel_paid_shipment_test(shipment_id: str, user=Depends(current_user), authorization: str | None = Header(default=None)):
    """Atomically refund simulated paid items and cancel the whole pending shipment."""
    require(user, 'klient')
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja płatności wyłączona')
    with order_write_db(user, authorization, ('klient',)) as con:
        shipment = con.execute('SELECT * FROM shipment_groups WHERE id=?' + (' FOR UPDATE' if DATABASE_URL else ''), (shipment_id,)).fetchone()
        if not shipment or shipment['buyer_id'] != user['id']:
            raise HTTPException(404, 'Nie znaleziono przesyłki')
        orders = con.execute('SELECT o.* FROM orders o JOIN shipment_order_links l ON l.order_id=o.id WHERE l.shipment_id=? ORDER BY o.id' + (' FOR UPDATE OF o' if DATABASE_URL else ''), (shipment_id,)).fetchall()
        require_shipment_membership(shipment, orders)
        if not orders:
            raise HTTPException(409, 'Pusta przesyłka')
        if all(o['status'] == 'anulowane_testowo' for o in orders):
            payments = [checked_refund_payment(con, o) for o in orders]
            if (any(p is not None and p.state not in ('refunded_test', 'awaiting_payment', 'failed_test') for p in payments)
                    or not any(p is not None and p.state == 'refunded_test' for p in payments)):
                raise HTTPException(409, 'Brak potwierdzonego zwrotu testowego przesyłki')
            return {'shipment_id':shipment_id, 'status':'anulowane_testowo',
                    'refund_grosze':sum(p.refund_grosze for p in payments if p),
                    'already_processed':True, 'mode':'test'}
        if any(o['status'] != 'oczekuje_na_platnosc_testowa' for o in orders):
            raise HTTPException(409, 'Anulowanie możliwe tylko przed realizacją przesyłki')
        payments = [checked_refund_payment(con, o) for o in orders]
        if any(p is not None and p.state not in ('paid_test', 'awaiting_payment', 'failed_test') for p in payments):
            raise HTTPException(409, 'Niedozwolony stan płatności; wymagana ręczna weryfikacja')
        if not any(p is not None and p.state == 'paid_test' for p in payments):
            raise HTTPException(409, 'Brak opłaconych pozycji; użyj zwykłego anulowania')
        refunded = 0
        for o, payment in zip(orders, payments):
            require_transition(o['fulfillment'], o['status'], 'anulowane_testowo')
            if payment is not None and payment.state == 'paid_test':
                event_id = f'cancel-paid-shipment:{shipment_id}:{o["id"]}'
                try:
                    updated = persist_event(con, payment, event_id, 'customer_cancel_refund_test', datetime.now(timezone.utc).isoformat())
                except ValueError as exc:
                    raise HTTPException(409, str(exc)) from exc
                refunded += updated.refund_grosze
            changed = con.execute('UPDATE orders SET status=? WHERE id=? AND status=?',
                                  ('anulowane_testowo', o['id'], 'oczekuje_na_platnosc_testowa'))
            if changed.rowcount != 1:
                raise HTTPException(409, 'Status zamówienia zmienił się')
            con.execute('UPDATE products SET stock=stock+? WHERE id=?', (o['quantity'], o['product_id']))
            record_order_event(con, o['id'], user['id'], 'shipment_paid_cancel_test', o['status'], 'anulowane_testowo')
        return {'shipment_id':shipment_id, 'status':'anulowane_testowo',
                'refund_grosze':refunded, 'already_processed':False, 'mode':'test',
                'notice':'Zwrot wyłącznie symulowany; nie przekazano pieniędzy.'}

@app.post('/orders/{order_id}/cancel-paid-test')
def cancel_paid_order_test(order_id: int, user=Depends(current_user), authorization: str | None = Header(default=None)):
    """Full simulated refund of a standalone pending order, once only."""
    require(user, 'klient')
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja płatności wyłączona')
    with order_write_db(user, authorization, ('klient',)) as con:
        order = con.execute('SELECT * FROM orders WHERE id=? AND buyer_id=?' + (' FOR UPDATE' if DATABASE_URL else ''),
                            (order_id, user['id'])).fetchone()
        if not order:
            raise HTTPException(404, 'Nie znaleziono zamówienia')
        if con.execute('SELECT 1 FROM shipment_order_links WHERE order_id=?', (order_id,)).fetchone():
            raise HTTPException(409, 'Anuluj całą przesyłkę, nie pojedynczy produkt')
        payment = checked_refund_payment(con, order)
        if order['status'] == 'anulowane_testowo':
            if payment is None or payment.state != 'refunded_test' or payment.refund_grosze != order['total_grosze']:
                raise HTTPException(409, 'Brak potwierdzonego pełnego zwrotu testowego')
            return {'order_id': order_id, 'status': 'anulowane_testowo', 'refund_grosze': payment.refund_grosze,
                    'already_processed': True, 'mode': 'test'}
        if order['status'] != 'oczekuje_na_platnosc_testowa':
            raise HTTPException(409, 'Anulowanie testowe możliwe tylko przed realizacją zamówienia')
        if payment is None or payment.state != 'paid_test':
            raise HTTPException(409, 'Brak opłaconego zamówienia; użyj zwykłego anulowania')
        try:
            updated = persist_event(con, payment, f'cancel-paid-order:{order_id}', 'customer_cancel_refund_test',
                                    datetime.now(timezone.utc).isoformat())
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        require_transition(order['fulfillment'], order['status'], 'anulowane_testowo')
        con.execute('UPDATE orders SET status=? WHERE id=?', ('anulowane_testowo', order_id))
        con.execute('UPDATE products SET stock=stock+? WHERE id=?', (order['quantity'], order['product_id']))
        record_order_event(con, order_id, user['id'], 'order_paid_cancel_test', order['status'], 'anulowane_testowo')
        return {'order_id': order_id, 'status': 'anulowane_testowo', 'refund_grosze': updated.refund_grosze,
                'already_processed': False, 'mode': 'test',
                'notice': 'Zwrot wyłącznie symulowany; nie przekazano pieniędzy.'}


@app.post('/orders/{order_id}/cancel-test')
def cancel_order_test(order_id: int, user=Depends(current_user), authorization: str | None = Header(default=None)):
    require(user, 'klient')
    with order_write_db(user, authorization, ('klient',)) as con:
        o = con.execute('SELECT * FROM orders WHERE id=? AND buyer_id=?' + (' FOR UPDATE' if DATABASE_URL else ''), (order_id,user['id'])).fetchone()
        if not o:
            raise HTTPException(404, 'Nie znaleziono zamówienia')
        if con.execute('SELECT 1 FROM shipment_order_links WHERE order_id=?', (order_id,)).fetchone():
            raise HTTPException(409, 'Anuluj całą przesyłkę, nie pojedynczy produkt')
        if o['status'] != 'oczekuje_na_platnosc_testowa':
            raise HTTPException(409, 'Nie można anulować zamówienia na tym etapie')
        payment = get_payment(con, order_id)
        if payment is not None and payment.state not in ('awaiting_payment', 'failed_test'):
            raise HTTPException(409, 'Zamówienie ma zarejestrowaną płatność; wymagany proces zwrotu')
        # Compare-and-set: restoring inventory is allowed only for the single
        # transaction that successfully moves this order out of the pending state.
        # This remains safe if another writer changes the status between read/write.
        require_transition(o['fulfillment'], o['status'], 'anulowane_testowo')
        changed = con.execute(
            'UPDATE orders SET status=? WHERE id=? AND buyer_id=? AND status=?',
            ('anulowane_testowo', order_id, user['id'], 'oczekuje_na_platnosc_testowa'),
        )
        if changed.rowcount != 1:
            raise HTTPException(409, 'Status zamówienia zmienił się; ponów operację')
        con.execute('UPDATE products SET stock=stock+? WHERE id=?', (o['quantity'],o['product_id']))
        record_order_event(con,order_id,user['id'],'cancel_test',o['status'],'anulowane_testowo')
        return {'status':'anulowane_testowo', 'stock_restored':True, 'refund_grosze':0,
                'warning':'Brak rzeczywistej płatności i zwrotu'}


class FarmerProfileIn(BaseModel):
    farm_name: CleanText = Field(min_length=2, max_length=120)
    city: CleanText = Field(min_length=2, max_length=120)
    description: CleanText = Field(default='', max_length=1500)

class PickupPointIn(BaseModel):
    name: CleanText = Field(min_length=2, max_length=120)
    city: CleanText = Field(min_length=2, max_length=120)
    street: CleanText = Field(min_length=3, max_length=180)
    opening_hours: CleanText = Field(min_length=3, max_length=180)
    latitude_e6: int | None = Field(default=None, strict=True, ge=-90_000_000, le=90_000_000)
    longitude_e6: int | None = Field(default=None, strict=True, ge=-180_000_000, le=180_000_000)

    @model_validator(mode='after')
    def paired_coordinates(self):
        if (self.latitude_e6 is None) != (self.longitude_e6 is None):
            raise ValueError('Podaj obie współrzędne albo pomiń lokalizację')
        return self


class PickupPointUpdateIn(PickupPointIn):
    active: bool = Field(strict=True)
    clear_coordinates: bool = Field(default=False, strict=True)

    @model_validator(mode='after')
    def unambiguous_coordinates(self):
        if self.clear_coordinates and self.latitude_e6 is not None:
            raise ValueError('Nie można jednocześnie ustawić i usunąć lokalizacji')
        return self


@app.put('/farmers/me/profile')
def update_farmer_profile(payload:FarmerProfileIn,user=Depends(current_user), authorization: str | None = Header(default=None)):
    require(user,'rolnik')
    with order_write_db(user, authorization, ('rolnik',)) as con:
        con.execute('''INSERT INTO farmer_profiles(user_id,farm_name,city,description) VALUES(?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET farm_name=excluded.farm_name,city=excluded.city,description=excluded.description''',
            (user['id'],payload.farm_name.strip(),payload.city.strip(),payload.description.strip()))
    return {'saved':True}

@app.get('/farmers/me/profile')
def get_farmer_profile(user=Depends(current_user)):
    require(user,'rolnik')
    with db() as con:
        row=con.execute('SELECT farm_name,city,description FROM farmer_profiles WHERE user_id=?',(user['id'],)).fetchone()
    if not row: raise HTTPException(404,'Uzupełnij profil gospodarstwa')
    return dict(row)

@app.post('/pickup-points',status_code=201)
def create_pickup_point(payload:PickupPointIn,user=Depends(current_user), authorization: str | None = Header(default=None)):
    require(user,'rolnik')
    with order_write_db(user, authorization, ('rolnik',)) as con:
        cur=con.execute('INSERT INTO pickup_points(farmer_id,name,city,street,opening_hours) VALUES(?,?,?,?,?)',
                        (user['id'],payload.name,payload.city,payload.street,payload.opening_hours))
        if payload.latitude_e6 is not None:
            from backend.local_marketplace import save_coordinates
            save_coordinates(con,cur.lastrowid,payload.latitude_e6,payload.longitude_e6)
        return {'id':cur.lastrowid}


@app.put('/pickup-points/{point_id}')
def update_pickup_point(point_id: int, payload: PickupPointUpdateIn, user=Depends(current_user),
                        authorization: str | None = Header(default=None)):
    require(user,'rolnik')
    with order_write_db(user, authorization, ('rolnik',)) as con:
        point = con.execute('SELECT * FROM pickup_points WHERE id=? AND farmer_id=?' +
            (' FOR UPDATE' if DATABASE_URL else ''), (point_id,user['id'])).fetchone()
        if not point:
            raise HTTPException(404,'Nie znaleziono punktu')
        coords = con.execute('SELECT latitude_e6,longitude_e6 FROM pickup_point_coordinates WHERE point_id=?', (point_id,)).fetchone()
        metadata_changed = any(point[k]!=getattr(payload,k) for k in ('name','city','street','opening_hours'))
        coords_changed = (payload.clear_coordinates and coords is not None) or (payload.latitude_e6 is not None and
            (coords is None or coords['latitude_e6']!=payload.latitude_e6 or coords['longitude_e6']!=payload.longitude_e6))
        if metadata_changed or coords_changed:
            open_order = con.execute("""SELECT 1 FROM order_locations l JOIN orders o ON o.id=l.order_id
                WHERE l.pickup_point_id=? AND o.status IN ('oczekuje_na_platnosc_testowa','gotowe_do_odbioru_testowo') LIMIT 1""", (point_id,)).fetchone()
            if open_order:
                raise HTTPException(409,'Punkt ma niezakończone zamówienia. Możesz wyłączyć nowe zakupy, ale nie zmieniać miejsca ani godzin odbioru.')
        con.execute('UPDATE pickup_points SET name=?,city=?,street=?,opening_hours=?,active=? WHERE id=? AND farmer_id=?',
            (payload.name,payload.city,payload.street,payload.opening_hours,int(payload.active),point_id,user['id']))
        if payload.clear_coordinates:
            con.execute('DELETE FROM pickup_point_coordinates WHERE point_id=?',(point_id,))
        elif payload.latitude_e6 is not None:
            from backend.local_marketplace import save_coordinates
            save_coordinates(con,point_id,payload.latitude_e6,payload.longitude_e6)
    return {'id':point_id,'saved':True,'active':payload.active}


@app.get('/farmers/me/pickup-points')
def my_pickup_points(user=Depends(current_user)):
    require(user, 'rolnik')
    with db() as con:
        return [dict(r) for r in con.execute('SELECT t.id,t.name,t.city,t.street,t.opening_hours,t.active,c.latitude_e6,c.longitude_e6 FROM pickup_points t LEFT JOIN pickup_point_coordinates c ON c.point_id=t.id WHERE t.farmer_id=? ORDER BY t.id DESC',(user['id'],))]

@app.get('/farmers/{farmer_id}/pickup-points')
def list_pickup_points(farmer_id:int):
    with db() as con:
        return [dict(r) for r in con.execute('SELECT id,name,city,street,opening_hours FROM pickup_points WHERE farmer_id=? AND active=1 ORDER BY id',(farmer_id,))]

@app.get('/orders/{order_id}/location')
def order_location(order_id:int,user=Depends(current_user), authorization: str | None = Header(default=None)):
    # Fetch address and assignment in a single query; never disclose to an
    # unassigned courier or after confirmation, even if assignment persists.
    with order_write_db(user, authorization, ('klient', 'rolnik', 'dostawca')) as con:
        row=con.execute('''SELECT o.buyer_id,o.farmer_id,o.fulfillment,o.status,
            o.pin_used,o.confirmed_at,l.pickup_point_id,l.delivery_city,
            l.delivery_street,l.delivery_postal_code,a.courier_id
            FROM orders o JOIN order_locations l ON l.order_id=o.id
            LEFT JOIN delivery_assignments a ON a.order_id=o.id
            WHERE o.id=?''',(order_id,)).fetchone()
    if not row:
        raise HTTPException(404,'Brak lokalizacji zamówienia')
    # Buyer can access their own location. Farmer may see pickup location;
    # delivery address is not exposed to farmer through this endpoint.
    allowed = (user['role']=='klient' and row['buyer_id']==user['id'])
    # A farmer may inspect their own pickup point, never a buyer's delivery address.
    allowed = allowed or (
        user['role']=='rolnik' and row['farmer_id']==user['id']
        and row['fulfillment']=='odbior'
    )
    if user['role']=='dostawca':
        allowed = courier_may_see_address(
            actor_id=user['id'],courier_id=row['courier_id'],
            fulfillment=row['fulfillment'],status=row['status'],
            pin_used=row['pin_used'],confirmed_at=row['confirmed_at'])
    if not allowed:
        raise HTTPException(403,'Brak dostępu do adresu')
    return {k:row[k] for k in ('fulfillment','pickup_point_id','delivery_city',
                               'delivery_street','delivery_postal_code')}

@app.post('/auth/logout-all')
def logout_all(user=Depends(current_user), authorization: str | None = Header(default=None)):
    with account_session_db(user,authorization) as con:
        con.execute('DELETE FROM sessions WHERE user_id=?', (user['id'],))
    return {'ok': True, 'message': 'Wszystkie sesje zostały unieważnione'}


# Etap 9: przypisywanie dostawcy, statusy i historia zdarzeń (tryb testowy).
def record_order_event(con, order_id, actor_id, event_type, old_status, new_status):
    """Persist audit event and recipient-scoped inbox entries in the same transaction."""
    timestamp = datetime.now(timezone.utc).isoformat()
    con.execute('INSERT INTO order_events(order_id,actor_id,event_type,previous_status,new_status,created_at) VALUES(?,?,?,?,?,?)',
                (order_id,actor_id,event_type,old_status,new_status,timestamp))
    order = con.execute('SELECT buyer_id,farmer_id FROM orders WHERE id=?', (order_id,)).fetchone()
    if not order:
        raise ValueError('Nie istnieje zamówienie')
    messages = {
        'order_created': ('Nowe zamówienie', 'Utworzono zamówienie testowe, bez pobrania płatności.'),
        'pickup_ready': ('Gotowe do odbioru', 'Możesz sprawdzić produkty przed podaniem PIN-u.'),
        'courier_assigned': ('Przydzielono dostawcę', 'Do zamówienia testowego przydzielono dostawcę.'),
        'dispatched_test': ('Zamówienie w drodze', 'Dostawa testowa została oznaczona jako wysłana.'),
        'pin_confirmed': ('Odbiór potwierdzony', 'Odbiór potwierdzono jednorazowym PIN-em.'),
        'cancel_test': ('Zamówienie anulowane', 'Zamówienie testowe zostało anulowane.'),
        'reservation_expired_test': ('Upłynął termin rezerwacji', 'Nieopłacona rezerwacja wygasła po 30 minutach. Towar wrócił do sprzedaży. Nie pobrano ani nie zwrócono pieniędzy.'),
        'courier_delivery_failed_test': ('Dostawa nieudana — zwrot testowy', 'Zgłoszono niedostarczenie przesyłki przez dostawcę. Zwrot jest symulowany, bez przelewu pieniędzy.'),
    }
    title, body = messages.get(event_type, ('Aktualizacja zamówienia', 'Zmieniono status zamówienia.'))
    recipients = {order['buyer_id'], order['farmer_id']}
    if event_type in ('courier_assigned','dispatched_test','pin_confirmed'):
        assignment = con.execute('SELECT courier_id FROM delivery_assignments WHERE order_id=?',(order_id,)).fetchone()
        if assignment:
            recipients.add(assignment['courier_id'])
    for recipient in recipients:
        con.execute('INSERT INTO notifications(user_id,order_id,event_type,title,body,created_at) VALUES(?,?,?,?,?,?)',
                    (recipient,order_id,event_type,title,body,timestamp))

class AssignCourierIn(BaseModel):
    courier_id: int = Field(strict=True, ge=1)

@app.post('/orders/{order_id}/assign-courier-test')
def assign_courier_test(order_id:int,payload:AssignCourierIn,user=Depends(current_user), authorization: str | None = Header(default=None)):
    require(user,'rolnik')
    with order_write_db(user, authorization, ('rolnik',)) as con:
        order=con.execute('SELECT * FROM orders WHERE id=?' + (' FOR UPDATE' if DATABASE_URL else ''),(order_id,)).fetchone()
        if not order or order['farmer_id']!=user['id']:
            raise HTTPException(404,'Nie znaleziono zamówienia')
        if order['fulfillment']!='dostawa' or order['status']!='oczekuje_na_platnosc_testowa':
            raise HTTPException(409,'Dostawcę można przypisać tylko do dostawy oczekującej w trybie testowym')
        courier=con.execute('SELECT id FROM users WHERE id=? AND role=?',(payload.courier_id,'dostawca')).fetchone()
        if not courier:
            raise HTTPException(422,'Wskazany użytkownik nie jest dostawcą')
        assigned=con.execute('SELECT order_id FROM delivery_assignments WHERE order_id=?',(order_id,)).fetchone()
        if assigned:
            raise HTTPException(409,'Dostawca został już przypisany')
        con.execute('INSERT INTO delivery_assignments(order_id,courier_id,assigned_by,assigned_at) VALUES(?,?,?,?)',
                    (order_id,payload.courier_id,user['id'],datetime.now(timezone.utc).isoformat()))
        record_order_event(con,order_id,user['id'],'courier_assigned',order['status'],order['status'])
    return {'order_id':order_id,'courier_id':payload.courier_id,'mode':'test'}

@app.post('/orders/{order_id}/dispatch-test')
def dispatch_test(order_id:int,user=Depends(current_user), authorization: str | None = Header(default=None)):
    require(user,'rolnik')
    with order_write_db(user, authorization, ('rolnik',)) as con:
        order=con.execute('SELECT * FROM orders WHERE id=?' + (' FOR UPDATE' if DATABASE_URL else ''),(order_id,)).fetchone()
        if not order or order['farmer_id']!=user['id']:
            raise HTTPException(404,'Nie znaleziono zamówienia')
        if order['fulfillment']!='dostawa' or order['status']!='oczekuje_na_platnosc_testowa':
            raise HTTPException(409,'Nieprawidłowy status dostawy')
        assignment=con.execute('SELECT courier_id FROM delivery_assignments WHERE order_id=?',(order_id,)).fetchone()
        if not assignment:
            raise HTTPException(409,'Najpierw przypisz dostawcę')
        require_unexpired_unpaid_reservation(con, order_id)
        require_transition(order['fulfillment'], order['status'], 'w_drodze_testowo')
        con.execute('UPDATE orders SET status=? WHERE id=?',('w_drodze_testowo',order_id))
        record_order_event(con,order_id,user['id'],'dispatched_test',order['status'],'w_drodze_testowo')
    return {'status':'w_drodze_testowo','warning':'Nie oznacza rzeczywistej opłaconej dostawy'}


# B/621–B/640: atomowa obsługa całej przesyłki przez rolnika i dostawcę.
@app.post('/shipments/{shipment_id}/assign-courier-test')
def assign_shipment_courier(shipment_id: str, payload: AssignCourierIn,
                            user=Depends(current_user), authorization: str | None = Header(default=None)):
    require(user, 'rolnik')
    with order_write_db(user, authorization, ('rolnik',)) as con:
        shipment = con.execute('SELECT * FROM shipment_groups WHERE id=?' + (' FOR UPDATE' if DATABASE_URL else ''), (shipment_id,)).fetchone()
        if not shipment or shipment['farmer_id'] != user['id']:
            raise HTTPException(404, 'Nie znaleziono przesyłki')
        if shipment['fulfillment'] != 'dostawa':
            raise HTTPException(409, 'Przesyłka nie jest dostawą na adres')
        courier = con.execute('SELECT id FROM users WHERE id=? AND role=?', (payload.courier_id, 'dostawca')).fetchone()
        if not courier:
            raise HTTPException(422, 'Nie znaleziono dostawcy')
        orders = con.execute('SELECT o.* FROM orders o JOIN shipment_order_links l ON l.order_id=o.id WHERE l.shipment_id=? ORDER BY o.id' + (' FOR UPDATE OF o' if DATABASE_URL else ''), (shipment_id,)).fetchall()
        require_shipment_membership(shipment, orders)
        if not orders or any(o['status'] != 'oczekuje_na_platnosc_testowa' for o in orders):
            raise HTTPException(409, 'Nieprawidłowy status zamówień')
        if any(con.execute('SELECT 1 FROM delivery_assignments WHERE order_id=?', (o['id'],)).fetchone() for o in orders):
            raise HTTPException(409, 'Dostawca jest już przypisany')
        now = datetime.now(timezone.utc).isoformat()
        for o in orders:
            con.execute('INSERT INTO delivery_assignments(order_id,courier_id,assigned_by,assigned_at) VALUES(?,?,?,?)', (o['id'],payload.courier_id,user['id'],now))
            record_order_event(con,o['id'],user['id'],'courier_assigned',o['status'],o['status'])
    return {'shipment_id':shipment_id,'courier_id':payload.courier_id,'assigned_orders':len(orders),'mode':'test'}

@app.post('/shipments/{shipment_id}/dispatch-test')
def dispatch_shipment(shipment_id: str, user=Depends(current_user), authorization: str | None = Header(default=None)):
    require(user, 'rolnik')
    with order_write_db(user, authorization, ('rolnik',)) as con:
        shipment = con.execute('SELECT * FROM shipment_groups WHERE id=?' + (' FOR UPDATE' if DATABASE_URL else ''), (shipment_id,)).fetchone()
        if not shipment or shipment['farmer_id'] != user['id']:
            raise HTTPException(404, 'Nie znaleziono przesyłki')
        if shipment['fulfillment'] != 'dostawa':
            raise HTTPException(409, 'Przesyłka nie jest dostawą na adres')
        orders = con.execute('SELECT o.* FROM orders o JOIN shipment_order_links l ON l.order_id=o.id WHERE l.shipment_id=? ORDER BY o.id' + (' FOR UPDATE OF o' if DATABASE_URL else ''), (shipment_id,)).fetchall()
        require_shipment_membership(shipment, orders)
        if not orders or any(o['status'] != 'oczekuje_na_platnosc_testowa' for o in orders):
            raise HTTPException(409, 'Nieprawidłowy status zamówień')
        couriers = [con.execute('SELECT courier_id FROM delivery_assignments WHERE order_id=?',(o['id'],)).fetchone() for o in orders]
        if any(c is None for c in couriers) or len({c['courier_id'] for c in couriers}) != 1:
            raise HTTPException(409, 'Cała przesyłka musi mieć jednego przypisanego dostawcę')
        for o in orders:
            require_unexpired_unpaid_reservation(con, o['id'])
        for o in orders:
            require_transition(o['fulfillment'],o['status'],'w_drodze_testowo')
            con.execute('UPDATE orders SET status=? WHERE id=?',('w_drodze_testowo',o['id']))
            record_order_event(con,o['id'],user['id'],'dispatched_test',o['status'],'w_drodze_testowo')
    return {'shipment_id':shipment_id,'status':'w_drodze_testowo','dispatched_orders':len(orders),'mode':'test'}

class ShipmentFailureIn(BaseModel):
    reason: Literal['dostawca_nie_przyjechal', 'dostawca_nie_dostarczyl']

@app.post('/shipments/{shipment_id}/courier-failure-test')
def fail_shipment_by_courier(shipment_id: str, payload: ShipmentFailureIn,
                            user=Depends(current_user), authorization: str | None = Header(default=None)):
    # Atomowa symulacja zwrotu bez przelewu.
    require(user, 'rolnik')
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja zwrotów jest wyłączona')
    with order_write_db(user, authorization, ('rolnik',)) as con:
        shipment = con.execute('SELECT * FROM shipment_groups WHERE id=?' + (' FOR UPDATE' if DATABASE_URL else ''), (shipment_id,)).fetchone()
        if not shipment or shipment['farmer_id'] != user['id']:
            raise HTTPException(404, 'Nie znaleziono przesyłki')
        if shipment['fulfillment'] != 'dostawa':
            raise HTTPException(409, 'Zwrot dotyczy tylko dostawy na adres')
        orders = con.execute("""SELECT o.* FROM orders o JOIN shipment_order_links l ON l.order_id=o.id
            WHERE l.shipment_id=? ORDER BY o.id""" + (' FOR UPDATE OF o' if DATABASE_URL else ''), (shipment_id,)).fetchall()
        require_shipment_membership(shipment, orders)
        if not orders:
            raise HTTPException(409, 'Przesyłka nie zawiera zamówień')
        states = {o['status'] for o in orders}
        if states == {'nieudana_dostawa_testowo'}:
            payments = [checked_refund_payment(con, o) for o in orders]
            if any(p is None or p.state != 'refunded_test' or p.refund_grosze != o['total_grosze']
                   for p, o in zip(payments, orders)):
                raise HTTPException(409, 'Niespójny stan zwrotów przesyłki')
            return {'shipment_id': shipment_id, 'status':'nieudana_dostawa_testowo',
                    'refund_grosze':sum(p.refund_grosze for p in payments), 'mode':'test', 'already_processed':True}
        if states != {'w_drodze_testowo'}:
            raise HTTPException(409, 'Zwrot możliwy tylko dla całej przesyłki w drodze')
        courier_ids = []
        for order in orders:
            assignment = con.execute('SELECT courier_id FROM delivery_assignments WHERE order_id=?', (order['id'],)).fetchone()
            if not assignment:
                raise HTTPException(409, 'Brak dostawcy dla zamówienia')
            courier_ids.append(assignment['courier_id'])
            payment = checked_refund_payment(con, order)
            if payment is None or payment.state != 'paid_test':
                raise HTTPException(409, 'Przed zwrotem wszystkie zamówienia muszą mieć symulowaną płatność')
        if len(set(courier_ids)) != 1:
            raise HTTPException(409, 'Niespójny dostawca przesyłki')
        refunded = 0
        for order in orders:
            payment = checked_refund_payment(con, order)
            event_id = 'shipment-failure:' + hashlib.sha256(f'{shipment_id}:{order["id"]}'.encode()).hexdigest()
            updated = persist_event(con, payment, event_id, 'delivery_failed_by_courier_test', datetime.now(timezone.utc).isoformat())
            refunded += updated.refund_grosze
            require_transition(order['fulfillment'], order['status'], 'nieudana_dostawa_testowo')
            con.execute('UPDATE orders SET status=? WHERE id=?', ('nieudana_dostawa_testowo', order['id']))
            record_order_event(con, order['id'], user['id'], 'courier_delivery_failed_test',
                               order['status'], 'nieudana_dostawa_testowo')
        return {'shipment_id':shipment_id, 'status':'nieudana_dostawa_testowo',
                'refund_grosze':refunded, 'mode':'test', 'already_processed':False,
                'notice':'Zwrot wyłącznie symulowany; nie wysłano pieniędzy.'}

# B/741: administracyjny, wyłącznie odczytowy rejestr przesyłek.
# Nie ujawnia adresów, kodów PIN ani danych kontaktowych.
@app.get('/admin/shipments/overview')
def admin_shipments_overview(limit: int = 50, offset: int = 0,
                             status: str | None = None, user=Depends(current_user)):
    require(user, 'admin')
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, 'Nieprawidłowa paginacja')
    allowed_statuses = {'oczekuje_na_platnosc_testowa', 'gotowe_do_odbioru_testowo',
                        'w_drodze_testowo', 'odebrane', 'anulowane_testowo',
                        'nieudana_dostawa_testowo'}
    if status is not None and status not in allowed_statuses:
        raise HTTPException(422, 'Nieprawidłowy filtr statusu')
    with db() as con:
        # Filtr statusu dotyczy całej przesyłki: wszystkie jej pozycje muszą
        # mieć wskazany status. Niejednorodne przesyłki oznaczamy jako mieszane.
        base = '''SELECT s.id AS shipment_id, s.fulfillment, s.delivery_grosze,
            s.created_at, COUNT(o.id) AS order_count,
            COALESCE(SUM(o.total_grosze),0) AS total_grosze,
            MIN(o.status) AS min_status, MAX(o.status) AS max_status
            FROM shipment_groups s
            JOIN shipment_order_links l ON l.shipment_id=s.id
            JOIN orders o ON o.id=l.order_id
            GROUP BY s.id,s.fulfillment,s.delivery_grosze,s.created_at'''
        predicate = ' WHERE min_status=? AND max_status=?' if status else ''
        args = (status, status) if status else ()
        total = con.execute('SELECT COUNT(*) AS n FROM (' + base + ') grouped' + predicate, args).fetchone()['n']
        rows = con.execute('SELECT * FROM (' + base + ') grouped' + predicate +
                           ' ORDER BY created_at DESC, shipment_id DESC LIMIT ? OFFSET ?',
                           (*args, limit, offset)).fetchall()
    shipments = []
    from backend.payment_store import get_payment
    with db() as payment_con:
        refund_by_shipment = {}
        for row in rows:
            order_ids = payment_con.execute('SELECT order_id FROM shipment_order_links WHERE shipment_id=?', (row['shipment_id'],)).fetchall()
            refund_by_shipment[row['shipment_id']] = sum((get_payment(payment_con, entry['order_id']).refund_grosze if get_payment(payment_con, entry['order_id']) else 0) for entry in order_ids)
    for row in rows:
        item = dict(row)
        item['status'] = item.pop('min_status') if item['min_status'] == item['max_status'] else 'mieszany'
        item.pop('max_status')
        item['products_grosze'] = item['total_grosze'] - item['delivery_grosze']
        item['refund_test_grosze'] = refund_by_shipment[item['shipment_id']]
        shipments.append(item)
    return {'shipments': shipments, 'total': total, 'limit': limit, 'offset': offset,
            'mode': 'test', 'refund_note': 'Kwoty zwrotów są wyłącznie symulowane.'}


@app.get('/admin/shipments/{shipment_id}/audit')
def admin_shipment_audit(shipment_id: str, user=Depends(current_user)):
    """Read-only audit: actual simulated refund ledger and per-order event trail."""
    require(user, 'admin')
    from backend.payment_store import get_payment
    with db() as con:
        shipment = con.execute('SELECT id,fulfillment,delivery_grosze,created_at FROM shipment_groups WHERE id=?', (shipment_id,)).fetchone()
        if shipment is None:
            raise HTTPException(404, 'Nie znaleziono przesyłki')
        orders = con.execute("""SELECT o.id,o.status,o.total_grosze,o.subtotal_grosze,o.delivery_grosze
            FROM orders o JOIN shipment_order_links l ON l.order_id=o.id
            WHERE l.shipment_id=? ORDER BY o.id""", (shipment_id,)).fetchall()
        items = []
        for order in orders:
            payment = get_payment(con, order['id'])
            events = con.execute("""SELECT event_type,previous_status,new_status,created_at
                FROM order_events WHERE order_id=? ORDER BY id""", (order['id'],)).fetchall()
            items.append({**dict(order), 'refund_test_grosze': payment.refund_grosze if payment else 0,
                          'events': [dict(event) for event in events]})
        total = sum(item['total_grosze'] for item in items)
        delivery = sum(item['delivery_grosze'] for item in items)
        return {'shipment_id': shipment_id, 'created_at': shipment['created_at'],
                'fulfillment': shipment['fulfillment'], 'order_count': len(items),
                'total_grosze': total, 'delivery_grosze': delivery,
                'refund_test_grosze': sum(item['refund_test_grosze'] for item in items),
                'delivery_consistent': delivery == shipment['delivery_grosze'],
                'items': items, 'mode': 'test'}


@app.get('/admin/shipments/reconciliation')
def admin_shipments_reconciliation(limit: int = 100, offset: int = 0,
                                   only_issues: bool = False, user=Depends(current_user)):
    """Read-only consistency report; does not change payments or shipment records."""
    require(user, 'admin')
    if not 1 <= limit <= 500 or offset < 0:
        raise HTTPException(422, 'Nieprawidłowa paginacja')
    from backend.payment_store import get_payment
    with db() as con:
        shipments = con.execute('SELECT id,buyer_id,farmer_id,fulfillment,delivery_grosze FROM shipment_groups ORDER BY id').fetchall()
        results = []
        for shipment in shipments:
            rows = con.execute('SELECT o.id,o.buyer_id,o.farmer_id,o.fulfillment,o.status,o.subtotal_grosze,o.delivery_grosze,o.total_grosze FROM shipment_order_links l JOIN orders o ON o.id=l.order_id WHERE l.shipment_id=?', (shipment['id'],)).fetchall()
            issues = []
            delivery = sum(r['delivery_grosze'] for r in rows)
            products = sum(r['subtotal_grosze'] for r in rows)
            total = sum(r['total_grosze'] for r in rows)
            refund = 0
            if not rows: issues.append('empty_shipment')
            if shipment['delivery_grosze'] < 0: issues.append('negative_shipment_delivery')
            if shipment['fulfillment'] == 'odbior' and shipment['delivery_grosze']:
                issues.append('pickup_has_delivery_fee')
            if any(r['buyer_id'] != shipment['buyer_id'] for r in rows):
                issues.append('buyer_mismatch')
            if any(r['farmer_id'] != shipment['farmer_id'] for r in rows):
                issues.append('farmer_mismatch')
            if any(r['fulfillment'] != shipment['fulfillment'] for r in rows):
                issues.append('fulfillment_mismatch')
            if any(r['subtotal_grosze'] < 0 or r['delivery_grosze'] < 0 or r['total_grosze'] < 0 for r in rows):
                issues.append('negative_order_amount')
            if shipment['fulfillment'] == 'dostawa' and sum(1 for r in rows if r['delivery_grosze'] > 0) > 1:
                issues.append('delivery_charged_multiple_times')
            if delivery != shipment['delivery_grosze']: issues.append('delivery_mismatch')
            if shipment['fulfillment'] != 'dostawa' and delivery: issues.append('pickup_has_delivery_fee')
            if products + delivery != total: issues.append('total_mismatch')
            if any(r['subtotal_grosze'] + r['delivery_grosze'] != r['total_grosze'] for r in rows):
                issues.append('order_line_total_mismatch')
            if shipment['fulfillment'] not in ('dostawa', 'odbior'):
                issues.append('invalid_fulfillment')
            if any(r['fulfillment'] not in ('dostawa', 'odbior') for r in rows):
                issues.append('invalid_order_fulfillment')
            if len({r['status'] for r in rows}) > 1: issues.append('mixed_statuses')
            for row in rows:
                payment = get_payment(con, row['id'])
                if payment:
                    refund += payment.refund_grosze
                    if payment.refund_grosze < 0 or payment.refund_grosze > row['total_grosze']:
                        issues.append('invalid_refund')
            if refund > total: issues.append('refund_exceeds_total')
            if rows and all(r['status'] == 'nieudana_dostawa_testowo' for r in rows) and refund != total:
                issues.append('failed_delivery_refund_incomplete')
            if issues or not only_issues:
                results.append({'shipment_id':shipment['id'], 'order_count':len(rows),
                                'products_grosze':products, 'delivery_grosze':delivery,
                                'total_grosze':total, 'refund_test_grosze':refund,
                                'issues':sorted(set(issues))})
        return {'total':len(results), 'limit':limit, 'offset':offset,
                'shipments':results[offset:offset+limit], 'mode':'test', 'read_only':True}


@app.get('/couriers/me/shipments')
def courier_shipments(user=Depends(current_user)):
    require(user,'dostawca')
    with db() as con:
        rows = con.execute('''SELECT s.id AS shipment_id, s.fulfillment, s.delivery_grosze,
            COUNT(o.id) AS item_count, SUM(o.total_grosze) AS total_grosze,
            MIN(o.status) AS status
            FROM shipment_groups s JOIN shipment_order_links l ON l.shipment_id=s.id
            JOIN orders o ON o.id=l.order_id
            JOIN delivery_assignments d ON d.order_id=o.id
            WHERE d.courier_id=? AND s.fulfillment='dostawa'
            GROUP BY s.id,s.fulfillment,s.delivery_grosze
            HAVING COUNT(o.id)=(SELECT COUNT(*) FROM shipment_order_links all_links WHERE all_links.shipment_id=s.id)
            ORDER BY s.id DESC''',(user['id'],)).fetchall()
        return {'shipments':[dict(r) for r in rows]}

@app.get('/orders/{order_id}/events')
def order_events(order_id:int,user=Depends(current_user)):
    with db() as con:
        order=con.execute('SELECT buyer_id,farmer_id FROM orders WHERE id=?',(order_id,)).fetchone()
        if not order:
            raise HTTPException(404,'Brak zamówienia')
        assigned=con.execute('SELECT courier_id FROM delivery_assignments WHERE order_id=?',(order_id,)).fetchone()
        allowed=user['id'] in (order['buyer_id'],order['farmer_id']) or (assigned and user['id']==assigned['courier_id'])
        if not allowed:
            raise HTTPException(403,'Brak uprawnień')
        return [dict(row) for row in con.execute('SELECT event_type,previous_status,new_status,created_at FROM order_events WHERE order_id=? ORDER BY id',(order_id,))]

@app.get('/couriers/me/orders')
def courier_orders(user=Depends(current_user)):
    require(user,'dostawca')
    with db() as con:
        return [dict(row) for row in con.execute('SELECT o.id,o.pickup_code,o.status,o.fulfillment FROM orders o JOIN delivery_assignments d ON d.order_id=o.id WHERE d.courier_id=? ORDER BY o.id DESC',(user['id'],))]


# Etap 10: powiadomienia wyłącznie wewnątrz konta (bez telefonów, e-maili i push).
@app.get('/notifications/me')
def my_notifications(limit:int=20, user=Depends(current_user)):
    if not 1 <= limit <= 100:
        raise HTTPException(422,'Limit musi mieścić się w przedziale 1–100')
    with db() as con:
        rows = con.execute("SELECT id,order_id,event_type,title,body,created_at,read_at FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT ?",
                           (user['id'],limit))
        return [dict(row) for row in rows]

@app.get('/notifications/me/unread-count')
def unread_notification_count(user=Depends(current_user)):
    with db() as con:
        row=con.execute('SELECT COUNT(*) AS total FROM notifications WHERE user_id=? AND read_at IS NULL',(user['id'],)).fetchone()
        return {'unread':row['total']}

@app.post('/notifications/{notification_id}/read')
def mark_notification_read(notification_id:int,user=Depends(current_user), authorization: str | None = Header(default=None)):
    now=datetime.now(timezone.utc).isoformat()
    with order_write_db(user, authorization, ('klient','rolnik','dostawca','admin')) as con:
        found=con.execute('SELECT id FROM notifications WHERE id=? AND user_id=?',(notification_id,user['id'])).fetchone()
        if not found:
            raise HTTPException(404,'Nie znaleziono powiadomienia')
        con.execute('UPDATE notifications SET read_at=? WHERE id=? AND user_id=? AND read_at IS NULL',
                    (now,notification_id,user['id']))
    return {'ok':True}



def migrate_stage11():
    """Draft-only commission records; no fiscal document is issued."""
    if DATABASE_URL:
        return
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS commission_drafts (
          id INTEGER PRIMARY KEY,
          order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id),
          farmer_id INTEGER NOT NULL REFERENCES users(id),
          basis_grosze INTEGER NOT NULL CHECK(basis_grosze>=0),
          rate_basis_points INTEGER NOT NULL CHECK(rate_basis_points BETWEEN 0 AND 10000),
          commission_grosze INTEGER NOT NULL CHECK(commission_grosze>=0),
          currency TEXT NOT NULL DEFAULT 'PLN',
          state TEXT NOT NULL DEFAULT 'draft' CHECK(state='draft'),
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS commission_drafts_farmer_idx ON commission_drafts(farmer_id,id);
        """)
migrate_stage11()

from backend.invoicing import calculate_commission_grosze

class CommissionDraftIn(BaseModel):
    order_id: int = Field(strict=True, ge=1)
    rate_basis_points: int = Field(strict=True, ge=0, le=10000)

@app.post('/accounting/commission-drafts', status_code=201)
def create_commission_draft(payload: CommissionDraftIn, user=Depends(current_user), authorization: str | None = Header(default=None)):
    """Create a private, non-fiscal preview; restricted to the seller of this order."""
    require(user, 'rolnik')
    with order_write_db(user, authorization, ('admin',) if user['role'] == 'admin' else ('rolnik',)) as con:
        order = con.execute('SELECT id,farmer_id,subtotal_grosze FROM orders WHERE id=?', (payload.order_id,)).fetchone()
        if not order or order['farmer_id'] != user['id']:
            raise HTTPException(404, 'Nie znaleziono zamówienia')
        # Basis: goods subtotal, explicitly excluding delivery. No VAT inferred.
        amount = calculate_commission_grosze(order['subtotal_grosze'], payload.rate_basis_points)
        try:
            cur = con.execute("""INSERT INTO commission_drafts
                (order_id,farmer_id,basis_grosze,rate_basis_points,commission_grosze,created_at)
                VALUES(?,?,?,?,?,?)""",
                (order['id'],user['id'],order['subtotal_grosze'],payload.rate_basis_points,amount,datetime.now(timezone.utc).isoformat()))
        except (sqlite3.IntegrityError, PgUniqueViolation):
            raise HTTPException(409, 'Projekt rozliczenia dla zamówienia już istnieje')
        return {'id':cur.lastrowid,'order_id':order['id'],'basis_grosze':order['subtotal_grosze'],
                'rate_basis_points':payload.rate_basis_points,'commission_grosze':amount,
                'status':'draft','faktura_wystawiona':False}

@app.get('/accounting/commission-drafts/me')
def my_commission_drafts(user=Depends(current_user)):
    require(user, 'rolnik')
    with db() as con:
        rows = con.execute("""SELECT id,order_id,basis_grosze,rate_basis_points,commission_grosze,
            currency,state,created_at FROM commission_drafts WHERE farmer_id=? ORDER BY id DESC""",
            (user['id'],)).fetchall()
        return {'items':[dict(r) for r in rows], 'faktury_wystawione':False}


# ETAP 12: Faktury - wyłącznie projekty dokumentów do weryfikacji księgowej.
def migrate_stage12():
    if DATABASE_URL:
        return  # Apply database/upgrade_12.sql to PostgreSQL before using endpoints.
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS invoice_drafts (
          id INTEGER PRIMARY KEY,
          commission_draft_id INTEGER NOT NULL UNIQUE REFERENCES commission_drafts(id),
          farmer_id INTEGER NOT NULL REFERENCES users(id),
          seller_name TEXT NOT NULL,
          seller_nip TEXT NOT NULL,
          buyer_name TEXT NOT NULL,
          buyer_nip TEXT,
          description TEXT NOT NULL,
          net_grosze INTEGER NOT NULL CHECK(net_grosze>=0),
          vat_basis_points INTEGER,
          vat_grosze INTEGER,
          gross_grosze INTEGER,
          currency TEXT NOT NULL DEFAULT 'PLN',
          state TEXT NOT NULL DEFAULT 'pending_tax_review' CHECK(state='pending_tax_review'),
          created_at TEXT NOT NULL,
          CHECK ((vat_basis_points IS NULL AND vat_grosze IS NULL AND gross_grosze IS NULL)
              OR (vat_basis_points BETWEEN 0 AND 10000 AND vat_grosze>=0 AND gross_grosze=net_grosze+vat_grosze))
        );
        CREATE INDEX IF NOT EXISTS invoice_drafts_farmer_idx ON invoice_drafts(farmer_id,id);
        """)
migrate_stage12()

class InvoiceDraftIn(BaseModel):
    commission_draft_id: int = Field(strict=True, ge=1)
    seller_name: str = Field(min_length=2, max_length=180)
    seller_nip: str = Field(pattern=r'^\d{10}$')
    buyer_name: str = Field(min_length=2, max_length=180)
    buyer_nip: str | None = Field(default=None, pattern=r'^\d{10}$')

@app.post('/accounting/invoice-drafts', status_code=201)
def create_invoice_draft(payload: InvoiceDraftIn, user=Depends(current_user), authorization: str | None = Header(default=None)):
    """Generate immutable review snapshot. NOT a tax invoice, no KSeF submission."""
    require(user,'rolnik')
    with order_write_db(user, authorization, ('admin',) if user['role'] == 'admin' else ('rolnik',)) as con:
        draft=con.execute('SELECT id,farmer_id,commission_grosze FROM commission_drafts WHERE id=?',
                          (payload.commission_draft_id,)).fetchone()
        if not draft or draft['farmer_id']!=user['id']:
            raise HTTPException(404,'Nie znaleziono projektu rozliczenia')
        try:
            cur=con.execute("""INSERT INTO invoice_drafts
              (commission_draft_id,farmer_id,seller_name,seller_nip,buyer_name,buyer_nip,
               description,net_grosze,created_at)
              VALUES(?,?,?,?,?,?,?,?,?)""",
              (draft['id'],user['id'],payload.seller_name.strip(),payload.seller_nip,
               payload.buyer_name.strip(),payload.buyer_nip,
               'Projekt dokumentu: prowizja platformy (wymaga weryfikacji wystawcy i VAT)',
               draft['commission_grosze'],datetime.now(timezone.utc).isoformat()))
        except (sqlite3.IntegrityError,PgUniqueViolation):
            raise HTTPException(409,'Projekt dokumentu dla tego rozliczenia już istnieje')
        return {'id':cur.lastrowid,'state':'pending_tax_review','net_grosze':draft['commission_grosze'],
                'vat_grosze':None,'gross_grosze':None,'issued':False,'sent_to_ksef':False}

@app.get('/accounting/invoice-drafts/me')
def my_invoice_drafts(user=Depends(current_user)):
    require(user,'rolnik')
    with db() as con:
        rows=con.execute("""SELECT id,commission_draft_id,seller_name,seller_nip,buyer_name,buyer_nip,
          description,net_grosze,vat_grosze,gross_grosze,currency,state,created_at
          FROM invoice_drafts WHERE farmer_id=? ORDER BY id DESC""",(user['id'],)).fetchall()
        return {'items':[dict(r) for r in rows], 'issued':False,'sent_to_ksef':False}

# ETAP 13: wnioski o korektę projektu (bez wystawiania faktur i bez wysyłki API).
def migrate_stage13():
    if DATABASE_URL:
        return  # PostgreSQL: database/upgrade_13.sql
    with db() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS invoice_correction_requests (
          id INTEGER PRIMARY KEY,
          invoice_draft_id INTEGER NOT NULL REFERENCES invoice_drafts(id),
          farmer_id INTEGER NOT NULL REFERENCES users(id),
          reason TEXT NOT NULL CHECK(length(reason) BETWEEN 10 AND 1000),
          requested_net_grosze INTEGER NOT NULL CHECK(requested_net_grosze>=0),
          status TEXT NOT NULL DEFAULT 'pending_review' CHECK(status='pending_review'),
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS correction_requests_farmer_idx
          ON invoice_correction_requests(farmer_id,id);
        CREATE TABLE IF NOT EXISTS accounting_audit_events (
          id INTEGER PRIMARY KEY,
          farmer_id INTEGER NOT NULL REFERENCES users(id),
          invoice_draft_id INTEGER NOT NULL REFERENCES invoice_drafts(id),
          event_type TEXT NOT NULL CHECK(event_type IN ('correction_requested')),
          correction_request_id INTEGER NOT NULL UNIQUE REFERENCES invoice_correction_requests(id),
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS accounting_audit_farmer_idx
          ON accounting_audit_events(farmer_id,id);
        ''')
migrate_stage13()

class CorrectionRequestIn(BaseModel):
    invoice_draft_id: int = Field(strict=True, ge=1)
    reason: str = Field(min_length=10,max_length=1000)
    requested_net_grosze: int = Field(strict=True, ge=0,le=9223372036854775807)

@app.post('/accounting/correction-requests',status_code=201)
def request_invoice_correction(payload:CorrectionRequestIn,user=Depends(current_user), authorization: str | None = Header(default=None)):
    """Only a review request; never modifies a draft or creates a tax correction."""
    require(user,'rolnik')
    reason=payload.reason.strip()
    if len(reason)<10:
        raise HTTPException(422,'Uzasadnienie musi mieć co najmniej 10 znaków')
    with order_write_db(user, authorization, ('admin',) if user['role'] == 'admin' else ('rolnik',)) as con:
        draft=con.execute('SELECT id,farmer_id FROM invoice_drafts WHERE id=?',
                          (payload.invoice_draft_id,)).fetchone()
        if not draft or draft['farmer_id']!=user['id']:
            raise HTTPException(404,'Nie znaleziono projektu dokumentu')
        now=datetime.now(timezone.utc).isoformat()
        cur=con.execute('''INSERT INTO invoice_correction_requests
          (invoice_draft_id,farmer_id,reason,requested_net_grosze,created_at)
          VALUES(?,?,?,?,?)''',(draft['id'],user['id'],reason,payload.requested_net_grosze,now))
        con.execute('''INSERT INTO accounting_audit_events
          (farmer_id,invoice_draft_id,event_type,correction_request_id,created_at)
          VALUES(?,?,?,?,?)''',(user['id'],draft['id'],'correction_requested',cur.lastrowid,now))
        return {'id':cur.lastrowid,'status':'pending_review','issued':False,'sent_to_ksef':False}

@app.get('/accounting/correction-requests/me')
def my_correction_requests(user=Depends(current_user)):
    require(user,'rolnik')
    with db() as con:
        rows=con.execute('''SELECT id,invoice_draft_id,reason,requested_net_grosze,status,created_at
          FROM invoice_correction_requests WHERE farmer_id=? ORDER BY id DESC''',(user['id'],)).fetchall()
        return {'items':[dict(row) for row in rows],'issued':False}

@app.get('/accounting/audit/me')
def my_accounting_audit(user=Depends(current_user)):
    require(user,'rolnik')
    with db() as con:
        rows=con.execute('''SELECT id,invoice_draft_id,event_type,correction_request_id,created_at
          FROM accounting_audit_events WHERE farmer_id=? ORDER BY id DESC''',(user['id'],)).fetchall()
        return {'items':[dict(row) for row in rows]}

# ETAP 14: bezpieczna kolejka eksportu do przyszłego adaptera księgowego.
# Brak połączeń HTTP, emisji dokumentów, numeracji faktur i wysyłki do KSeF.
def migrate_stage14():
    if DATABASE_URL:
        return  # PostgreSQL: database/upgrade_14.sql
    with db() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS accounting_export_jobs (
          id INTEGER PRIMARY KEY,
          invoice_draft_id INTEGER NOT NULL UNIQUE REFERENCES invoice_drafts(id),
          farmer_id INTEGER NOT NULL REFERENCES users(id),
          status TEXT NOT NULL DEFAULT 'blocked_tax_review' CHECK(status='blocked_tax_review'),
          payload_sha256 TEXT NOT NULL CHECK(length(payload_sha256)=64),
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS accounting_export_jobs_farmer_idx
          ON accounting_export_jobs(farmer_id,id);
        ''')
migrate_stage14()


def accounting_preview_data(draft):
    """Minimalny, deterministyczny podgląd bez danych osobowych ani API tokenów."""
    return {
        'source_type': 'commission_invoice_draft',
        'source_id': draft['id'],
        'currency': draft['currency'],
        'net_grosze': draft['net_grosze'],
        'vat_grosze': draft['vat_grosze'],
        'gross_grosze': draft['gross_grosze'],
        'tax_review_required': True,
        'is_invoice': False,
    }


@app.get('/accounting/export-preview/{draft_id}')
def accounting_export_preview(draft_id: int, user=Depends(current_user)):
    require(user,'rolnik')
    with db() as con:
        row=con.execute('''SELECT id,farmer_id,currency,net_grosze,vat_grosze,gross_grosze
            FROM invoice_drafts WHERE id=? AND farmer_id=?''',(draft_id,user['id'])).fetchone()
        if not row:
            raise HTTPException(404,'Nie znaleziono projektu dokumentu')
        return accounting_preview_data(row)


@app.post('/accounting/export-jobs/{draft_id}',status_code=201)
def prepare_accounting_export(draft_id: int,user=Depends(current_user), authorization: str | None = Header(default=None)):
    """Idempotentnie rejestruje blokowane zadanie. Nigdy nie wysyła faktury."""
    import json
    require(user,'rolnik')
    with order_write_db(user, authorization, ('admin',) if user['role'] == 'admin' else ('rolnik',)) as con:
        row=con.execute('''SELECT id,farmer_id,currency,net_grosze,vat_grosze,gross_grosze
            FROM invoice_drafts WHERE id=? AND farmer_id=?''',(draft_id,user['id'])).fetchone()
        if not row:
            raise HTTPException(404,'Nie znaleziono projektu dokumentu')
        payload=accounting_preview_data(row)
        fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        con.execute('''INSERT INTO accounting_export_jobs
            (invoice_draft_id,farmer_id,payload_sha256,created_at) VALUES(?,?,?,?)
            ON CONFLICT(invoice_draft_id) DO NOTHING''',
            (draft_id,user['id'],fingerprint,datetime.now(timezone.utc).isoformat()))
        job=con.execute('''SELECT id,invoice_draft_id,status,payload_sha256,created_at
            FROM accounting_export_jobs WHERE invoice_draft_id=? AND farmer_id=?''',
            (draft_id,user['id'])).fetchone()
        return {**dict(job),'sent':False,'issued':False,'ksef_submitted':False}


@app.get('/accounting/export-jobs/me')
def my_accounting_export_jobs(user=Depends(current_user)):
    require(user,'rolnik')
    with db() as con:
        rows=con.execute('''SELECT id,invoice_draft_id,status,payload_sha256,created_at
            FROM accounting_export_jobs WHERE farmer_id=? ORDER BY id DESC''',(user['id'],)).fetchall()
        return {'items':[dict(r) for r in rows],'external_api_enabled':False}

# ETAP 15: diagnostyka bezpiecznej kolejki (bez uruchamiania integracji).
@app.get('/accounting/export-jobs/{job_id}/diagnostics')
def accounting_export_diagnostics(job_id: int, user=Depends(current_user)):
    """Weryfikuje integralność snapshotu i blokady bez ujawniania danych kontrahentów."""
    import json
    require(user, 'rolnik')
    with db() as con:
        row=con.execute('''SELECT j.id,j.invoice_draft_id,j.status,j.payload_sha256,
            d.currency,d.net_grosze,d.vat_grosze,d.gross_grosze,d.id AS draft_id
            FROM accounting_export_jobs j
            JOIN invoice_drafts d ON d.id=j.invoice_draft_id
            WHERE j.id=? AND j.farmer_id=? AND d.farmer_id=?''',
            (job_id,user['id'],user['id'])).fetchone()
        if not row:
            raise HTTPException(404,'Nie znaleziono zadania')
        snapshot=accounting_preview_data({
            'id':row['draft_id'],'currency':row['currency'],
            'net_grosze':row['net_grosze'],'vat_grosze':row['vat_grosze'],
            'gross_grosze':row['gross_grosze']})
        digest=hashlib.sha256(json.dumps(snapshot,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        pending=con.execute('''SELECT COUNT(*) AS n FROM invoice_correction_requests
            WHERE invoice_draft_id=? AND status='pending_review' ''',(row['draft_id'],)).fetchone()['n']
        issues=[]
        if digest != row['payload_sha256']:
            issues.append('snapshot_changed')
        if pending:
            issues.append('pending_correction_review')
        if row['vat_grosze'] is None or row['gross_grosze'] is None:
            issues.append('tax_amounts_unverified')
        elif row['gross_grosze'] != row['net_grosze'] + row['vat_grosze']:
            issues.append('amount_mismatch')
        if row['net_grosze'] < 0 or (row['vat_grosze'] is not None and row['vat_grosze'] < 0):
            issues.append('negative_amount')
        issues.append('tax_review_required')
        return {'job_id':row['id'],'draft_id':row['draft_id'],
                'status':row['status'],'snapshot_integrity_ok':digest==row['payload_sha256'],
                'pending_correction_requests':pending,'issues':issues,
                'ready_for_external_api':False,'sent':False,'issued':False}


# ETAP 16: utrwalona historia kontroli dokumentów; bez wysyłki do zewnętrznych API.
def migrate_stage16():
    if DATABASE_URL:
        return  # PostgreSQL: database/upgrade_16.sql
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS accounting_validation_runs (
          id INTEGER PRIMARY KEY,
          export_job_id INTEGER NOT NULL REFERENCES accounting_export_jobs(id),
          farmer_id INTEGER NOT NULL REFERENCES users(id),
          result_sha256 TEXT NOT NULL CHECK(length(result_sha256)=64),
          issues_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          UNIQUE(export_job_id,result_sha256)
        );
        CREATE INDEX IF NOT EXISTS accounting_validation_runs_owner_idx
          ON accounting_validation_runs(farmer_id,export_job_id,id);
        """)
migrate_stage16()


@app.post('/accounting/export-jobs/{job_id}/validate', status_code=200)
def validate_accounting_export(job_id: int, user=Depends(current_user), authorization: str | None = Header(default=None)):
    # Idempotentny zapis wyniku kontroli; nie zmienia statusu zadania.
    import json
    report=accounting_export_diagnostics(job_id,user=user)
    issues=json.dumps(report['issues'],ensure_ascii=False,separators=(',',':'))
    # Fingerprint includes issues and source snapshot state, never sensitive data.
    canonical=json.dumps({'issues':report['issues'],
        'snapshot_integrity_ok':report['snapshot_integrity_ok'],
        'pending_correction_requests':report['pending_correction_requests']},
        sort_keys=True,separators=(',',':'))
    digest=hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    with order_write_db(user, authorization, ('admin',) if user['role'] == 'admin' else ('rolnik',)) as con:
        # Repeat authorization inside the write transaction.
        owner=con.execute('SELECT id FROM accounting_export_jobs WHERE id=? AND farmer_id=?',
                          (job_id,user['id'])).fetchone()
        if not owner:
            raise HTTPException(404,'Nie znaleziono zadania')
        con.execute("""INSERT INTO accounting_validation_runs
            (export_job_id,farmer_id,result_sha256,issues_json,created_at)
            VALUES(?,?,?,?,?) ON CONFLICT(export_job_id,result_sha256) DO NOTHING""",
            (job_id,user['id'],digest,issues,datetime.now(timezone.utc).isoformat()))
        row=con.execute("""SELECT id,created_at FROM accounting_validation_runs
            WHERE export_job_id=? AND farmer_id=? AND result_sha256=?""",
            (job_id,user['id'],digest)).fetchone()
    return {'validation_id':row['id'],'job_id':job_id,'issues':report['issues'],
            'created_at':row['created_at'],'ready_for_external_api':False,
            'sent':False,'issued':False}


@app.get('/accounting/export-jobs/{job_id}/validation-history')
def accounting_validation_history(job_id: int, user=Depends(current_user)):
    import json
    require(user,'rolnik')
    with db() as con:
        owner=con.execute('SELECT id FROM accounting_export_jobs WHERE id=? AND farmer_id=?',
                          (job_id,user['id'])).fetchone()
        if not owner:
            raise HTTPException(404,'Nie znaleziono zadania')
        rows=con.execute("""SELECT id,issues_json,created_at FROM accounting_validation_runs
            WHERE export_job_id=? AND farmer_id=? ORDER BY id DESC LIMIT 100""",
            (job_id,user['id'])).fetchall()
    return {'job_id':job_id,'items':[{'id':r['id'],'issues':json.loads(r['issues_json']),
        'created_at':r['created_at']} for r in rows]}

# ETAP 17: potwierdzenie zapoznania się z raportem kontroli.
# Potwierdzenie nie zatwierdza faktury i nie odblokowuje wysyłki.
def migrate_stage17():
    if DATABASE_URL:
        return  # PostgreSQL: database/upgrade_17.sql
    with db() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS accounting_review_acknowledgements (
          id INTEGER PRIMARY KEY,
          validation_id INTEGER NOT NULL UNIQUE REFERENCES accounting_validation_runs(id),
          export_job_id INTEGER NOT NULL REFERENCES accounting_export_jobs(id),
          farmer_id INTEGER NOT NULL REFERENCES users(id),
          acknowledged_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS accounting_review_ack_owner_idx
          ON accounting_review_acknowledgements(farmer_id,export_job_id,id);
        ''')
migrate_stage17()


@app.post('/accounting/export-jobs/{job_id}/acknowledge-validation')
def acknowledge_accounting_validation(job_id: int, user=Depends(current_user), authorization: str | None = Header(default=None)):
    """Potwierdzenie zapoznania się WYŁĄCZNIE z najnowszą walidacją.

    Nie jest zatwierdzeniem podatkowym ani zgodą na emisję faktury.
    """
    require(user, 'rolnik')
    with order_write_db(user, authorization, ('admin',) if user['role'] == 'admin' else ('rolnik',)) as con:
        job = con.execute('SELECT id FROM accounting_export_jobs WHERE id=? AND farmer_id=?',
                          (job_id, user['id'])).fetchone()
        if not job:
            raise HTTPException(404, 'Nie znaleziono zadania')
        latest = con.execute('''SELECT id,issues_json,created_at FROM accounting_validation_runs
            WHERE export_job_id=? AND farmer_id=? ORDER BY id DESC LIMIT 1''',
            (job_id,user['id'])).fetchone()
        if not latest:
            raise HTTPException(409, 'Najpierw wykonaj kontrolę dokumentu')
        con.execute('''INSERT INTO accounting_review_acknowledgements
            (validation_id,export_job_id,farmer_id,acknowledged_at)
            VALUES(?,?,?,?) ON CONFLICT(validation_id) DO NOTHING''',
            (latest['id'],job_id,user['id'],datetime.now(timezone.utc).isoformat()))
        ack=con.execute('''SELECT id,validation_id,acknowledged_at
            FROM accounting_review_acknowledgements WHERE validation_id=? AND farmer_id=?''',
            (latest['id'],user['id'])).fetchone()
        return {'id':ack['id'],'validation_id':ack['validation_id'],
                'acknowledged_at':ack['acknowledged_at'],'issues_acknowledged':True,
                'tax_approved':False,'ready_for_external_api':False,'sent':False,'issued':False}


@app.get('/accounting/export-jobs/{job_id}/review-status')
def accounting_review_status(job_id: int, user=Depends(current_user)):
    require(user,'rolnik')
    with db() as con:
        job=con.execute('SELECT id,status FROM accounting_export_jobs WHERE id=? AND farmer_id=?',
                        (job_id,user['id'])).fetchone()
        if not job:
            raise HTTPException(404,'Nie znaleziono zadania')
        latest=con.execute('''SELECT id FROM accounting_validation_runs
            WHERE export_job_id=? AND farmer_id=? ORDER BY id DESC LIMIT 1''',
            (job_id,user['id'])).fetchone()
        acknowledged=False
        if latest:
            acknowledged=con.execute('''SELECT id FROM accounting_review_acknowledgements
                WHERE validation_id=? AND farmer_id=?''',(latest['id'],user['id'])).fetchone() is not None
    return {'job_id':job_id,'latest_validation_id':latest['id'] if latest else None,
            'latest_validation_acknowledged':acknowledged,'status':job['status'],
            'tax_approved':False,'ready_for_external_api':False,'sent':False,'issued':False}

# ETAP 18: polityka pośrednictwa. Nie generujemy faktur sprzedażowych rolników.
from backend.marketplace_policy import POLICY

@app.get('/marketplace/accounting-policy')
def marketplace_accounting_policy():
    """Jawne zasady odpowiedzialności za dokumentowanie sprzedaży."""
    return POLICY.copy()

# ETAP 19: prywatny podgląd rozliczenia; bez rejestrowania płatności i wypłat.
from backend.settlement_preview import calculate as calculate_settlement_preview

@app.get('/marketplace/orders/{order_id}/settlement-preview')
def order_settlement_preview(order_id: int, rate_basis_points: int = 500, user=Depends(current_user)):
    """Wyłącznie sprzedawca danego zamówienia; nie oznacza wpłaty klienta."""
    require(user, 'rolnik')
    if not 0 <= rate_basis_points <= 10000:
        raise HTTPException(422, 'Stawka prowizji poza zakresem')
    with db() as con:
        row = con.execute('SELECT id,farmer_id,subtotal_grosze,delivery_grosze FROM orders WHERE id=? AND farmer_id=?',
                          (order_id, user['id'])).fetchone()
    if row is None:
        raise HTTPException(404, 'Nie znaleziono zamówienia')
    result = calculate_settlement_preview(row['subtotal_grosze'], row['delivery_grosze'], rate_basis_points)
    return {'order_id': row['id'], **result, 'operator_fees_included': False,
            'notice': 'Symulacja bez pobrania płatności, wypłaty i dokumentu podatkowego.'}

# Etap 21: trwały dziennik symulowanych płatności. Wyłącznie lokalnie/testowo.
from backend.payment_store import SCHEMA_SQLITE, get_payment, create_payment, persist_event, public_payment

if not DATABASE_URL:
    with db() as _payment_con:
        _payment_con.executescript(SCHEMA_SQLITE)

class TestPaymentEventIn(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    event_type: Literal['payment_success_test','payment_failed_test',
        'delivery_failed_by_courier_test','order_completed_test','weekly_payout_test']

@app.get('/test/payments/{order_id}')
def get_payment_test(order_id: int, user=Depends(current_user)):
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja wyłączona')
    with db() as con:
        order = con.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
        if not order or user['id'] not in (order['buyer_id'], order['farmer_id']):
            raise HTTPException(404, 'Brak zamówienia')
        payment = get_payment(con, order_id)
        return public_payment(payment) if payment else {'order_id':order_id,'state':'not_initialized_test'}

@app.post('/test/payments/{order_id}/events')
def post_payment_test(order_id: int, payload: TestPaymentEventIn, user=Depends(current_user), authorization: str | None = Header(default=None)):
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja wyłączona')
    if not payload.event_id.strip():
        raise HTTPException(422, 'Nieprawidłowy identyfikator zdarzenia')
    # Caller-supplied keys must never reserve an internal refund event ID
    # or collide with events submitted for another customer's order.
    event_key = f'api:{order_id}:' + hashlib.sha256(payload.event_id.encode('utf-8')).hexdigest()
    # Sesja jest ponownie sprawdzana w transakcji zapisu PostgreSQL.
    # SQLite pozostaje lokalną ścieżką developerską.
    with order_write_db(user, authorization, ('klient', 'rolnik')) as con:
        order = con.execute('SELECT * FROM orders WHERE id=?' + (' FOR UPDATE' if DATABASE_URL else ''), (order_id,)).fetchone()
        if not order:
            raise HTTPException(404, 'Brak zamówienia')
        # Symulowane potwierdzenie płatności może wykonać kupujący, pozostałe operacje rolnik.
        if payload.event_type.startswith('payment_'):
            authorized = user['id'] == order['buyer_id']
        else:
            authorized = user['id'] == order['farmer_id']
        if not authorized:
            raise HTTPException(403, 'Brak uprawnień')
        if payload.event_type.startswith('payment_') and order['status'] != 'oczekuje_na_platnosc_testowa':
            raise HTTPException(409, 'Nie można rejestrować płatności dla zamkniętego zamówienia')
        if payload.event_type.startswith('payment_') and payment_deadline_passed(con, order_id, now=datetime.now(timezone.utc)):
            existing = get_payment(con, order_id)
            # A retry of an already committed event never creates a new payment.
            previous = con.execute('SELECT event_type FROM payment_simulation_events WHERE event_id=?', (event_key,)).fetchone()
            if existing is None or previous is None or previous['event_type'] != payload.event_type:
                raise HTTPException(409, 'Upłynął termin rezerwacji; odśwież zamówienia')
        if payload.event_type == 'order_completed_test' and order['status'] != 'odebrane':
            raise HTTPException(409, 'Zamówienie nie zostało odebrane')
        if payload.event_type == 'delivery_failed_by_courier_test':
            if con.execute('SELECT 1 FROM shipment_order_links WHERE order_id=?', (order_id,)).fetchone():
                raise HTTPException(409, 'Zwróć całą przesyłkę, nie pojedynczy produkt')
            if order['fulfillment'] != 'dostawa':
                raise HTTPException(409, 'To nie jest zamówienie z dostawą')
            # Nie wolno symulować zwrotu za nieudaną dostawę przed jej
            # rozpoczęciem ani po potwierdzonym odbiorze PIN-em.
            if order['status'] != 'w_drodze_testowo':
                # Idempotent retry of the SAME refund event is safe after closure.
                previous = con.execute('SELECT order_id,event_type FROM payment_simulation_events WHERE event_id=?',
                                       (event_key,)).fetchone()
                if not (order['status'] == 'nieudana_dostawa_testowo' and previous
                        and previous['order_id'] == order_id
                        and previous['event_type'] == payload.event_type):
                    raise HTTPException(409, 'Zwrot za nieudaną dostawę tylko w trakcie dostawy')
        if payload.event_type == 'weekly_payout_test' and order['status'] != 'odebrane':
            raise HTTPException(409, 'Wypłata wyłącznie po odbiorze')
        try:
            payment = create_payment(con, order)
            from backend.payment_store import validate_order_refund
            validate_order_refund(con, payment, order)
            updated = persist_event(con, payment, event_key, payload.event_type,
                                    datetime.now(timezone.utc).isoformat())
            if payload.event_type == 'delivery_failed_by_courier_test' and order['status'] == 'w_drodze_testowo':
                # Revoke courier access to the address in the same transaction as the refund.
                require_transition(order['fulfillment'], order['status'], 'nieudana_dostawa_testowo')
                con.execute('UPDATE orders SET status=? WHERE id=?', ('nieudana_dostawa_testowo', order_id))
                record_order_event(con, order_id, user['id'], 'courier_delivery_failed_test',
                                   order['status'], 'nieudana_dostawa_testowo')
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return public_payment(updated)

# Etap 22: raporty i podgląd tygodniowych wypłat, wyłącznie symulacje.
from backend.payout_reports import seller_report, next_weekly_date

@app.get('/test/farmers/me/payout-report')
def payout_report_test(user=Depends(current_user)):
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja wyłączona')
    if user['role'] != 'rolnik':
        raise HTTPException(403, 'Tylko dla rolnika')
    with db() as con:
        report = seller_report(con, user['id'])
    report['next_weekly_payout_date'] = next_weekly_date(datetime.now(timezone.utc).date()).isoformat()
    report['notice'] = 'Podgląd testowy. Nie wykonano przelewu ani nie uruchomiono harmonogramu.'
    return report

# Etap 23: trwałe plany tygodniowych wypłat, BEZ wykonywania przelewów.
from backend.payout_batches import SCHEMA_SQLITE as PAYOUT_PLAN_SCHEMA, create_plan, get_plan

if not DATABASE_URL:
    with db() as _plan_con:
        _plan_con.executescript(PAYOUT_PLAN_SCHEMA)

@app.get('/test/farmers/me/payout-plans/{payout_date}')
def get_payout_plan_test(payout_date: str, user=Depends(current_user)):
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja wyłączona')
    require(user, 'rolnik')
    try:
        parsed = datetime.strptime(payout_date, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(422, 'Nieprawidłowa data')
    if parsed.weekday() != 0:
        raise HTTPException(422, 'Plan dotyczy poniedziałku')
    with db() as con:
        return get_plan(con,user['id'],payout_date) or {'status':'not_created_test','payout_date':payout_date}

@app.post('/test/farmers/me/payout-plans')
def create_payout_plan_test(user=Depends(current_user), authorization: str | None = Header(default=None)):
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja wyłączona')
    require(user, 'rolnik')
    today = datetime.now(timezone.utc).date()
    payout_date = next_weekly_date(today).isoformat()
    with order_write_db(user, authorization, ('admin',) if user['role'] == 'admin' else ('rolnik',)) as con:
        if DATABASE_URL:
            # Lock farmer row to serialize concurrent planning for this farmer.
            con.execute('SELECT id FROM users WHERE id=? FOR UPDATE',(user['id'],)).fetchone()
        result = create_plan(con,user['id'],payout_date,datetime.now(timezone.utc).isoformat())
    return result

# Etap 24: weryfikacja aktualności planu, bez modyfikacji i bez wypłat.
from backend.payout_reconciliation import reconcile_plan

@app.get('/test/farmers/me/payout-plans/{payout_date}/reconciliation')
def payout_plan_reconciliation_test(payout_date: str, user=Depends(current_user)):
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja wyłączona')
    require(user, 'rolnik')
    try:
        parsed = datetime.strptime(payout_date, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(422, 'Nieprawidłowa data')
    if parsed.weekday() != 0:
        raise HTTPException(422, 'Plan dotyczy poniedziałku')
    with db() as con:
        result = reconcile_plan(con, user['id'], payout_date)
    if result is None:
        raise HTTPException(404, 'Nie znaleziono planu')
    return result

# Etap 25: atomowe rezerwacje testowe; bez przelewów i bez operatora płatności.
from backend.payout_reservations import SCHEMA_SQLITE as PAYOUT_RESERVATION_SCHEMA, reserve_plan

if not DATABASE_URL:
    with db() as _reserve_con:
        _reserve_con.executescript(PAYOUT_RESERVATION_SCHEMA)

@app.post('/test/farmers/me/payout-plans/{payout_date}/reserve')
def reserve_payout_plan_test(payout_date: str, user=Depends(current_user), authorization: str | None = Header(default=None)):
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja wyłączona')
    require(user, 'rolnik')
    try:
        parsed = datetime.strptime(payout_date, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(422, 'Nieprawidłowa data')
    if parsed.weekday() != 0:
        raise HTTPException(422, 'Plan dotyczy poniedziałku')
    with order_write_db(user, authorization, ('admin',) if user['role'] == 'admin' else ('rolnik',)) as con:
        if DATABASE_URL:
            con.execute('SELECT id FROM users WHERE id=? FOR UPDATE', (user['id'],)).fetchone()
        try:
            return reserve_plan(con,user['id'],payout_date,datetime.now(timezone.utc).isoformat())
        except ValueError as exc:
            raise HTTPException(409,str(exc))


# Etap 26: ponowna kontrola i anulowanie rezerwacji testowych.
from backend.payout_reservation_review import review_reservation, cancel_reservation

def _validate_payout_date(value):
    try:
        parsed = datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(422, 'Nieprawidłowa data')
    if parsed.weekday() != 0:
        raise HTTPException(422, 'Plan dotyczy poniedziałku')

@app.get('/test/farmers/me/payout-plans/{payout_date}/reservation-review')
def reservation_review_test(payout_date: str, user=Depends(current_user)):
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja wyłączona')
    require(user, 'rolnik')
    _validate_payout_date(payout_date)
    with db() as con:
        report=review_reservation(con,user['id'],payout_date)
    if report is None:
        raise HTTPException(404, 'Nie znaleziono rezerwacji')
    return report

@app.post('/test/farmers/me/payout-plans/{payout_date}/cancel-reservation')
def cancel_reservation_test(payout_date: str, user=Depends(current_user), authorization: str | None = Header(default=None)):
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja wyłączona')
    require(user, 'rolnik')
    _validate_payout_date(payout_date)
    with order_write_db(user, authorization, ('admin',) if user['role'] == 'admin' else ('rolnik',)) as con:
        if DATABASE_URL:
            con.execute('SELECT id FROM users WHERE id=? FOR UPDATE',(user['id'],)).fetchone()
        try:
            return cancel_reservation(con,user['id'],payout_date)
        except ValueError as exc:
            raise HTTPException(404,str(exc))

# Etap 27: jawnie uruchamiana automatyczna kontrola wszystkich rezerwacji rolnika.
# Brak schedulera i brak dostępu do prawdziwych środków.
from backend.payout_auto_review import invalidate_stale_reservations

@app.post('/test/farmers/me/payout-reservations/reconcile-all')
def reconcile_all_payout_reservations_test(user=Depends(current_user), authorization: str | None = Header(default=None)):
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja wyłączona')
    require(user, 'rolnik')
    with order_write_db(user, authorization, ('admin',) if user['role'] == 'admin' else ('rolnik',)) as con:
        if DATABASE_URL:
            con.execute('SELECT id FROM users WHERE id=? FOR UPDATE', (user['id'],)).fetchone()
        return invalidate_stale_reservations(con, user['id'])

# Etap 28: ręczne uruchomienie poniedziałkowego przebiegu przez administratora.
# To nie jest automatyczny scheduler, nie rezerwuje i nie wypłaca pieniędzy.
from backend.payout_scheduler import SCHEMA_SQLITE as PAYOUT_SCHEDULE_SCHEMA, prepare_weekly_run

if not DATABASE_URL:
    with db() as _schedule_con:
        _schedule_con.executescript(PAYOUT_SCHEDULE_SCHEMA)

@app.post('/test/admin/payout-schedule/run')
def run_payout_schedule_test(user=Depends(current_user), authorization: str | None = Header(default=None)):
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja wyłączona')
    require(user, 'admin')
    today = datetime.now(timezone.utc).date()
    if today.weekday() != 0:
        raise HTTPException(409, 'Ręczny przebieg dozwolony wyłącznie w poniedziałek (UTC)')
    with order_write_db(user, authorization, ('admin',) if user['role'] == 'admin' else ('rolnik',)) as con:
        if DATABASE_URL:
            # Single global lock to serialize concurrent administrator runs.
            con.execute('SELECT id FROM users WHERE id=? FOR UPDATE', (user['id'],)).fetchone()
        return prepare_weekly_run(con, today.isoformat(), datetime.now(timezone.utc).isoformat())


# Etap 30: wewnętrzny raport operacyjny prowizji — tylko płatności TESTOWE.
from backend.platform_reports import monthly_platform_report, validate_month

@app.get('/test/admin/finance/monthly/{month}')
def admin_monthly_finance_test(month: str, user=Depends(current_user)):
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja wyłączona')
    require(user, 'admin')
    try:
        validate_month(month)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    with db() as con:
        return monthly_platform_report(con, month)

# Etap 31: administracyjny eksport raportu operacyjnego TEST do CSV.
from fastapi.responses import Response
from backend.finance_export import export_monthly_csv

@app.get('/test/admin/finance/monthly/{month}/export.csv')
def admin_monthly_finance_csv_test(month: str, user=Depends(current_user)):
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja wyłączona')
    require(user, 'admin')
    try:
        validate_month(month)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    with db() as con:
        content = export_monthly_csv(con, month)
    return Response(content=content, media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename="wiejskapaka-test-{month}.csv"',
                             'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})

# Pakiet 1/5: ręczne uzgadnianie danych testowych, bez dostępu do PSP.
from backend.psp_reconciliation import reconcile_test_payments

@app.post('/test/admin/finance/reconcile')
def reconcile_test_finance(entries: list[dict], user=Depends(current_user), authorization: str | None = Header(default=None)):
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1':
        raise HTTPException(404, 'Symulacja wyłączona')
    require(user, 'admin')
    try:
        with order_write_db(user, authorization, ('admin',) if user['role'] == 'admin' else ('rolnik',)) as con:
            return reconcile_test_payments(con, entries)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


# Pakiet 3/5: weryfikacja sprzedawców bez gromadzenia PESEL w bazie developerskiej.
from backend.seller_compliance import (
    create_compliance_tables, seller_compliance_status, acknowledge_seller_rules,
    review_seller_account, seller_review_queue,
)

if not DATABASE_URL:
    with db() as _compliance_connection:
        create_compliance_tables(_compliance_connection)

class SellerRulesAcknowledgement(BaseModel):
    rules_version: Literal['2026-10-draft']
    accepted: Literal[True]

class SellerReview(BaseModel):
    expected_rules_version: str | None = Field(default=None, min_length=1, max_length=80)
    expected_review_status: Literal['pending', 'approved', 'needs_information', 'rejected'] | None = None
    expected_reviewed_at: str | None = Field(default=None, max_length=80)
    decision: Literal['approved', 'needs_information', 'rejected']
    reason: str = Field(min_length=3, max_length=500)

@app.get('/farmers/me/compliance')
def my_seller_compliance(user=Depends(current_user)):
    require(user, 'rolnik')
    with db() as con:
        return seller_compliance_status(con, user['id'])

@app.post('/farmers/me/compliance/acknowledge')
def acknowledge_compliance(payload: SellerRulesAcknowledgement, user=Depends(current_user), authorization: str | None = Header(default=None)):
    require(user, 'rolnik')
    with order_write_db(user, authorization, ('rolnik',)) as con:
        acknowledge_seller_rules(con, user['id'], payload.rules_version)
        return seller_compliance_status(con, user['id'])

@app.get('/admin/farmers/compliance-queue')
def admin_seller_compliance_queue(status: str | None = None, limit: int = 20,
                                   offset: int = 0, user=Depends(current_user)):
    require(user, 'admin')
    with db() as con:
        try:
            return seller_review_queue(con, status, limit, offset)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

@app.post('/admin/farmers/{farmer_id}/compliance/review')
def review_farmer_compliance(farmer_id: int, payload: SellerReview, user=Depends(current_user), authorization: str | None = Header(default=None)):
    require(user, 'admin')
    with order_write_db(user, authorization, ('admin',)) as con:
        farmer = con.execute('SELECT id FROM users WHERE id=? AND role=?', (farmer_id, 'rolnik')).fetchone()
        if not farmer:
            raise HTTPException(404, 'Nie znaleziono rolnika')
        try:
            expected = None
            if {'expected_rules_version', 'expected_review_status', 'expected_reviewed_at'} & payload.model_fields_set:
                if payload.expected_rules_version is None or payload.expected_review_status is None or 'expected_reviewed_at' not in payload.model_fields_set:
                    raise ValueError('Niepełny stan profilu. Odśwież kolejkę.')
                expected = {'rules_version': payload.expected_rules_version,
                            'review_status': payload.expected_review_status,
                            'reviewed_at': payload.expected_reviewed_at}
            review_seller_account(con, farmer_id, user['id'], payload.decision, payload.reason, expected=expected, postgres=bool(DATABASE_URL))
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return seller_compliance_status(con, farmer_id)

@app.get('/couriers/me/active-addresses')
def courier_active_addresses(user=Depends(current_user), authorization: str | None = Header(default=None)):
    """Addresses only for authenticated couriers with an active assignment."""
    require(user, 'dostawca')
    if DATABASE_URL:
        from backend.pg_adapter import postgres_verified_db
        from backend.neon_order_access import courier_active_delivery_addresses
        from backend.neon_session_bridge import AuthenticationFailed
        try:
            with postgres_verified_db(DATABASE_URL, authorization) as (con, actor_id):
                from backend.neon_auth_policy import actor_role
                if not actor_role(con, actor_id, ('dostawca',)):
                    raise HTTPException(403, 'Brak uprawnień')
                return [dict(row) for row in courier_active_delivery_addresses(con, actor_id)]
        except AuthenticationFailed:
            raise HTTPException(401, 'Sesja nieważna')
    with purchase_record_read_db(user,authorization,('dostawca',)) as con:
        rows = con.execute("""SELECT o.id AS order_id,
                loc.delivery_city, loc.delivery_street, loc.delivery_postal_code
            FROM orders o
            JOIN delivery_assignments a ON a.order_id=o.id
            JOIN order_locations loc ON loc.order_id=o.id
            WHERE a.courier_id=?
              AND o.fulfillment='dostawa'
              AND o.status='w_drodze_testowo'
              AND o.pin_used=0
              AND o.confirmed_at IS NULL
            ORDER BY o.id DESC""", (user['id'],)).fetchall()
    return [dict(row) for row in rows]


if not DATABASE_URL:
    from backend.inventory_reservations import SCHEMA_SQLITE as HOLD_SCHEMA
    with db() as _hold_con:
        _hold_con.executescript(HOLD_SCHEMA)


class NearbySearchIn(BaseModel):
    latitude_e6: int = Field(strict=True, ge=-90_000_000, le=90_000_000)
    longitude_e6: int = Field(strict=True, ge=-180_000_000, le=180_000_000)
    radius_m: int = Field(default=1000, strict=True)
    q: CleanText = Field(default='',max_length=120)
    limit: int = Field(default=24,strict=True,ge=1,le=100)
    offset: int = Field(default=0,strict=True,ge=0,le=10000)
    min_price_grosze: int | None = Field(default=None,strict=True,ge=0,le=100_000_000)
    max_price_grosze: int | None = Field(default=None,strict=True,ge=0,le=100_000_000)

    @field_validator('radius_m')
    @classmethod
    def allowed_radius(cls,value):
        from backend.local_marketplace import RADII_M
        if value not in RADII_M:
            raise ValueError('Dozwolone promienie: 100, 500, 1000 i 5000 m')
        return value

    @model_validator(mode='after')
    def price_range(self):
        if self.min_price_grosze is not None and self.max_price_grosze is not None and self.min_price_grosze>self.max_price_grosze:
            raise ValueError('Cena minimalna nie może przekraczać maksymalnej')
        return self


@app.post('/marketplace/nearby')
def search_nearby(payload:NearbySearchIn):
    from backend.local_marketplace import nearby_offers
    with db() as con:
        result = nearby_offers(con,**payload.model_dump())
        if product_unit_storage.enabled():
            for offer in result['items']:
                offer['product'] = product_unit_storage.enrich_product(con, offer['product'])
        return result


if not DATABASE_URL and product_unit_storage.enabled():
    with db() as _unit_con:
        _unit_con.executescript(product_unit_storage.SCHEMA_SQLITE)

if not DATABASE_URL:
    from backend.local_marketplace import SCHEMA_SQLITE as LOCAL_MARKET_SCHEMA, refresh_product_index
    with db() as _local_market_con:
        _local_market_con.executescript(LOCAL_MARKET_SCHEMA)
        refresh_product_index(_local_market_con)


if not DATABASE_URL:
    from backend.purchase_records import SCHEMA_SQLITE as PURCHASE_RECORD_SCHEMA
    with db() as _record_con:
        _record_con.executescript(PURCHASE_RECORD_SCHEMA)


@contextmanager
def purchase_record_read_db(user,authorization,allowed_roles):
    """Authorize private records inside the same snapshot as their data."""
    if not DATABASE_URL:
        # Keep private reads in a consistent read snapshot without a write lock.
        with db() as con:
            con.execute('BEGIN')
            authorize_transaction(con,user,authorization,allowed_roles)
            yield con
    else:
        with order_write_db(user,authorization,allowed_roles) as con:
            yield con


@app.get('/orders/{order_id}/purchase-record')
def get_order_purchase_record(order_id:int,user=Depends(current_user),authorization: str | None = Header(default=None)):
    if user['role'] not in ('klient','rolnik'):
        raise HTTPException(403,'Brak uprawnień')
    with purchase_record_read_db(user,authorization,('klient','rolnik')) as con:
        owner_key='buyer_id' if user['role']=='klient' else 'farmer_id'
        order=con.execute('SELECT * FROM orders WHERE id=? AND '+owner_key+'=?'+(' FOR SHARE' if DATABASE_URL else ''),(order_id,user['id'])).fetchone()
        if order is None or order[owner_key]!=user['id']:
            raise HTTPException(404,'Nie znaleziono zamówienia')
        from backend.purchase_records import order_record
        try:return order_record(con,order)
        except ValueError as exc:raise HTTPException(409,str(exc)) from exc


@app.get('/shipments/{shipment_id}/purchase-record')
def get_shipment_purchase_record(shipment_id:str,user=Depends(current_user),authorization: str | None = Header(default=None)):
    if user['role'] not in ('klient','rolnik'):
        raise HTTPException(403,'Brak uprawnień')
    with purchase_record_read_db(user,authorization,('klient','rolnik')) as con:
        owner_key='buyer_id' if user['role']=='klient' else 'farmer_id'
        shipment=con.execute('SELECT * FROM shipment_groups WHERE id=? AND '+owner_key+'=?'+(' FOR SHARE' if DATABASE_URL else ''),(shipment_id,user['id'])).fetchone()
        if shipment is None or shipment[owner_key]!=user['id']:
            raise HTTPException(404,'Nie znaleziono przesyłki')
        orders=con.execute('SELECT o.* FROM orders o JOIN shipment_order_links l ON l.order_id=o.id WHERE l.shipment_id=? ORDER BY o.id'+(' FOR SHARE OF o' if DATABASE_URL else ''),(shipment_id,)).fetchall()
        if not orders or any(o['buyer_id']!=shipment['buyer_id'] or o['farmer_id']!=shipment['farmer_id'] or o['fulfillment']!=shipment['fulfillment'] for o in orders):
            raise HTTPException(409,'Przesyłka wymaga weryfikacji zgodności')
        from backend.purchase_records import order_record
        try:items=[order_record(con,o) for o in orders]
        except ValueError as exc:raise HTTPException(409,str(exc)) from exc
        complete=all(i['original_available'] for i in items)
        original=None
        if complete:
            products=sum(i['original']['subtotal_grosze'] for i in items)
            delivery=sum(i['original']['delivery_grosze'] for i in items)
            total=sum(i['original']['total_grosze'] for i in items)
            if delivery!=shipment['delivery_grosze'] or products+delivery!=total or sum(i['original']['delivery_grosze']>0 for i in items)>1:
                raise HTTPException(409,'Niezgodna opłata przesyłki; wymagany przegląd')
            if shipment['fulfillment']=='odbior' and len({json.dumps(i['original']['pickup_point'],sort_keys=True) for i in items})!=1:
                raise HTTPException(409,'Niezgodne miejsce odbioru przesyłki; wymagany przegląd')
            original={'products_grosze':products,'delivery_grosze':delivery,'total_grosze':total}
        return {'shipment_id':shipment_id,'mode':'test','original_available':complete,'original':original,'orders':items,
                'notice':'Zapis testowy, bez faktury i bez potwierdzenia rzeczywistej płatności.'}


@app.get('/admin/orders/purchase-record-audit')
def audit_order_purchase_records(user=Depends(current_user),authorization: str | None = Header(default=None)):
    require(user,'admin')
    with purchase_record_read_db(user,authorization,('admin',)) as con:
        from backend.purchase_records import audit_records
        return audit_records(con)


class RecoverPinIn(BaseModel):
    model_config = {'extra':'forbid'}
    password: str = Field(min_length=1,max_length=256)


def recover_purchase_pin(payload,user,authorization,*,order_id=None,shipment_id=None):
    from backend.pin_recovery import recover, RecoveryError
    require(user,'klient')
    denial = None
    with order_write_db(user,authorization,('klient',)) as con:
        lock_buyer_operation(con,user['id'])
        authorize_local_transaction(con,user,authorization,('klient',))
        try:
            result = recover(con,CHECKOUT_VAULT,ph,user['id'],payload.password,
                             order_id=order_id,shipment_id=shipment_id,postgres=bool(DATABASE_URL))
        except RecoveryError as exc:
            # Commit the rate counter even for a wrong password or unavailable PIN.
            denial = exc
    if denial is not None:raise HTTPException(denial.status,str(denial),headers=denial.headers)
    return result


@app.post('/orders/{order_id}/recover-pin-test')
def recover_order_pin(order_id:int,payload:RecoverPinIn,user=Depends(current_user),authorization: str | None=Header(default=None)):
    return recover_purchase_pin(payload,user,authorization,order_id=order_id)


@app.post('/shipments/{shipment_id}/recover-pin-test')
def recover_shipment_pin(shipment_id:str,payload:RecoverPinIn,user=Depends(current_user),authorization: str | None=Header(default=None)):
    return recover_purchase_pin(payload,user,authorization,shipment_id=shipment_id)


from backend.account_security import SCHEMA_SQLITE as ACCOUNT_SECURITY_SCHEMA
if not DATABASE_URL:
    with db() as _account_con:_account_con.executescript(ACCOUNT_SECURITY_SCHEMA)
with db() as _account_con:
    _account_con.execute('SELECT user_id,attempts,window_started_at FROM password_change_access LIMIT 0')


class ChangePasswordIn(BaseModel):
    model_config={'extra':'forbid'}
    current_password: str = Field(min_length=1,max_length=256)
    new_password: str = Field(min_length=12,max_length=256)


@app.post('/auth/change-password')
def change_account_password(payload:ChangePasswordIn,user=Depends(current_user),authorization: str | None=Header(default=None)):
    from backend.account_security import change_password,AccountChangeError
    denial=None
    with account_session_db(user,authorization) as con:
        try:result=change_password(con,ph,user['id'],payload.current_password,payload.new_password)
        except AccountChangeError as exc:denial=exc
    if denial is not None:raise HTTPException(denial.status,str(denial),headers=denial.headers)
    return result


# Demo-only password reset: never silently enable a local mailbox on PostgreSQL.
from backend import password_reset as reset_service
RESET_TEST_ENABLED = os.environ.get('WP_ENABLE_TEST_PASSWORD_RESET') == '1' and (
    not DATABASE_URL or reset_service.postgres_demo_reset_allowed(os.environ, DATABASE_URL))
RESET_OUTBOX = None
if RESET_TEST_ENABLED:
    _reset_folder = os.environ.get('WP_TEST_RESET_OUTBOX', '')
    if not _reset_folder:
        raise RuntimeError('Testowe odzyskiwanie hasła wymaga prywatnej skrzynki lokalnej')
    if DATABASE_URL:
        _reset_path = Path(_reset_folder)
        if not _reset_path.is_absolute() or _reset_path.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
            raise RuntimeError('Testowa skrzynka PostgreSQL musi byc poza projektem')
    RESET_OUTBOX = reset_service.prepare_outbox(_reset_folder)
    if not DATABASE_URL:
        with db() as _reset_con:
            _reset_con.executescript(reset_service.SCHEMA_SQLITE)


class RequestPasswordResetIn(BaseModel):
    model_config = {'extra': 'forbid'}
    email: CleanText = Field(min_length=5, max_length=254)


class ConfirmPasswordResetIn(BaseModel):
    model_config = {'extra': 'forbid'}
    token: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


# Test-only encrypted outbox. No SMTP client or worker is started by the API.
from backend import reset_mail_queue, reset_http_config
QUEUED_RESET_KEYS = reset_http_config.load_config(os.environ, DATABASE_URL)
if QUEUED_RESET_KEYS is not None:
    with db() as _queue_con:
        if not DATABASE_URL:
            _queue_con.executescript(reset_service.SCHEMA_SQLITE + reset_mail_queue.SCHEMA)
        # PostgreSQL must already have the controlled migrations applied.
        _queue_con.execute('SELECT token_hash FROM password_reset_tokens LIMIT 0')
        _queue_con.execute('SELECT bucket FROM password_reset_limits LIMIT 0')
        _queue_con.execute('SELECT id,payload,key_id FROM reset_mail_queue LIMIT 0')


class QueuedPasswordResetIn(RequestPasswordResetIn):
    @field_validator('email')
    @classmethod
    def mailbox(cls, value):
        from backend.smtp_reset_transport import address
        return address(value.strip().lower())


@app.post('/auth/password-reset/request', status_code=202)
def request_queued_password_reset(payload: QueuedPasswordResetIn):
    if QUEUED_RESET_KEYS is None:
        raise HTTPException(404, 'Odzyskiwanie hasła jest niedostępne.')
    with db() as con:
        if not DATABASE_URL:
            con.execute('BEGIN IMMEDIATE')
        reset_mail_queue.issue(con, QUEUED_RESET_KEYS, payload.email,
                              now=int(datetime.now(timezone.utc).timestamp()))
    return {'message': reset_service.NOTICE}


@app.post('/auth/password-reset/confirm')
def confirm_queued_password_reset(payload: ConfirmPasswordResetIn):
    if QUEUED_RESET_KEYS is None:
        raise HTTPException(404, 'Odzyskiwanie hasła jest niedostępne.')
    with db() as con:
        if not DATABASE_URL:
            con.execute('BEGIN IMMEDIATE')
        outcome = reset_service.consume(con, ph, payload.token, payload.new_password)
    if outcome == 429:
        raise HTTPException(429, 'Zbyt wiele prób. Spróbuj później.', headers={'Retry-After': '900'})
    if outcome != 200:
        raise HTTPException(400, reset_service.INVALID)
    return {'changed': True, 'reauthentication_required': True}


@app.get('/auth/password-reset-test/options')
def password_reset_options():
    return {'enabled': RESET_TEST_ENABLED, 'test_only': True}


@app.post('/auth/password-reset-test/request', status_code=202)
def request_test_password_reset(payload: RequestPasswordResetIn):
    if not RESET_TEST_ENABLED:
        raise HTTPException(404, 'Odzyskiwanie hasła jest niedostępne.')
    message_file = None
    try:
        with db() as con:
            if not DATABASE_URL:
                con.execute('BEGIN IMMEDIATE')
            reset_token = reset_service.issue(con, payload.email)
            if reset_token:
                message_file = reset_service.deliver_demo(RESET_OUTBOX, payload.email, reset_token)
    except Exception:
        if message_file is not None:
            message_file.unlink(missing_ok=True)
        raise
    return {'message': reset_service.NOTICE}


@app.post('/auth/password-reset-test/confirm')
def confirm_test_password_reset(payload: ConfirmPasswordResetIn):
    if not RESET_TEST_ENABLED:
        raise HTTPException(404, 'Odzyskiwanie hasła jest niedostępne.')
    with db() as con:
        if not DATABASE_URL:
            con.execute('BEGIN IMMEDIATE')
        outcome = reset_service.consume(con, ph, payload.token, payload.new_password)
    if outcome == 429:
        raise HTTPException(429, 'Zbyt wiele prób. Spróbuj później.', headers={'Retry-After': '900'})
    if outcome != 200:
        raise HTTPException(400, reset_service.INVALID)
    return {'changed': True, 'reauthentication_required': True}

# Private test-only support cases; explicitly no monetary or order side effects.
from uuid import UUID
from fastapi import Query
from backend import support_cases as support

if not DATABASE_URL:
    with db() as _support_con:
        _support_con.executescript(support.SCHEMA)

class SupportCaseIn(BaseModel):
    model_config={'extra':'forbid'}
    kind: Literal['order','shipment']
    target_id: CleanText = Field(min_length=1,max_length=64)
    category: Literal['product','pickup','delivery','other']
    description: CleanText = Field(min_length=10,max_length=2000)
    request_id: UUID

class SupportReplyIn(BaseModel):
    model_config={'extra':'forbid'}
    message: CleanText = Field(min_length=1,max_length=2000)
    request_id: UUID
    expected_revision: int = Field(strict=True,ge=1,le=2_000_000_000)
    status: Literal['in_review','closed_test'] | None = None


def require_support_test():
    if os.environ.get('WP_ENABLE_TEST_PAYMENTS')!='1':
        raise HTTPException(404,'Obsługa testowych zgłoszeń wyłączona')


@app.get('/test/support/cases')
def list_support_cases(status: Literal['new','in_review','closed_test'] | None = None,
        limit: int = Query(default=20,ge=1,le=50),offset: int = Query(default=0,ge=0,le=10000),user=Depends(current_user)):
    require_support_test()
    try:
        with db() as con:return support.listing(con,user,status=status,limit=limit,offset=offset)
    except support.CaseError as exc:raise HTTPException(exc.status,str(exc)) from exc


@app.post('/test/support/cases',status_code=201)
def create_support_case(body: SupportCaseIn,user=Depends(current_user),authorization: str | None = Header(default=None)):
    require_support_test()
    try:
        with order_write_db(user,authorization,('klient',)) as con:
            return support.create(con,user,body.kind,body.target_id,body.category,body.description,body.request_id.hex,postgres=bool(DATABASE_URL))
    except support.CaseError as exc:raise HTTPException(exc.status,str(exc)) from exc


@app.get('/test/support/cases/{case_id}')
def support_case_detail(case_id: str,before_revision: int | None = Query(default=None,ge=1,le=2_000_000_000),user=Depends(current_user)):
    require_support_test()
    try:
        with db() as con:return support.detail(con,case_id,user,before_revision=before_revision)
    except support.CaseError as exc:raise HTTPException(exc.status,str(exc)) from exc


@app.post('/test/support/cases/{case_id}/replies')
def reply_support_case(case_id: str,body: SupportReplyIn,user=Depends(current_user),authorization: str | None = Header(default=None)):
    require_support_test()
    try:
        with order_write_db(user,authorization,('klient','rolnik','admin')) as con:
            return support.reply(con,case_id,user,body.message,body.request_id.hex,body.expected_revision,body.status,postgres=bool(DATABASE_URL))
    except support.CaseError as exc:raise HTTPException(exc.status,str(exc)) from exc
