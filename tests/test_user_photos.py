"""Shared photo sanitizer, permissions, atomic replacement and hard byte bounds."""
import io
import sqlite3
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from backend import user_photos as photos


def picture(mode='RGB', size=(600, 400), fmt='JPEG', **save):
    image = Image.new(mode, size, (255, 0, 0, 0) if mode == 'RGBA' else 'red')
    stream = io.BytesIO()
    image.save(stream, fmt, **save)
    return stream.getvalue()


@pytest.mark.parametrize('mode,fmt', [('RGB','JPEG'), ('RGBA','PNG'), ('RGB','WEBP'), ('L','PNG')])
def test_supported_photos_always_become_bounded_metadata_free_jpeg(mode, fmt):
    data, width, height = photos.compress_photo(picture(mode, fmt=fmt))
    assert 0 < len(data) <= 1_000_000
    with Image.open(io.BytesIO(data)) as image:
        assert image.format == 'JPEG' and image.mode == 'RGB'
        assert image.size == (width,height) == (600,400)
        assert not image.getexif() and 'icc_profile' not in image.info
        if mode == 'RGBA':
            assert all(v > 250 for v in image.getpixel((0,0)))


def test_orientation_is_applied_and_exif_removed():
    exif = Image.Exif();exif[274]=6;exif[270]='private metadata'
    data,w,h = photos.compress_photo(picture(size=(600,400),exif=exif))
    assert (w,h)==(400,600)
    assert not Image.open(io.BytesIO(data)).getexif()
    assert b'private metadata' not in data


def test_noisy_large_photo_is_resized_and_compressed():
    image=Image.effect_noise((3200,2400),100).convert('RGB')
    source=io.BytesIO();image.save(source,'PNG')
    data,w,h=photos.compress_photo(source.getvalue())
    assert len(data)<=photos.MAX_BYTES and max(w,h)<=2048
    assert abs(w/h-4/3)<.01


@pytest.mark.parametrize('source',[b'',b'<svg onload="alert(1)"></svg>',b'not an image',picture()[:80]])
def test_corrupt_and_non_raster_sources_are_rejected(source):
    with pytest.raises(HTTPException):photos.compress_photo(source)


def test_source_bytes_pixels_and_animation_are_bounded(monkeypatch):
    monkeypatch.setattr(photos,'MAX_SOURCE_BYTES',20)
    with pytest.raises(HTTPException) as error:photos.compress_photo(b'x'*21)
    assert error.value.status_code==413
    monkeypatch.setattr(photos,'MAX_SOURCE_BYTES',20_000_000)
    monkeypatch.setattr(photos,'MAX_PIXELS',100)
    with pytest.raises(HTTPException) as error:photos.compress_photo(picture())
    assert error.value.status_code==413
    monkeypatch.setattr(photos,'MAX_PIXELS',50_000_000)
    stream=io.BytesIO();a=Image.new('RGB',(10,10),'red');b=Image.new('RGB',(10,10),'blue')
    a.save(stream,'PNG',save_all=True,append_images=[b])
    with pytest.raises(HTTPException):photos.compress_photo(stream.getvalue())


@pytest.fixture(scope='module')
def api():
    from backend import app as module
    patch=pytest.MonkeyPatch();patch.setenv('WP_ENABLE_USER_PHOTOS','1')
    with module.db() as con:con.executescript(photos.SCHEMA_SQLITE)
    client=TestClient(module.app)
    users=[]
    for role in ('rolnik','rolnik','klient'):
        account={'email':uuid4().hex+'@example.invalid','password':'PhotoPrivateSynthetic2026','role':role}
        result=client.post('/auth/register',json=account);assert result.status_code==201
        token=client.post('/auth/login',json=account).json()['access_token']
        users.append(({'Authorization':'Bearer '+token},result.json()['id']))
    yield client,users,module
    patch.undo()


def test_all_target_types_share_sanitizer_and_public_output(api):
    client,users,_=api;farmer=users[0]
    product=client.post('/products',headers=farmer[0],json={'name':'Zdjęcie produktu','price_grosze':200,'delivery_grosze':500,'stock':5}).json()['id']
    for kind,sid,owner in [('product',product,farmer),('farm',farmer[1],farmer),('profile',users[2][1],users[2])]:
        url=f'/user-photos/{kind}/{sid}'
        response=client.put(url,headers={**owner[0],'Content-Type':'text/plain'},content=picture())
        assert response.status_code==200,response.text
        assert response.json()['bytes']<=photos.MAX_BYTES
        public=client.get(url);assert public.status_code==200
        assert public.headers['content-type']=='image/jpeg'
        assert public.headers['x-content-type-options']=='nosniff'
        assert len(public.content)==response.json()['bytes']
        assert client.put(url,content=picture()).status_code==401
        assert client.put(url,headers=users[1][0],content=picture()).status_code==404
        assert client.delete(url,headers=users[1][0]).status_code==404
        old=public.content
        assert client.put(url,headers=owner[0],content=b'invalid').status_code==422
        assert client.get(url).content==old
        assert client.delete(url,headers=owner[0]).status_code==200
        assert client.get(url).status_code==404
    assert client.put(f'/user-photos/farm/{users[2][1]}',headers=users[2][0],content=picture()).status_code==404


def test_disabled_scope_stream_limits_and_mine_privacy(api,monkeypatch):
    client,users,_=api;headers,uid=users[0];url=f'/user-photos/profile/{uid}'
    assert client.put(url,headers=headers,content=picture()).status_code==200
    mine=client.get('/user-photos/mine',headers=headers)
    assert mine.status_code==200 and mine.json()['items']
    assert all('data' not in row for row in mine.json()['items'])
    assert client.get('/user-photos/mine',headers=users[1][0]).json()['items']==[]
    monkeypatch.setattr(photos,'MAX_SOURCE_BYTES',10)
    assert client.put(url,headers=headers,content=b'x'*11).status_code==413
    assert client.put(url,headers=headers,content=iter([b'123456',b'123456'])).status_code==413
    monkeypatch.setenv('WP_ENABLE_USER_PHOTOS','0')
    assert client.get('/user-photos/config').json()['enabled'] is False
    assert client.get(url).status_code==503
    assert client.put(url,headers=headers,content=b'x').status_code==503


def test_logout_during_processing_prevents_photo_write(api,monkeypatch):
    client,users,module=api;headers,uid=users[1];url=f'/user-photos/profile/{uid}'
    original=photos.compress_photo
    def revoke(source):
        result=original(source)
        with module.db() as con:con.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
        return result
    monkeypatch.setattr(photos,'compress_photo',revoke)
    assert client.put(url,headers=headers,content=picture()).status_code==401
    assert client.get(url).status_code==404


def test_database_enforces_exact_byte_ceiling(api):
    _,users,module=api
    with module.db() as con:
        con.execute('INSERT INTO user_photos VALUES(?,?,?,?,?,?,?)',('profile',users[2][1],users[2][1],b'x'*1_000_000,'a'*64,1,1))
        with pytest.raises(sqlite3.IntegrityError):
            con.execute('UPDATE user_photos SET data=? WHERE kind=? AND subject_id=?',(b'x'*1_000_001,'profile',users[2][1]))
