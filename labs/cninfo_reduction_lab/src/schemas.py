from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    text: str = Field(description="支持字段的公告原文")
    page_no: Optional[int] = Field(default=None, description="证据所在页码")


class ShareholderReductionExtract(BaseModel):
    doc_id: str
    stock_code: Optional[str] = None
    company_name: str
    event_type: Literal["股东减持"]
    shareholder_name: Optional[str] = None
    reduction_method: Optional[str] = None
    reduction_amount_text: Optional[str] = None
    reduction_ratio_text: Optional[str] = None
    reduction_period: Optional[str] = None
    reason: Optional[str] = None
    evidence: Evidence
