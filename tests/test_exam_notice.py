from __future__ import annotations

from typing import Any, Mapping

from zc_center.api.exam_notice import ExamNoticeApi
from zc_center.api.exam_position import ExamPositionApi
from zc_center.response import Response


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._notice_uuid = "notice-uuid-1"

    def exam_position(self) -> ExamPositionApi:
        return ExamPositionApi(self)  # type: ignore[arg-type]

    def post(self, path: str, payload: Mapping[str, Any] | None = None) -> Response:
        body = dict(payload or {})
        self.calls.append((path, body))
        if path == "/sapi/exam-notice/report":
            data = {"notice": {"uuid": self._notice_uuid}, "action": "created"}
        elif path == "/sapi/exam-notice/report-batch":
            data = {
                "created": 1,
                "exists": 0,
                "failed": 0,
                "results": [{"action": "created", "notice": {"uuid": self._notice_uuid}}],
            }
        else:
            data = {"ok": True}
        return Response(200, {"code": 0, "msg": "ok", "data": data}, {}, "")


def test_report_splits_positions_into_batches() -> None:
    client = RecordingClient()
    api = ExamNoticeApi(client)  # type: ignore[arg-type]
    positions = [{"code": f"P{i:03d}", "name": f"岗{i}"} for i in range(101)]

    api.report(
        {
            "title": "公告",
            "collect_source": "来源",
            "positions": positions,
        }
    )

    paths = [path for path, _ in client.calls]
    assert paths[0] == "/sapi/exam-notice/report"
    assert "positions" not in client.calls[0][1]
    assert paths[1:] == [
        "/sapi/exam-position/report-batch",
        "/sapi/exam-position/report-batch",
    ]
    assert len(client.calls[1][1]["items"]) == 100
    assert client.calls[1][1]["sync_index"] is False
    assert len(client.calls[2][1]["items"]) == 1
    assert client.calls[2][1]["sync_index"] is True
    assert client.calls[1][1]["notice_uuid"] == "notice-uuid-1"


def test_report_batch_keeps_notice_payload_without_positions() -> None:
    client = RecordingClient()
    api = ExamNoticeApi(client)  # type: ignore[arg-type]
    api.report_batch(
        [
            {
                "title": "公告",
                "collect_source": "来源",
                "uuid": "self-uuid",
                "positions": [{"code": "A", "name": "岗A"}],
            }
        ]
    )
    assert "positions" not in client.calls[0][1]["items"][0]
    assert client.calls[1][0] == "/sapi/exam-position/report-batch"
    assert client.calls[1][1]["sync_index"] is True
