from __future__ import annotations

from typing import Any, Mapping

from zc_center.api.enterprise import EnterpriseApi
from zc_center.api.organization import OrganizationApi
from zc_center.response import Response


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def post(self, path: str, payload: Mapping[str, Any] | None = None) -> Response:
        body = dict(payload or {})
        self.calls.append((path, body))
        return Response(200, {"code": 0, "msg": "ok", "data": body}, {}, "")


def test_organization_report_and_detail_paths() -> None:
    client = RecordingClient()
    api = OrganizationApi(client)  # type: ignore[arg-type]
    report = {"external_id": "school-1", "name": "示例学校", "primary_type": "school"}
    api.report(report)
    api.detail({"external_id": "school-1"})
    assert client.calls == [
        ("/sapi/organization/report", report),
        ("/sapi/organization/detail", {"external_id": "school-1"}),
    ]


def test_enterprise_detail_path() -> None:
    client = RecordingClient()
    EnterpriseApi(client).detail({"credit_code": "91110000MA01234567"})  # type: ignore[arg-type]
    assert client.calls == [("/sapi/enterprise/detail", {"credit_code": "91110000MA01234567"})]
