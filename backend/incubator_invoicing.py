"""Operator-confirmed platform credits and manual CRM invoice tracking."""

import csv
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Annotated, Literal
from sqlite3 import IntegrityError
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from backend.invoicing import calculate_commission_grosze
from backend.monthly_platform_fees import monthly_fee_summary
from backend.pg_adapter import PgUniqueViolation, gateway_configured

MIGRATION = Path(__file__).resolve().parents[1] / 'database' / 'upgrade_incubator_invoicing.sql'
TABLE = 'incubator_invoice_entries'
WARSAW = ZoneInfo('Europe/Warsaw')
Mode = Literal['test', 'verified']
Kind = Literal['withdrawal_fee', 'pickup_point', 'advertising', 'refund']
Status = Literal['pending', 'issued', 'closed']
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
Grosze = Annotated[int, Field(strict=True, ge=1, le=9_000_000_000_000)]
SERVICES = {
    'withdrawal_fee': 'Prowizja od wypłaty sprzedawcy (5%)',
    'pickup_point': 'Punkt odbioru',
    'advertising': 'Usługa reklamowa',
}
STATE = """CASE
 WHEN invoice_number IS NOT NULL THEN 'issued'
 WHEN absorbs_refund=1 OR refunded_grosze=amount_grosze THEN 'closed'
 ELSE 'pending' END"""
PUBLIC_COLUMNS = """id,mode,kind,original_id,seller_id,buyer_name,buyer_address,buyer_nip,service,
 transaction_id,operator_settlement_id,transaction_on,settled_on,amount_grosze,refunded_grosze,withdrawal_gross_grosze,
 invoice_number,issued_on"""
COLUMNS = f"""{PUBLIC_COLUMNS},({STATE}) AS status,
 COALESCE(invoice_amount_grosze, CASE WHEN kind='refund' AND absorbs_refund=0 THEN -amount_grosze
 WHEN kind='refund' THEN 0 ELSE amount_grosze-refunded_grosze END) AS invoice_grosze"""


class EntryReference(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Mode = 'test'
    transaction_id: Text
    operator_settlement_id: Text
    transaction_on: date
    settled_on: date
    confirmed: Literal[True]

    @field_validator('transaction_id', 'operator_settlement_id')
    @classmethod
    def single_line(cls, value):
        if not value.isprintable():
            raise ValueError('Wpisz tekst w jednym wierszu.')
        return value


class Credit(EntryReference):
    kind: Literal['withdrawal_fee', 'pickup_point', 'advertising']
    seller_id: Annotated[int, Field(strict=True, ge=1, le=9_007_199_254_740_991)] | None = None
    buyer_name: Text
    buyer_address: Text
    buyer_nip: str | None = Field(default=None, pattern=r'^[0-9]{10}$')
    amount_grosze: Grosze
    withdrawal_gross_grosze: Grosze | None = None

    @field_validator('buyer_name', 'buyer_address')
    @classmethod
    def single_line_buyer(cls, value):
        return cls.single_line(value)


class Refund(EntryReference):
    amount_grosze: Grosze


class Issue(BaseModel):
    model_config = ConfigDict(extra='forbid')
    invoice_number: Text
    issued_on: date
    expected_grosze: Annotated[int, Field(strict=True, ge=-9_000_000_000_000, le=9_000_000_000_000)]

    @field_validator('invoice_number')
    @classmethod
    def single_line(cls, value):
        return EntryReference.single_line(value)


def create_sqlite_schema(con):
    schema = MIGRATION.read_text(encoding='utf-8').split('REVOKE ALL', 1)[0]
    con.executescript(schema)


def today():
    return datetime.now(WARSAW).date()


def month_bounds(month):
    try:
        start = date.fromisoformat(month + '-01') if len(month) == 7 else None
        if start is None:
            raise ValueError
        next_month = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
        return start.isoformat(), next_month.isoformat()
    except ValueError:
        raise HTTPException(422, 'Wybierz prawidłowy miesiąc.') from None


def ensure_reference_dates(payload):
    if not date(2000, 1, 1) <= payload.transaction_on <= payload.settled_on <= today():
        raise HTTPException(422, 'Sprawdź datę transakcji i datę rozliczenia.')


def validate_credit(con, payload):
    if payload.kind != 'withdrawal_fee':
        if payload.withdrawal_gross_grosze is not None:
            raise HTTPException(422, 'Kwota wypłaty dotyczy wyłącznie prowizji.')
        validate_seller(con, payload.seller_id)
        return payload.seller_id, None
    gross = payload.withdrawal_gross_grosze
    seller = payload.seller_id
    if payload.mode == 'test':
        withdrawal = con.execute("""SELECT t.gross_grosze,t.fee_grosze,e.user_id,e.created_at AS requested_at,
                r.created_at AS resolved_at
            FROM wallet_preview_terms t JOIN wallet_preview_resolutions r ON r.withdrawal_id=t.withdrawal_id
            JOIN wallet_preview_entries e ON e.id=t.withdrawal_id AND e.user_id=r.user_id
            WHERE t.withdrawal_id=? AND t.owner_role='rolnik' AND t.fee_basis_points=500
                AND e.kind='withdrawal' AND r.state='completed_test'""", (payload.transaction_id,)).fetchone()
        if withdrawal is None:
            raise HTTPException(409, 'Wybierz zakończoną wypłatę testową sprzedawcy.')
        requested_on = datetime.fromtimestamp(withdrawal['requested_at'], WARSAW).date()
        resolved_on = datetime.fromtimestamp(withdrawal['resolved_at'], WARSAW).date()
        if (payload.amount_grosze != withdrawal['fee_grosze'] or payload.transaction_on != requested_on
                or payload.settled_on < resolved_on or gross not in (None, withdrawal['gross_grosze'])
                or seller not in (None, withdrawal['user_id'])):
            raise HTTPException(422, 'Kwota lub daty są niezgodne z zapisem wypłaty testowej.')
        gross, seller = withdrawal['gross_grosze'], withdrawal['user_id']
    if seller is None:
        raise HTTPException(422, 'Wskaż konto sprzedawcy.')
    if payload.mode == 'verified':
        validate_seller(con, seller)
    if gross is None or payload.amount_grosze != calculate_commission_grosze(gross, 500):
        raise HTTPException(422, 'Wpływ musi odpowiadać wyłącznie prowizji 5% od wypłaty.')

    return seller, gross


def validate_seller(con, seller_id):
    if seller_id is not None and con.execute(
        "SELECT 1 FROM users WHERE id=? AND role='rolnik'", (seller_id,)
    ).fetchone() is None:
        raise HTTPException(422, 'Identyfikator nie należy do konta sprzedawcy.')


def insert_entry(con, payload, actor, *, kind, buyer, service, seller_id, gross=None, original_id=None, absorbs_refund=0):
    entry_id = uuid4().hex
    row = con.execute(f"""INSERT INTO {TABLE}
        (id,mode,kind,original_id,seller_id,buyer_name,buyer_address,buyer_nip,service,transaction_id,
         operator_settlement_id,transaction_on,settled_on,withdrawal_gross_grosze,amount_grosze,absorbs_refund,recorded_by,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING RETURNING id""",
        (entry_id, payload.mode, kind, original_id, seller_id, *buyer, service, payload.transaction_id,
         payload.operator_settlement_id, payload.transaction_on.isoformat(), payload.settled_on.isoformat(),
         gross, payload.amount_grosze, absorbs_refund, actor['id'], datetime.now(timezone.utc).isoformat())).fetchone()
    if row is None:
        raise HTTPException(409, 'Ten wpływ lub zwrot znajduje się już w rejestrze.')
    return {'id': entry_id}


def record_refund(con, original_id, payload, actor):
    # One statement locks the original and prevents concurrent refunds from exceeding it.
    original = con.execute(f"""UPDATE {TABLE} SET refunded_grosze=refunded_grosze+?
        WHERE id=? AND mode=? AND kind<>'refund' AND settled_on<=?
          AND refunded_grosze+?<=amount_grosze
        RETURNING seller_id,buyer_name,buyer_address,buyer_nip,service,invoice_number""",
        (payload.amount_grosze, original_id, payload.mode, payload.transaction_on.isoformat(),
         payload.amount_grosze)).fetchone()
    if original is None:
        raise HTTPException(409, 'Brak pasującego wpływu lub zwrot przekracza pozostałą kwotę.')
    return insert_entry(con, payload, actor, kind='refund', original_id=original_id,
                        buyer=(original['buyer_name'], original['buyer_address'], original['buyer_nip']),
                        service='Zwrot: ' + original['service'], seller_id=original['seller_id'], absorbs_refund=int(original['invoice_number'] is None))


def issue_invoice(con, entry_id, payload, actor, verified_enabled):
    row = con.execute(f"""SELECT mode FROM {TABLE} WHERE id=?""",
                      (entry_id,)).fetchone()
    if row is None:
        raise HTTPException(404, 'Nie znaleziono pozycji.')
    ensure_mode(row['mode'], verified_enabled)
    if not date(2000, 1, 1) <= payload.issued_on <= today():
        raise HTTPException(422, 'Podaj prawidłową datę wystawienia dokumentu z CRM.')
    amount = "CASE WHEN kind='refund' THEN -amount_grosze ELSE amount_grosze-refunded_grosze END"
    try:
        saved = con.execute(f"""UPDATE {TABLE}
            SET invoice_number=?,invoice_number_key=?,issued_on=?,issued_by=?,invoice_amount_grosze={amount}
            WHERE id=? AND invoice_number IS NULL AND absorbs_refund=0 AND refunded_grosze<amount_grosze
              AND ({amount})=?
            RETURNING id""",
            (payload.invoice_number, payload.invoice_number.casefold(), payload.issued_on.isoformat(),
             actor['id'], entry_id, payload.expected_grosze)).fetchone()
    except (IntegrityError, PgUniqueViolation):
        raise HTTPException(409, 'Ten numer faktury jest już zapisany.') from None
    if saved is None:
        raise HTTPException(409, 'Kwota lub status pozycji się zmieniły. Odśwież rejestr.')
    return {'id': entry_id}


def ensure_mode(mode, verified_enabled):
    if mode == 'verified' and not verified_enabled:
        raise HTTPException(409, 'Rejestr rzeczywistych wpływów jest wyłączony.')


def filters(mode, month, status, kind, search):
    clauses, args = ['mode=?'], [mode]
    if month:
        start, end = month_bounds(month)
        column = 'issued_on' if status == 'issued' else 'settled_on'
        clauses.append(f'{column}>=? AND {column}<?')
        args += [start, end]
    if status:
        clauses.append(f'({STATE})=?')
        args.append(status)
    if kind:
        clauses.append('kind=?')
        args.append(kind)
    if search.strip():
        value = search.strip().lower().replace('!', '!!').replace('%', '!%').replace('_', '!_')
        fields = ('buyer_name','buyer_address','buyer_nip','transaction_id','operator_settlement_id','invoice_number')
        clauses.append('(' + ' OR '.join(f"LOWER({field}) LIKE ? ESCAPE '!'" for field in fields) + ')')
        args += [f'%{value}%'] * len(fields)
    return ' AND '.join(clauses), tuple(args)


def summary(con, mode, month):
    start, end = month_bounds(month)
    issued = con.execute(f"""SELECT COUNT(*) AS n FROM {TABLE}
        WHERE mode=? AND issued_on>=? AND issued_on<?""", (mode, start, end)).fetchone()['n']
    sums = con.execute(f"""SELECT
        COALESCE(SUM(CASE WHEN e.kind='refund' THEN -e.amount_grosze ELSE e.amount_grosze END),0) AS revenue,
        COALESCE(SUM(CASE WHEN e.kind='withdrawal_fee' THEN e.amount_grosze
            WHEN o.kind='withdrawal_fee' THEN -e.amount_grosze ELSE 0 END),0) AS fees
        FROM {TABLE} e LEFT JOIN {TABLE} o ON e.original_id=o.id
        WHERE e.mode=? AND e.settled_on>=? AND e.settled_on<?""", (mode, start, end)).fetchone()
    return {'issued': issued, 'free_remaining': max(0, 100-issued),
            'extra_cost_grosze': ((max(0, issued-100)+99)//100)*4000,
            'revenue_grosze': str(int(sums['revenue'])), 'commission_grosze': str(int(sums['fees']))}


def select_entries(con, where, args, limit, offset=0):
    return con.execute(f"""SELECT entries.*,original.invoice_number AS original_invoice_number
        FROM (SELECT {COLUMNS} FROM {TABLE} WHERE {where}
              ORDER BY settled_on DESC,id DESC LIMIT ? OFFSET ?) entries
        LEFT JOIN {TABLE} original ON entries.original_id=original.id
        ORDER BY entries.settled_on DESC,entries.id DESC""", (*args, limit, offset)).fetchall()


def csv_export(rows):
    output = StringIO(newline='')
    writer = csv.writer(output, delimiter=';')
    writer.writerow(('Tryb','Status','Nabywca','Adres','NIP','Usługa','Transakcja','Rozliczenie operatora',
                     'Data transakcji','Data rozliczenia','Wpływ lub zwrot (gr)','Kwota do faktury (gr)',
                     'Faktura','Wystawiono','Faktura korygowana','ID oryginału'))
    for row in rows:
        cells = [row[key] for key in ('mode','status','buyer_name','buyer_address','buyer_nip','service',
                  'transaction_id','operator_settlement_id','transaction_on','settled_on','amount_grosze',
                  'invoice_grosze','invoice_number','issued_on','original_invoice_number','original_id')]
        if row['kind'] == 'refund':
            cells[10] = -cells[10]
        writer.writerow(["'" + value if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@'))
                         else value for value in cells])
    return '\ufeff' + output.getvalue()


def install(app, db, admin_db, current_user, environ, database_url):
    enabled = environ.get('WP_ENABLE_INCUBATOR_INVOICING', '0' if database_url else '1') == '1'
    verified_enabled = bool(enabled and database_url and gateway_configured()
                            and environ.get('WP_ENABLE_INCUBATOR_MANUAL_SETTLEMENTS') == '1')
    if enabled and not database_url:
        with db() as con:
            create_sqlite_schema(con)

    def admin(user=Depends(current_user)):
        if user['role'] != 'admin':
            raise HTTPException(403, 'Brak uprawnień.')
        return user

    def access(user=Depends(admin)):
        if not enabled:
            raise HTTPException(404, 'Moduł fakturowania jest wyłączony.')
        return user

    base = '/admin/incubator-invoicing'

    @app.get(base + '/config')
    def config(user=Depends(admin)):
        return {'enabled': enabled, 'verified_enabled': verified_enabled}

    @app.get(base)
    def listing(response: Response, mode: Mode = 'test', month: str = '', status: Status | None = None,
                kind: Kind | None = None, search: str = Query('', max_length=240),
                offset: int = Query(0, ge=0, le=10_000_000), user=Depends(access),
                authorization: str = Header()):
        ensure_mode(mode, verified_enabled)
        selected = month or today().strftime('%Y-%m')
        where, args = filters(mode, month, status, kind, search)
        response.headers['Cache-Control'] = 'no-store'
        with admin_db(user, authorization, ('admin',)) as con:
            items = select_entries(con, where, args, 51, offset)
            totals = summary(con, mode, selected)
        return {'items': [dict(row) for row in items[:50]], 'more': len(items)>50, 'summary': totals}

    @app.get(base + '/seller-summary')
    def seller_summary(response: Response, month: str, mode: Mode = 'test',
                       user=Depends(access), authorization: str = Header()):
        ensure_mode(mode, verified_enabled)
        start, end = month_bounds(month)
        with admin_db(user, authorization, ('admin',)) as con:
            rows = con.execute(f"""SELECT e.id AS source_id,e.seller_id,e.settled_on AS posted_on,
                    COALESCE(o.kind,e.kind) AS kind,
                    CASE WHEN e.kind='refund' THEN -e.amount_grosze ELSE e.amount_grosze END AS amount_grosze
                FROM {TABLE} e LEFT JOIN {TABLE} o ON e.original_id=o.id
                WHERE e.mode=? AND e.settled_on>=? AND e.settled_on<? AND e.seller_id IS NOT NULL""",
                (mode, start, end)).fetchall()
        entries = [dict(row, currency='PLN', kind='seller_withdrawal_fee' if row['kind']=='withdrawal_fee'
                        else row['kind']) for row in rows]
        year, period = map(int, month.split('-'))
        response.headers['Cache-Control'] = 'no-store'
        return {'items': monthly_fee_summary(entries, year, period), 'mode': mode}

    @app.get(base + '/export.csv')
    def export(mode: Mode = 'test', month: str = '', status: Status | None = None, kind: Kind | None = None,
               search: str = Query('', max_length=240), user=Depends(access), authorization: str = Header()):
        ensure_mode(mode, verified_enabled)
        where, args = filters(mode, month, status, kind, search)
        with admin_db(user, authorization, ('admin',)) as con:
            rows = select_entries(con, where, args, 10001)
        if len(rows)>10_000:
            raise HTTPException(422, 'Zawęź filtr przed pobraniem CSV.')
        return Response(csv_export(rows), media_type='text/csv; charset=utf-8',
                        headers={'Cache-Control': 'no-store',
                                 'Content-Disposition': 'attachment; filename="wiejskapaka-twoj-startup.csv"'})

    @app.post(base, status_code=201)
    def credit(payload: Credit, user=Depends(access), authorization: str = Header()):
        ensure_mode(payload.mode, verified_enabled)
        ensure_reference_dates(payload)
        with admin_db(user, authorization, ('admin',)) as con:
            seller, gross = validate_credit(con, payload)
            return insert_entry(con, payload, user, kind=payload.kind, service=SERVICES[payload.kind],
                                buyer=(payload.buyer_name, payload.buyer_address, payload.buyer_nip), seller_id=seller, gross=gross)

    @app.post(base + '/{entry_id}/refund', status_code=201)
    def refund(entry_id: str, payload: Refund, user=Depends(access), authorization: str = Header()):
        ensure_mode(payload.mode, verified_enabled)
        ensure_reference_dates(payload)
        with admin_db(user, authorization, ('admin',)) as con:
            return record_refund(con, entry_id, payload, user)

    @app.post(base + '/{entry_id}/issue')
    def issue(entry_id: str, payload: Issue, user=Depends(access), authorization: str = Header()):
        with admin_db(user, authorization, ('admin',)) as con:
            return issue_invoice(con, entry_id, payload, user, verified_enabled)
