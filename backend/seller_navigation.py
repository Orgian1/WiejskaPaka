"""Account-scoped seller route order with optimistic concurrency across devices."""
import json
from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

SCHEMA = '''CREATE TABLE IF NOT EXISTS seller_navigation (
 user_id INTEGER PRIMARY KEY REFERENCES users(id),
 revision INTEGER NOT NULL DEFAULT 0 CHECK(revision >= 0),
 point_ids TEXT NOT NULL DEFAULT '[]'
)'''


class NavigationIn(BaseModel):
    revision: int = Field(strict=True, ge=0, le=2147483646)
    point_ids: list[int] = Field(max_length=1000)

    @field_validator('point_ids', mode='before')
    @classmethod
    def unique_positive_ids(cls, value):
        if not isinstance(value, list) or any(type(i) is not int or i <= 0 for i in value):
            raise ValueError('Wymagane dodatnie identyfikatory punktów')
        if len(set(value)) != len(value):
            raise ValueError('Punkty nie mogą się powtarzać')
        return value


def ordered_ids(con, user_id, saved):
    owned = [r['id'] for r in con.execute(
        'SELECT id FROM pickup_points WHERE farmer_id=? ORDER BY id', (user_id,)).fetchall()]
    present = set(owned)
    result = [i for i in saved if i in present]
    selected = set(result)
    return result + [i for i in owned if i not in selected]


def install(app, db, write_db, current_user, database_url):
    if not database_url:
        with db() as con:
            con.execute(SCHEMA)

    @app.get('/farmers/me/navigation')
    def get_navigation(user=Depends(current_user), authorization: str | None = Header(default=None)):
        with write_db(user, authorization, ('rolnik',)) as con:
            row = con.execute('SELECT revision,point_ids FROM seller_navigation WHERE user_id=?', (user['id'],)).fetchone()
            return {'revision': row['revision'] if row else 0,
                    'point_ids': ordered_ids(con, user['id'], json.loads(row['point_ids']) if row else [])}

    @app.put('/farmers/me/navigation')
    def save_navigation(payload: NavigationIn, user=Depends(current_user), authorization: str | None = Header(default=None)):
        with write_db(user, authorization, ('rolnik',)) as con:
            ids = ordered_ids(con, user['id'], [])
            if not set(payload.point_ids).issubset(ids):
                raise HTTPException(404, 'Punkt nie należy do tego konta lub już nie istnieje')
            # Initialize once; CAS below also serializes competing first writes on PostgreSQL.
            con.execute("INSERT INTO seller_navigation(user_id,revision,point_ids) VALUES(?,0,'[]') ON CONFLICT(user_id) DO NOTHING", (user['id'],))
            points = ordered_ids(con, user['id'], payload.point_ids)
            changed = con.execute('UPDATE seller_navigation SET point_ids=?,revision=revision+1 WHERE user_id=? AND revision=?',
                                  (json.dumps(points), user['id'], payload.revision))
            if changed.rowcount != 1:
                raise HTTPException(409, 'Kolejność zmieniono na innym urządzeniu. Odśwież listę i spróbuj ponownie.')
            return {'revision': payload.revision+1, 'point_ids': points}
