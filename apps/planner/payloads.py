from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prod_ai.main import DailyAvailability, PlannerConfig, Subject, _clamp_int, _parse_date, _parse_time


@dataclass(frozen=True)
class PlannerRequestData:
    subjects: list[Subject]
    config: PlannerConfig
    start_day: dt.date | None


def sample_payload_dict() -> dict[str, Any]:
    sample_path = Path(__file__).resolve().parents[2] / "prod_ai" / "sample.json"
    return json.loads(sample_path.read_text(encoding="utf-8"))


def sample_payload_text() -> str:
    return json.dumps(sample_payload_dict(), ensure_ascii=False, indent=2)


def parse_request_payload(payload_text: str, start_date_text: str | None = None) -> PlannerRequestData:
    payload = json.loads(payload_text or "{}")
    subjects: list[Subject] = []
    for item in payload.get("subjects") or []:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        subjects.append(
            Subject(
                name=name,
                priority=_clamp_int(int(item.get("priority", 3)), 1, 5),
                difficulty=_clamp_int(int(item.get("difficulty", 3)), 1, 5),
                weekly_hours=float(item.get("weekly_hours", 5)),
                exam_date=_parse_date(str(item.get("exam_date", "")).strip())
                if str(item.get("exam_date", "")).strip()
                else None,
            )
        )

    cfg = payload.get("config") or {}

    def _t(key: str, default: str) -> dt.time:
        return _parse_time(str(cfg.get(key, default)))

    config = PlannerConfig(
        horizon_days=max(1, int(cfg.get("horizon_days", 14))),
        pomodoro_minutes=max(15, int(cfg.get("pomodoro_minutes", 50))),
        break_minutes=max(0, int(cfg.get("break_minutes", 10))),
        max_subject_switches_per_day=max(1, int(cfg.get("max_subject_switches_per_day", 3))),
        focus_time=str(cfg.get("focus_time", "balanced")).lower(),
        availability_weekday=DailyAvailability(
            start=_t("weekday_start", "17:00"),
            end=_t("weekday_end", "21:00"),
        ),
        availability_weekend=DailyAvailability(
            start=_t("weekend_start", "10:00"),
            end=_t("weekend_end", "16:00"),
        ),
    )

    start_day = _parse_date(start_date_text.strip()) if start_date_text else None
    return PlannerRequestData(subjects=subjects, config=config, start_day=start_day)

