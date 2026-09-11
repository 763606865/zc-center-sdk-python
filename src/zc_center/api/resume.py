from __future__ import annotations

from typing import Any, Mapping

from ..response import Response
from .abstract import AbstractApi


class ResumeApi(AbstractApi):
    def list(self, params: Mapping[str, Any] | None = None) -> Response:
        return self.post("/sapi/resume/list", dict(params or {}))

    def detail(self, uuid: str) -> Response:
        return self.post("/sapi/resume/detail", {"uuid": uuid})

    def report(self, resume: Mapping[str, Any]) -> Response:
        return self.post("/sapi/resume/report", dict(resume))

    def update(self, resume: Mapping[str, Any]) -> Response:
        return self.post("/sapi/resume/update", dict(resume))
