from __future__ import annotations

from typing import Any, Mapping

from ..response import Response
from .abstract import AbstractApi


class OrganizationApi(AbstractApi):
    """组织管理 SAPI。参见 docs/sapi/组织.md。"""

    TYPE_ENTERPRISE = "enterprise"
    TYPE_SCHOOL = "school"
    TYPE_GOVERNMENT = "government"
    TYPE_PUBLIC_INSTITUTION = "public_institution"
    TYPE_ASSOCIATION = "association"
    TYPE_LAW_FIRM = "law_firm"
    TYPE_HR_AGENCY = "hr_agency"
    TYPE_MEDICAL = "medical"
    TYPE_FOUNDATION = "foundation"
    TYPE_COMMUNITY = "community"
    TYPE_OTHER = "other"

    def report(self, payload: Mapping[str, Any]) -> Response:
        """按 external_id 幂等上报，或按 organization_uuid 更新。"""
        return self.post("/sapi/organization/report", dict(payload))

    def detail(self, payload: Mapping[str, Any]) -> Response:
        """按 organization_uuid 或 external_id 获取详情。"""
        return self.post("/sapi/organization/detail", dict(payload))
