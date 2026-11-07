from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class FieldCipher:
    def __init__(self, key_b64: str) -> None:
        raw = base64.b64decode(key_b64)
        if len(raw) != 32:
            raise ValueError("PD_ENCRYPTION_KEY must decode to 32 bytes")
        self._gcm = AESGCM(raw)

    def encrypt(self, plaintext: str) -> bytes:
        nonce = os.urandom(12)
        ct = self._gcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return nonce + ct

    def decrypt(self, blob: bytes) -> str:
        nonce, ct = blob[:12], blob[12:]
        return self._gcm.decrypt(nonce, ct, None).decode("utf-8")
