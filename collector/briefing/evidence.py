import hashlib
from ..publish import atomic_write


def preserve_raw(root, raw):
    digest = hashlib.sha256(raw).hexdigest()
    path = root / 'raw' / (digest + '.bin')
    if not path.exists():
        atomic_write(path, raw)
    return digest
