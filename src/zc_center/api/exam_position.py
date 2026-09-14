from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..response import Response
from .abstract import AbstractApi


class ExamPositionApi(AbstractApi):
    def list(self, params: Mapping[str, Any]) -> Response:
        return self.post("/sapi/exam-position/list", dict(params))

    def report_batch(
        self,
        notice_uuid: str,
        items: Sequence[Mapping[str, Any]],
        *,
        sync_index: bool = False,
    ) -> Response:
        return self.post(
            "/sapi/exam-position/report-batch",
            {
                "notice_uuid": notice_uuid,
                "items": list(items),
                "sync_index": sync_index,
            },
        )
