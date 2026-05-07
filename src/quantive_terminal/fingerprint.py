import hashlib
import platform
import uuid


def get_fingerprint():
    raw = f"{platform.node()}|{uuid.getnode()}|{platform.system()}|{platform.machine()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:40]
