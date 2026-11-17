"""Temporary ad artwork for disposable demo databases only."""
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

def make_banner(audience):
    background = '#e7f2e5' if audience == 'rolnik' else '#fbe9e7'
    ink = '#245c35' if audience == 'rolnik' else '#9c2525'
    image = Image.new('RGB', (1200, 520), background)
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype('DejaVuSans-Bold.ttf', 48)
        subtitle_font = ImageFont.truetype('DejaVuSans.ttf', 35)
    except OSError:
        title_font = ImageFont.load_default()
        subtitle_font = title_font
    lines = [
        ('TU JEST MIEJSCE NA TWOJĄ REKLAMĘ', 160, title_font),
        ('DOTRZYJ DO ROLNIKÓW I SPRZEDAWCÓW' if audience == 'rolnik' else 'DOTRZYJ DO KLIENTÓW', 275, subtitle_font),
    ]
    for line, y, font in lines:
        bounds = draw.textbbox((0, 0), line, font=font)
        draw.text(((1200 - bounds[2] + bounds[0]) / 2, y), line, fill=ink, font=font)
    buffer = BytesIO()
    image.save(buffer, 'JPEG', quality=88)
    return base64.b64encode(buffer.getvalue()).decode('ascii')
