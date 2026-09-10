from __future__ import annotations

from typing import Any, Mapping


class Response:
    def __init__(
        self,
        status_code: int,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        raw_body: str,
    ) -> None:
        self._status_code = status_code
        self._payload = dict(payload)
        self._headers = dict(headers)
        self._raw_body = raw_body

    def status_code(self) -> int:
        return self._status_code

    def payload(self) -> dict[str, Any]:
        return self._payload

    def data(self) -> Any:
        return self._payload.get("data")

    def message(self) -> str:
        return str(self._payload.get("msg") or "")

    def headers(self) -> dict[str, str]:
        return self._headers

    def raw_body(self) -> str:
        return self._raw_body
