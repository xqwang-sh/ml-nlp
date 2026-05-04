from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    text: str = Field(description="支持风险类别判断的年报原文")
    page_no: Optional[int] = Field(default=None, description="证据所在页码")


class RiskCategory(BaseModel):
    category: Literal[
        "市场风险",
        "行业竞争风险",
        "经营风险",
        "财务风险",
        "政策与合规风险",
        "技术与研发风险",
        "供应链与原材料风险",
        "汇率与利率风险",
        "环境与安全风险",
        "管理与内控风险",
        "其他风险",
    ]
    evidence: Evidence


class AnnualReportRiskExtract(BaseModel):
    doc_id: str
    stock_code: Optional[str] = None
    company_name: str
    report_year: Literal["2024"]
    event_type: Literal["年报风险披露"]
    risk_categories: list[RiskCategory]
