"""Content-version public UI assets so deployments cannot reuse older URLs."""
import hashlib
import re
from pathlib import Path

ASSET = re.compile(r'((?:src|href)="/assets/)([A-Za-z0-9_-]+\.(?:js|css))(")')


def versioned_index(root):
    root = Path(root)
    html = (root / 'index.html').read_text(encoding='utf-8')

    def replace(match):
        digest = hashlib.sha256((root / match[2]).read_bytes()).hexdigest()[:20]
        return f'{match[1]}{match[2]}?v={digest}{match[3]}'

    return ASSET.sub(replace, html)
