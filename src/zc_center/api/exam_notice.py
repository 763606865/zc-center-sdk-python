from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..response import Response
from .abstract import AbstractApi


class ExamNoticeApi(AbstractApi):
    def list(self, params: Mapping[str, Any] | None = None) -> Response:
        return self.post("/sapi/exam-notice/list", dict(params or {}))

    def report(self, notice: Mapping[str, Any]) -> Response:
        return self.post("/sapi/exam-notice/report", dict(notice))

    def report_batch(self, items: Sequence[Mapping[str, Any]]) -> Response:
        return self.post("/sapi/exam-notice/report-batch", {"items": list(items)})
