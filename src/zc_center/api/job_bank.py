from __future__ import annotations

from typing import Any, Mapping

from ..response import Response
from .abstract import AbstractApi


class JobBankApi(AbstractApi):
    """职位库 SAPI。参见 docs/sapi/职位.md"""

    def list(self, params: Mapping[str, Any] | None = None) -> Response:
        """列出当前应用可访问的已发布职位库。POST /sapi/job-bank/list"""
        return self.post("/sapi/job-bank/list", dict(params or {}))

    def detail(self, uuid: str) -> Response:
        """按 UUID 获取职位库详情（含 job_count）。POST /sapi/job-bank/detail"""
        return self.post("/sapi/job-bank/detail", {"uuid": uuid})
