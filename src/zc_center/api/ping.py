from __future__ import annotations

from typing import Any, Mapping

from ..response import Response
from .abstract import AbstractApi


class PingApi(AbstractApi):
    def send(self, echo: str = "ping") -> Response:
        return self.post("/sapi/ping", {"echo": echo})
