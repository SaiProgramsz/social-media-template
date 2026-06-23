from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from prod_ai.main import _blocks_to_payload, ai_tips, build_plan, format_plan

from .payloads import PlannerRequestData, parse_request_payload


@dataclass(frozen=True)
class PlannerResult:
    blocks_payload: dict[str, Any]
    formatted_plan: str
    coaching_tips: str
    subject_count: int


def generate_plan_from_request(request_data: PlannerRequestData) -> PlannerResult:
    blocks = build_plan(
        request_data.subjects,
        request_data.config,
        start_day=request_data.start_day,
    )
    return PlannerResult(
        blocks_payload=_blocks_to_payload(blocks),
        formatted_plan=format_plan(blocks),
        coaching_tips=ai_tips(request_data.subjects, request_data.config),
        subject_count=len(request_data.subjects),
    )


def generate_plan_from_payload(
    payload_text: str, start_date_text: str | None = None
) -> PlannerResult:
    return generate_plan_from_request(parse_request_payload(payload_text, start_date_text))

