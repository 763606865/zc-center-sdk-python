from __future__ import annotations

from typing import Any, Mapping

from ..response import Response
from .abstract import AbstractApi


class EnterpriseApi(AbstractApi):
    """企业与职工 SAPI。参见 docs/sapi/企业.md。"""

    ROLE_ADMIN = 1
    ROLE_MEMBER = 2

    def report(self, payload: Mapping[str, Any]) -> Response:
        return self.post("/sapi/enterprise/report", dict(payload))

    def detail(self, payload: Mapping[str, Any]) -> Response:
        return self.post("/sapi/enterprise/detail", dict(payload))

    def add_member(self, payload: Mapping[str, Any]) -> Response:
        return self.post("/sapi/enterprise/member/add", dict(payload))

    def remove_member(self, payload: Mapping[str, Any]) -> Response:
        return self.post("/sapi/enterprise/member/remove", dict(payload))
