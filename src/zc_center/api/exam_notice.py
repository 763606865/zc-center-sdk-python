from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..response import Response
from .abstract import AbstractApi

POSITION_BATCH_SIZE = 100


class ExamNoticeApi(AbstractApi):
    def list(self, params: Mapping[str, Any] | None = None) -> Response:
        return self.post("/sapi/exam-notice/list", dict(params or {}))

    def report(self, notice: Mapping[str, Any]) -> Response:
        payload, positions = _detach_positions(notice)
        response = self.post("/sapi/exam-notice/report", payload)
        data = response.data() or {}
        notice_data = data.get("notice") if isinstance(data, dict) else None
        uuid = ""
        if isinstance(notice_data, dict):
            uuid = str(notice_data.get("uuid") or "")
        if not uuid:
            uuid = str(payload.get("uuid") or "")
        self._push_positions(uuid, positions)
        return response

    def report_batch(self, items: Sequence[Mapping[str, Any]]) -> Response:
        stripped: list[dict[str, Any]] = []
        pending: list[list[Any]] = []
        for item in items:
            payload, positions = _detach_positions(item)
            stripped.append(payload)
            pending.append(positions)
        response = self.post("/sapi/exam-notice/report-batch", {"items": stripped})
        data = response.data() or {}
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            return response
        for index, row in enumerate(results):
            if not isinstance(row, dict) or row.get("action") == "failed":
                continue
            notice_data = row.get("notice")
            uuid = ""
            if isinstance(notice_data, dict):
                uuid = str(notice_data.get("uuid") or "")
            if not uuid and index < len(stripped):
                uuid = str(stripped[index].get("uuid") or "")
            self._push_positions(uuid, pending[index] if index < len(pending) else [])
        return response

    def _push_positions(self, notice_uuid: str, positions: Sequence[Mapping[str, Any]]) -> None:
        if not notice_uuid or not positions:
            return
        items = list(positions)
        last_start = (len(items) - 1) // POSITION_BATCH_SIZE * POSITION_BATCH_SIZE
        for start in range(0, len(items), POSITION_BATCH_SIZE):
            chunk = items[start : start + POSITION_BATCH_SIZE]
            self._client.exam_position().report_batch(
                notice_uuid,
                chunk,
                sync_index=start == last_start,
            )


def _detach_positions(notice: Mapping[str, Any]) -> tuple[dict[str, Any], list[Any]]:
    payload = dict(notice)
    raw = payload.pop("positions", None)
    if isinstance(raw, list):
        return payload, raw
    return payload, []
