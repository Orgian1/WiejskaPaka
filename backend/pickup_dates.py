"""Optional seller attendance dates; never reinterpret existing order reservations."""
from datetime import date, datetime, timedelta
import os
from zoneinfo import ZoneInfo

SCHEMA_SQLITE = '''CREATE TABLE IF NOT EXISTS pickup_point_dates (
 point_id INTEGER NOT NULL REFERENCES pickup_points(id) ON DELETE CASCADE,
 attendance_date TEXT NOT NULL,
 PRIMARY KEY(point_id,attendance_date));'''


def enabled():
    return os.environ.get('WP_ENABLE_PICKUP_DATES') == '1'


def today():
    return datetime.now(ZoneInfo('Europe/Warsaw')).date()


def validate(values, *, current=None):
    current = current or today()
    if not isinstance(values,list) or not 1 <= len(values) <= 90:
        raise ValueError('Wybierz od 1 do 90 dat obecności w punkcie')
    result=[]
    for value in values:
        if not isinstance(value,str):
            raise ValueError('Nieprawidłowa data obecności')
        parsed=date.fromisoformat(value)
        if parsed.isoformat()!=value or not current <= parsed <= current+timedelta(days=365):
            raise ValueError('Wybierz daty od dzisiaj do roku naprzód')
        result.append(value)
    if len(set(result))!=len(result):
        raise ValueError('Daty obecności nie mogą się powtarzać')
    return sorted(result)


def read(con, point_id):
    return [row['attendance_date'] for row in con.execute(
        'SELECT attendance_date FROM pickup_point_dates WHERE point_id=? ORDER BY attendance_date',
        (point_id,)).fetchall()]


def replace(con, point_id, values):
    values=validate(values)
    con.execute('DELETE FROM pickup_point_dates WHERE point_id=?',(point_id,))
    for value in values:
        con.execute('INSERT INTO pickup_point_dates(point_id,attendance_date) VALUES(?,?)',(point_id,value))


def enrich(con, row):
    result=dict(row)
    if enabled():
        result['attendance_dates']=[value for value in read(con,row['id']) if value >= today().isoformat()]
    return result
