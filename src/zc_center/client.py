from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

import requests

from .api.exam_notice import ExamNoticeApi
from .api.exam_position import ExamPositionApi
from .api.job import JobApi
from .api.job_bank import JobBankApi
from .api.ping import PingApi
from .api.resume import ResumeApi
from .crypto import Crypto
from .exceptions import (
    ApiException,
    CryptoException,
    SapiException,
    SignatureException,
    TransportException,
)
from .response import Response

Logger = Callable[[str, Mapping[str, Any]], None]


class Client:
    """ZC Center SAPI 客户端：签名、加解密、验签与业务入口。"""

    def __init__(
        self,
        *,
        base_url: str,
        app_key: str,
        app_secret: str,
        encryption: bool = True,
        timeout: float = 10.0,
        connect_timeout: float = 3.0,
        verify_ssl: bool = True,
        debug: bool = False,
        logger: Logger | None = None,
        session: requests.Session | None = None,
        crypto: Crypto | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.app_key = app_key.strip()
        self.app_secret = app_secret
        self.encryption = encryption
        self.timeout = (connect_timeout, timeout)
        self.verify_ssl = verify_ssl
        self.debug = debug
        self._logger = logger
        self._session = session or requests.Session()
        self._crypto = crypto or Crypto()
        self._apis: dict[type[Any], Any] = {}

        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise SapiException("ZC Center SDK的base_url配置无效")
        if not self.app_key or not self.app_secret:
            raise SapiException("ZC Center SDK的app_key或app_secret未配置")

    def ping(self) -> PingApi:
        return self._api(PingApi)

    def exam_notice(self) -> ExamNoticeApi:
        return self._api(ExamNoticeApi)

    def exam_position(self) -> ExamPositionApi:
        return self._api(ExamPositionApi)

    def resume(self) -> ResumeApi:
        return self._api(ResumeApi)

    def job(self) -> JobApi:
        return self._api(JobApi)

    def job_bank(self) -> JobBankApi:
        return self._api(JobBankApi)

    def get(self, path: str, query: Mapping[str, Any] | None = None) -> Response:
        return self.request("GET", path, {}, query or {})

    def post(
        self,
        path: str,
        payload: Mapping[str, Any] | None = None,
        query: Mapping[str, Any] | None = None,
    ) -> Response:
        return self.request("POST", path, payload or {}, query or {})

    def request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
        query: Mapping[str, Any] | None = None,
    ) -> Response:
        path = "/" + path.lstrip("/")
        if not path.startswith("/sapi/"):
            raise SapiException("SAPI请求路径必须以/sapi/开头")

        payload = dict(payload or {})
        query = dict(query or {})
        timestamp = str(int(time.time()))
        nonce = self._crypto.nonce()
        aad = self._crypto.aad(self.app_key, timestamp, nonce)

        try:
            body_obj: Mapping[str, Any] = (
                self._crypto.encrypt(payload, self.app_secret, aad) if self.encryption else payload
            )
            body = self._crypto.json_encode(body_obj)
        except (CryptoException, TypeError, ValueError) as exc:
            raise SapiException("SAPI请求JSON编码或加密失败") from exc

        canonical = self._crypto.canonical_request(method, path, query, timestamp, nonce, body)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-App-Key": self.app_key,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": self._crypto.sign(canonical, self.app_secret),
            "X-Encrypted": "1" if self.encryption else "0",
        }
        url = self.base_url + path

        self._log(
            "SAPI request",
            {
                "method": method.upper(),
                "url": url,
                "query": query,
                "request_headers": headers,
                "request_params": payload,
            },
        )

        try:
            http_response = self._session.request(
                method=method.upper(),
                url=url,
                params=query or None,
                data=body.encode("utf-8"),
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        except requests.RequestException as exc:
            self._log(
                "SAPI request transport error",
                {"method": method.upper(), "url": url, "error": str(exc)},
            )
            raise TransportException(f"SAPI网络请求失败：{exc}") from exc

        return self._parse_response(http_response, timestamp, nonce, aad)

    def _parse_response(
        self,
        response: requests.Response,
        timestamp: str,
        nonce: str,
        aad: str,
    ) -> Response:
        raw_body = response.text
        status_code = response.status_code
        response_headers = {k: v for k, v in response.headers.items()}
        signature = (response.headers.get("X-Response-Signature") or "").strip()
        encrypted = (response.headers.get("X-Encrypted") or "") == "1"

        self._log(
            "SAPI response",
            {
                "http_status": status_code,
                "response_headers": response_headers,
            },
        )

        try:
            decoded = json.loads(raw_body) if raw_body else None
        except json.JSONDecodeError as exc:
            raise TransportException("SAPI响应不是有效JSON") from exc
        if not isinstance(decoded, dict):
            raise TransportException("SAPI响应必须是JSON对象")

        if signature == "":
            if status_code >= 400:
                raise self._api_exception(decoded, status_code, False)
            raise SignatureException("SAPI响应缺少X-Response-Signature")

        if encrypted:
            if not self._crypto.verify_encrypted_response(
                decoded, signature, timestamp, nonce, self.app_secret
            ):
                raise SignatureException("SAPI加密响应签名验证失败")
            try:
                payload = self._crypto.decrypt(decoded, self.app_secret, aad)
            except CryptoException as exc:
                raise SapiException("SAPI响应解密失败") from exc
        else:
            if not self._crypto.verify_plaintext_response(
                raw_body, signature, timestamp, nonce, self.app_secret
            ):
                raise SignatureException("SAPI明文响应签名验证失败")
            payload = decoded

        self._log(
            "SAPI response payload",
            {"http_status": status_code, "response_payload": payload},
        )

        if status_code >= 400 or int(payload.get("code") or 0) != 0:
            raise self._api_exception(payload, status_code, True)

        return Response(status_code, payload, response_headers, raw_body)

    def _api_exception(
        self,
        payload: Mapping[str, Any],
        http_status: int,
        signature_verified: bool,
    ) -> ApiException:
        data = payload.get("data")
        return ApiException(
            str(payload.get("msg") or "SAPI接口调用失败"),
            code=int(payload.get("code") or 0),
            http_status=http_status,
            data=data if isinstance(data, (dict, list)) else None,
            signature_verified=signature_verified,
        )

    def _api(self, api_cls: type[Any]) -> Any:
        if api_cls not in self._apis:
            self._apis[api_cls] = api_cls(self)
        return self._apis[api_cls]

    def _log(self, message: str, context: Mapping[str, Any]) -> None:
        if not self.debug:
            return
        if self._logger is not None:
            self._logger(message, context)
            return
        logging.getLogger("zc_center").info("%s %s", message, json.dumps(context, ensure_ascii=False))
