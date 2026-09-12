from __future__ import annotations

from typing import Any, Mapping

from ..response import Response
from .abstract import AbstractApi


class JobApi(AbstractApi):
    """职位同步 SAPI。参见 docs/sapi/职位.md"""

    def list(self, params: Mapping[str, Any] | None = None) -> Response:
        """增量拉取可访问职位（含删除 tombstone）。POST /sapi/job/list"""
        return self.post("/sapi/job/list", dict(params or {}))

    def detail(self, uuid: str) -> Response:
        return self.post("/sapi/job/detail", {"uuid": uuid})

    def report(self, job: Mapping[str, Any]) -> Response:
        """归属应用向自有职位库上报职位。POST /sapi/job/report"""
        return self.post("/sapi/job/report", dict(job))

    def update(self, job: Mapping[str, Any]) -> Response:
        """更新职位（归属可改内容+状态；订阅仅 status）。POST /sapi/job/update"""
        return self.post("/sapi/job/update", dict(job))
