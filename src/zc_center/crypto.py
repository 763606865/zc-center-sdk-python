from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from typing import Any, Mapping
from urllib.parse import quote

from .exceptions import CryptoException


class Crypto:
    """与 ThinkPHP / Spring Boot SDK 对齐的签名与 AES-GCM 工具。"""

    def encrypt(self, payload: Mapping[str, Any], app_secret: str, aad: str) -> dict[str, str]:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        plaintext = self.json_encode(payload).encode("utf-8")
        iv = secrets.token_bytes(12)
        aesgcm = AESGCM(self._key(app_secret))
        sealed = aesgcm.encrypt(iv, plaintext, aad.encode("utf-8"))
        ciphertext, tag = sealed[:-16], sealed[-16:]
        return {
            "algorithm": "AES-256-GCM",
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
            "iv": base64.b64encode(iv).decode("ascii"),
            "tag": base64.b64encode(tag).decode("ascii"),
        }

    def decrypt(self, envelope: Mapping[str, Any], app_secret: str, aad: str) -> dict[str, Any]:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        for field in ("ciphertext", "iv", "tag"):
            value = envelope.get(field)
            if not isinstance(value, str) or value == "":
                raise CryptoException(f"SAPI加密响应缺少字段：{field}")

        try:
            ciphertext = base64.b64decode(envelope["ciphertext"], validate=True)
            iv = base64.b64decode(envelope["iv"], validate=True)
            tag = base64.b64decode(envelope["tag"], validate=True)
        except Exception as exc:  # noqa: BLE001
            raise CryptoException("SAPI加密响应格式错误") from exc

        if len(iv) != 12 or len(tag) != 16:
            raise CryptoException("SAPI加密响应格式错误")

        aesgcm = AESGCM(self._key(app_secret))
        try:
            plaintext = aesgcm.decrypt(iv, ciphertext + tag, aad.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise CryptoException("SAPI响应解密或完整性验证失败") from exc

        try:
            payload = json.loads(plaintext.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise CryptoException("SAPI解密响应不是JSON对象") from exc
        if not isinstance(payload, dict):
            raise CryptoException("SAPI解密响应不是JSON对象")
        return payload

    def canonical_request(
        self,
        method: str,
        path: str,
        query: Mapping[str, Any],
        timestamp: str,
        nonce: str,
        raw_body: str,
    ) -> str:
        normalized_path = "/" + path.lstrip("/")
        canonical_query = self._canonical_query(query)
        return "\n".join(
            [
                method.upper(),
                normalized_path,
                canonical_query,
                timestamp,
                nonce,
                self.sha256_hex(raw_body),
            ]
        )

    def sign(self, canonical: str, app_secret: str) -> str:
        return hmac.new(app_secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    def aad(self, app_key: str, timestamp: str, nonce: str) -> str:
        return "\n".join([app_key, timestamp, nonce])

    def verify_encrypted_response(
        self,
        envelope: Mapping[str, Any],
        signature: str,
        timestamp: str,
        nonce: str,
        app_secret: str,
    ) -> bool:
        for field in ("iv", "tag", "ciphertext"):
            if not isinstance(envelope.get(field), str):
                return False
        canonical = "\n".join(
            [
                timestamp,
                nonce,
                str(envelope["iv"]),
                str(envelope["tag"]),
                str(envelope["ciphertext"]),
            ]
        )
        expected = self.sign(canonical, app_secret)
        return signature != "" and hmac.compare_digest(expected, signature.lower())

    def verify_plaintext_response(
        self,
        raw_body: str,
        signature: str,
        timestamp: str,
        nonce: str,
        app_secret: str,
    ) -> bool:
        canonical = "\n".join([timestamp, nonce, self.sha256_hex(raw_body)])
        expected = self.sign(canonical, app_secret)
        return signature != "" and hmac.compare_digest(expected, signature.lower())

    def json_encode(self, payload: Mapping[str, Any] | list[Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

    def nonce(self) -> str:
        # 与 PHP rtrim(strtr(base64_encode(random_bytes(18)), '+/', '-_'), '=') 等价
        raw = base64.b64encode(secrets.token_bytes(18)).decode("ascii")
        return raw.translate(str.maketrans("+/", "-_")).rstrip("=")

    def sha256_hex(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _key(self, app_secret: str) -> bytes:
        return hashlib.sha256(app_secret.encode("utf-8")).digest()

    def _canonical_query(self, query: Mapping[str, Any]) -> str:
        if not query:
            return ""
        parts: list[str] = []
        for key in sorted(query.keys()):
            value = query[key]
            if value is None:
                continue
            encoded_key = quote(str(key), safe="-_.~")
            encoded_value = quote(str(value), safe="-_.~")
            parts.append(f"{encoded_key}={encoded_value}")
        return "&".join(parts)
