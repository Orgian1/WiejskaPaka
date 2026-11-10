"""One bounded sanitizer for every published user photo (never store originals)."""
import hashlib
import io
import os
import threading
import warnings

from fastapi import Depends, Header, HTTPException, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 1_000_000
MAX_PRODUCT_BYTES = 500_000
MAX_SOURCE_BYTES = 20_000_000
MAX_PIXELS = 50_000_000
_PROCESSOR = threading.BoundedSemaphore(1)
SCHEMA_SQLITE = '''CREATE TABLE IF NOT EXISTS user_photos (
 kind TEXT NOT NULL CHECK(kind IN ('product','profile','farm')),
 subject_id INTEGER NOT NULL CHECK(subject_id>0),
 owner_id INTEGER NOT NULL REFERENCES users(id),
 data BLOB NOT NULL CHECK(length(data)>0 AND length(data)<=1000000),
 digest TEXT NOT NULL CHECK(length(digest)=64),
 width INTEGER NOT NULL CHECK(width BETWEEN 1 AND 2048),
 height INTEGER NOT NULL CHECK(height BETWEEN 1 AND 2048),
 PRIMARY KEY(kind,subject_id)
);'''


def enabled():
    return os.environ.get('WP_ENABLE_USER_PHOTOS') == '1'


def compress_photo(source, *, max_bytes=None):
    max_bytes = MAX_BYTES if max_bytes is None else max_bytes
    if not source or len(source) > MAX_SOURCE_BYTES:
        raise HTTPException(413, 'Zdjęcie źródłowe musi mieć od 1 bajta do 20 MB.')
    with _PROCESSOR, warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        try:
            with Image.open(io.BytesIO(source), formats=['JPEG', 'PNG', 'WEBP']) as original:
                if original.width * original.height > MAX_PIXELS:
                    raise HTTPException(413, 'Zdjęcie ma za dużo pikseli (maksymalnie 50 mln).')
                if getattr(original, 'n_frames', 1) != 1:
                    raise HTTPException(422, 'Wybierz pojedyncze zdjęcie, bez animacji.')
                original.load()
                oriented = ImageOps.exif_transpose(original)
                oriented.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                # A fresh RGB image discards EXIF/GPS, XMP, ICC and filenames.
                image = Image.new('RGB', oriented.size, 'white')
                rgba = oriented.convert('RGBA')
                image.paste(rgba, mask=rgba.getchannel('A'))
                for _ in range(8):
                    for quality in (90, 80, 70, 60, 45):
                        result = io.BytesIO()
                        image.save(result, 'JPEG', quality=quality, optimize=True)
                        data = result.getvalue()
                        if len(data) <= max_bytes:
                            return data, image.width, image.height
                    image = image.resize((max(1, image.width*3//4), max(1, image.height*3//4)), Image.Resampling.LANCZOS)
        except HTTPException:
            raise
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
                Image.DecompressionBombWarning, Image.DecompressionBombError):
            raise HTTPException(422, 'Nie można odczytać zdjęcia. Wybierz poprawny JPEG, PNG lub WebP.') from None
    raise HTTPException(422, 'Nie udało się zmniejszyć zdjęcia do wymaganego limitu.')


def register_routes(app, db, write_db, current_user):
    def require_enabled():
        if not enabled():
            raise HTTPException(503, 'Dodawanie zdjęć nie zostało jeszcze włączone.')

    def owns(con, kind, subject_id, user):
        if kind not in ('product', 'profile', 'farm') or subject_id < 1:
            raise HTTPException(404, 'Nie znaleziono miejsca na zdjęcie.')
        if kind == 'product':
            row = con.execute('SELECT farmer_id FROM products WHERE id=?', (subject_id,)).fetchone()
            valid = user['role'] == 'rolnik' and row and row['farmer_id'] == user['id']
        else:
            valid = subject_id == user['id'] and (kind == 'profile' or user['role'] == 'rolnik')
        if not valid:
            raise HTTPException(404, 'Nie znaleziono miejsca na zdjęcie.')

    @app.get('/user-photos/config')
    def photo_config():
        return {'enabled': enabled(), 'max_bytes': MAX_BYTES, 'max_product_bytes': MAX_PRODUCT_BYTES, 'max_source_bytes': MAX_SOURCE_BYTES}

    @app.get('/user-photos/{kind}/{subject_id}')
    def photo_read(kind: str, subject_id: int):
        require_enabled()
        if kind not in ('product', 'profile', 'farm') or subject_id < 1:
            raise HTTPException(404, 'Nie znaleziono zdjęcia.')
        with db() as con:
            row = con.execute('SELECT data FROM user_photos WHERE kind=? AND subject_id=?', (kind, subject_id)).fetchone()
        if not row:
            raise HTTPException(404, 'Nie znaleziono zdjęcia.')
        return Response(bytes(row['data']), media_type='image/jpeg', headers={'X-Content-Type-Options': 'nosniff'})

    @app.get('/user-photos/mine')
    def photos_mine(user=Depends(current_user)):
        require_enabled()
        with db() as con:
            rows = con.execute('SELECT kind,subject_id,digest,width,height FROM user_photos WHERE owner_id=? ORDER BY kind,subject_id', (user['id'],)).fetchall()
        return {'items': [dict(row) for row in rows]}

    @app.put('/user-photos/{kind}/{subject_id}')
    async def photo_upload(kind: str, subject_id: int, request: Request,
                           user=Depends(current_user), authorization: str | None = Header(default=None)):
        require_enabled()
        # Check ownership before reading/decoding and reauthenticate after it.
        def check():
            with write_db(user, authorization, (user['role'],)) as con:
                owns(con, kind, subject_id, user)
        await run_in_threadpool(check)
        declared = request.headers.get('content-length')
        if declared is not None and (not declared.isdecimal() or int(declared) > MAX_SOURCE_BYTES):
            raise HTTPException(413, 'Zdjęcie źródłowe przekracza 20 MB.')
        source = bytearray()
        async for chunk in request.stream():
            if len(source) + len(chunk) > MAX_SOURCE_BYTES:
                raise HTTPException(413, 'Zdjęcie źródłowe przekracza 20 MB.')
            source.extend(chunk)
        def save():
            data, width, height = (compress_photo(bytes(source), max_bytes=MAX_PRODUCT_BYTES)
                                   if kind == 'product' else compress_photo(bytes(source)))
            digest = hashlib.sha256(data).hexdigest()
            with write_db(user, authorization, (user['role'],)) as con:
                owns(con, kind, subject_id, user)
                con.execute('''INSERT INTO user_photos(kind,subject_id,owner_id,data,digest,width,height)
                    VALUES(?,?,?,?,?,?,?) ON CONFLICT(kind,subject_id) DO UPDATE SET
                    owner_id=excluded.owner_id,data=excluded.data,digest=excluded.digest,width=excluded.width,height=excluded.height''',
                    (kind, subject_id, user['id'], data, digest, width, height))
            return {'kind': kind, 'subject_id': subject_id, 'bytes': len(data), 'width': width, 'height': height, 'digest': digest}
        return await run_in_threadpool(save)

    @app.delete('/user-photos/{kind}/{subject_id}')
    def photo_delete(kind: str, subject_id: int, user=Depends(current_user), authorization: str | None = Header(default=None)):
        require_enabled()
        with write_db(user, authorization, (user['role'],)) as con:
            owns(con, kind, subject_id, user)
            con.execute('DELETE FROM user_photos WHERE kind=? AND subject_id=? AND owner_id=?', (kind, subject_id, user['id']))
        return {'ok': True}
