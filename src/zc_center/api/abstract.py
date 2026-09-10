from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from ..response import Response

if TYPE_CHECKING:
    from ..client import Client


class AbstractApi:
    def __init__(self, client: Client) -> None:
        self._client = client

    def post(self, path: str, payload: Mapping[str, Any] | None = None) -> Response:
        return self._client.post(path, payload or {})
