from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
from uuid import uuid4

from src.utils.config import PROJECT_ROOT


class CredentialVault:
    """Small local vault for API connector secrets.

    The vault stores encrypted values in JSON config and keeps the encryption key
    in a gitignored local key file unless AIOS_CONNECTOR_KEY is provided.
    """

    def __init__(self, key_path: str | Path = PROJECT_ROOT / "config" / "api_connector.key") -> None:
        self.key_path = Path(key_path)

    def encrypt(self, value: str) -> str:
        if not value:
            return ""
        raw = value.encode("utf-8")
        encrypted = self._xor(raw)
        return "enc:v1:" + base64.urlsafe_b64encode(encrypted).decode("ascii")

    def decrypt(self, value: str) -> str:
        if not value:
            return ""
        if not value.startswith("enc:v1:"):
            return ""
        try:
            raw = base64.urlsafe_b64decode(value.split(":", 2)[2].encode("ascii"))
            return self._xor(raw).decode("utf-8")
        except Exception:
            return ""

    def masked(self, value: str) -> str:
        plain = self.decrypt(value)
        if not plain:
            return ""
        return f"{plain[:2]}...{plain[-2:]}" if len(plain) >= 6 else "***"

    def _key(self) -> bytes:
        env_key = os.getenv("AIOS_CONNECTOR_KEY", "").strip()
        if env_key:
            return hashlib.sha256(env_key.encode("utf-8")).digest()
        if not self.key_path.exists():
            self.key_path.parent.mkdir(parents=True, exist_ok=True)
            self.key_path.write_text(uuid4().hex + uuid4().hex, encoding="utf-8")
        return hashlib.sha256(self.key_path.read_bytes()).digest()

    def _xor(self, data: bytes) -> bytes:
        key = self._key()
        stream = bytearray()
        counter = 0
        while len(stream) < len(data):
            stream.extend(hashlib.sha256(key + counter.to_bytes(4, "big")).digest())
            counter += 1
        return bytes(byte ^ stream[index] for index, byte in enumerate(data))
