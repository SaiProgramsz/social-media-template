from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import http.server
import json
import os
import socketserver
import sys
import webbrowser
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class Subject:
    name: str
    priority: int  # 1-5 (5 is highest)
    difficulty: int  # 1-5 (5 is hardest)
    weekly_hours: float
    exam_date: Optional[dt.date] = None


@dataclass(frozen=True)
class DailyAvailability:
    start: dt.time
    end: dt.time


@dataclass(frozen=True)
class PlannerConfig:
    horizon_days: int
    pomodoro_minutes: int
    break_minutes: int
    max_subject_switches_per_day: int
    focus_time: str  # "morning" | "afternoon" | "evening" | "balanced"
    availability_weekday: DailyAvailability
    availability_weekend: DailyAvailability


@dataclass(frozen=True)
class StudyBlock:
    start: dt.datetime
    end: dt.datetime
    subject: str
    kind: str  # "study" | "review" | "break"
    notes: str = ""


def _clamp_int(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def _parse_date(value: str) -> Optional[dt.date]:
    value = value.strip()
    if not value:
        return None
    return dt.date.fromisoformat(value)


def _parse_time(value: str) -> dt.time:
    return dt.time.fromisoformat(value.strip())


def _today_local() -> dt.date:
    return dt.date.today()


def _is_weekend(day: dt.date) -> bool:
    return day.weekday() >= 5


def _availability_for_day(cfg: PlannerConfig, day: dt.date) -> DailyAvailability:
    return cfg.availability_weekend if _is_weekend(day) else cfg.availability_weekday


def _datetime_on(day: dt.date, t: dt.time) -> dt.datetime:
    return dt.datetime.combine(day, t)


def _minutes_between(a: dt.datetime, b: dt.datetime) -> int:
    return int((b - a).total_seconds() // 60)


def _ceil_div(a: int, b: int) -> int:
    return (a + b - 1) // b


def _subject_urgency(subject: Subject, day: dt.date) -> float:
    """
    Higher is more urgent. If no exam date, urgency is based on priority only.
    """
    if subject.exam_date is None:
        return float(subject.priority)
    days_left = (subject.exam_date - day).days
    if days_left <= 0:
        return 100.0 + subject.priority
    # Inverse curve: closer exams ramp urgency quickly.
    return (30.0 / days_left) + (subject.priority * 1.5)


def _energy_slots(
    cfg: PlannerConfig, day: dt.date
) -> List[Tuple[dt.datetime, dt.datetime, float]]:
    """
    Returns (slot_start, slot_end, energy_score 0..1) coarse buckets within availability.
    Used to bias hard subjects into high-energy periods.
    """
    avail = _availability_for_day(cfg, day)
    start = _datetime_on(day, avail.start)
    end = _datetime_on(day, avail.end)
    total = max(1, _minutes_between(start, end))

    # Split into 3 buckets and assign energy scores depending on focus_time.
    bucket_minutes = max(30, total // 3)
    buckets: List[Tuple[dt.datetime, dt.datetime, float]] = []
    for i in range(3):
        s = start + dt.timedelta(minutes=i * bucket_minutes)
        e = min(end, s + dt.timedelta(minutes=bucket_minutes))
        if s >= e:
            continue
        buckets.append((s, e, 0.5))

    if not buckets:
        return [(start, end, 0.5)]

    if cfg.focus_time == "morning":
        scores = [0.95, 0.65, 0.45]
    elif cfg.focus_time == "afternoon":
        scores = [0.6, 0.95, 0.55]
    elif cfg.focus_time == "evening":
        scores = [0.55, 0.7, 0.95]
    else:
        scores = [0.8, 0.85, 0.8]

    out: List[Tuple[dt.datetime, dt.datetime, float]] = []
    for idx, (s, e, _) in enumerate(buckets):
        out.append((s, e, scores[min(idx, len(scores) - 1)]))
    return out


def _generate_study_slots(
    cfg: PlannerConfig, day: dt.date
) -> List[Tuple[dt.datetime, dt.datetime]]:
    avail = _availability_for_day(cfg, day)
    cursor = _datetime_on(day, avail.start)
    end = _datetime_on(day, avail.end)

    slots: List[Tuple[dt.datetime, dt.datetime]] = []
    pom = cfg.pomodoro_minutes
    brk = cfg.break_minutes
    while cursor < end:
        study_end = min(end, cursor + dt.timedelta(minutes=pom))
        if study_end <= cursor:
            break
        slots.append((cursor, study_end))
        cursor = study_end + dt.timedelta(minutes=brk)
    return slots


def _weighted_subject_order(
    subjects: List[Subject], day: dt.date
) -> List[Tuple[Subject, float]]:
    """
    Produces weights for each subject for the given day.
    """
    weights: List[Tuple[Subject, float]] = []
    for s in subjects:
        urgency = _subject_urgency(s, day)
        # Difficulty adds some extra weight so hard items appear more often,
        # but urgency/priority dominates.
        weight = urgency * (1.0 + (s.difficulty - 1) * 0.10)
        weights.append((s, weight))
    weights.sort(key=lambda x: x[1], reverse=True)
    return weights


def _pick_subject(
    candidates: List[Subject],
    weights: Dict[str, float],
    remaining_minutes: Dict[str, int],
    energy_score: float,
    recently_used: List[str],
    max_switches: int,
) -> Optional[Subject]:
    usable = [s for s in candidates if remaining_minutes.get(s.name, 0) > 0]
    if not usable:
        return None

    # Penalize switching too frequently.
    switch_penalty = 0.35 if len(set(recently_used)) >= max_switches else 1.0

    best: Tuple[float, Subject] | None = None
    for s in usable:
        base = weights.get(s.name, 1.0)
        # Place hard subjects into high energy slots.
        hardness = (s.difficulty - 1) / 4.0  # 0..1
        energy_fit = 1.0 + ((energy_score - 0.5) * (0.9 * hardness))
        # Promote continuity if same as last.
        continuity = 1.15 if (recently_used and recently_used[-1] == s.name) else 1.0
        # If low energy, slightly prefer easier subjects.
        ease_boost = 1.0 + ((0.55 - energy_score) * (0.5 * (1.0 - hardness)))
        score = base * energy_fit * continuity * ease_boost * switch_penalty
        if best is None or score > best[0]:
            best = (score, s)
    return best[1] if best else None


def _allocate_minutes(
    subjects: List[Subject], cfg: PlannerConfig, day: dt.date
) -> Dict[str, int]:
    """
    Convert weekly_hours to a daily target minutes budget.
    If exam is soon, scale up.
    """
    out: Dict[str, int] = {}
    for s in subjects:
        base_daily = (s.weekly_hours * 60.0) / 7.0
        scale = 1.0
        if s.exam_date is not None:
            days_left = (s.exam_date - day).days
            if days_left <= 3:
                scale = 1.6
            elif days_left <= 7:
                scale = 1.3
            elif days_left <= 14:
                scale = 1.15
        out[s.name] = max(0, int(round(base_daily * scale)))
    return out


def build_plan(
    subjects: List[Subject], cfg: PlannerConfig, start_day: Optional[dt.date] = None
) -> List[StudyBlock]:
    if not subjects:
        return []

    day0 = start_day or _today_local()
    blocks: List[StudyBlock] = []

    for offset in range(cfg.horizon_days):
        day = day0 + dt.timedelta(days=offset)
        slots = _generate_study_slots(cfg, day)
        if not slots:
            continue

        day_weights = {s.name: w for s, w in _weighted_subject_order(subjects, day)}
        remaining = _allocate_minutes(subjects, cfg, day)
        energy_buckets = _energy_slots(cfg, day)

        recent: List[str] = []
        for slot_start, slot_end in slots:
            slot_minutes = max(1, _minutes_between(slot_start, slot_end))
            # Map slot to an energy score using buckets.
            energy_score = 0.5
            for bs, be, score in energy_buckets:
                if bs <= slot_start < be:
                    energy_score = score
                    break

            chosen = _pick_subject(
                candidates=subjects,
                weights=day_weights,
                remaining_minutes=remaining,
                energy_score=energy_score,
                recently_used=recent,
                max_switches=cfg.max_subject_switches_per_day,
            )
            if chosen is None:
                continue

            allocate = min(slot_minutes, remaining.get(chosen.name, 0))
            if allocate <= 0:
                continue

            study_end = slot_start + dt.timedelta(minutes=allocate)
            blocks.append(
                StudyBlock(
                    start=slot_start,
                    end=study_end,
                    subject=chosen.name,
                    kind="study",
                    notes=f"Focus: {cfg.pomodoro_minutes}m then {cfg.break_minutes}m break",
                )
            )
            remaining[chosen.name] = max(0, remaining.get(chosen.name, 0) - allocate)
            recent.append(chosen.name)

            # Schedule quick spaced-repetition reviews.
            for days_after, minutes in ((1, 10), (3, 10)):
                review_day = day + dt.timedelta(days=days_after)
                avail = _availability_for_day(cfg, review_day)
                review_start = _datetime_on(review_day, avail.start)
                review_end = review_start + dt.timedelta(minutes=minutes)
                blocks.append(
                    StudyBlock(
                        start=review_start,
                        end=review_end,
                        subject=chosen.name,
                        kind="review",
                        notes="Spaced repetition quick review",
                    )
                )

    blocks.sort(key=lambda b: (b.start, b.kind != "review"))
    return _dedupe_overlaps(blocks)


def _dedupe_overlaps(blocks: List[StudyBlock]) -> List[StudyBlock]:
    """
    Removes exact-duplicate review blocks and basic overlaps on the same day/time.
    """
    seen = set()
    out: List[StudyBlock] = []
    for b in blocks:
        key = (b.start, b.end, b.subject, b.kind)
        if key in seen:
            continue
        seen.add(key)
        out.append(b)

    # If multiple reviews start at the same time, keep the first few and shift others slightly.
    out.sort(key=lambda b: b.start)
    shifted: List[StudyBlock] = []
    used_starts: Dict[dt.datetime, int] = {}
    for b in out:
        if b.kind != "review":
            shifted.append(b)
            continue
        count = used_starts.get(b.start, 0)
        used_starts[b.start] = count + 1
        if count == 0:
            shifted.append(b)
        else:
            delta = dt.timedelta(minutes=10 * count)
            shifted.append(
                dataclasses.replace(b, start=b.start + delta, end=b.end + delta)
            )
    return shifted


def format_plan(blocks: List[StudyBlock], tz_note: str = "local") -> str:
    if not blocks:
        return "No study blocks generated. Add subjects and availability."

    lines: List[str] = []
    current_day: Optional[dt.date] = None
    for b in blocks:
        day = b.start.date()
        if current_day != day:
            current_day = day
            lines.append("")
            lines.append(day.isoformat() + f" ({tz_note})")
            lines.append("-" * 60)
        start_s = b.start.strftime("%H:%M")
        end_s = b.end.strftime("%H:%M")
        tag = "REV" if b.kind == "review" else "STUDY"
        lines.append(f"{start_s}-{end_s}  [{tag:5}]  {b.subject}  {b.notes}".rstrip())
    return "\n".join(lines).lstrip("\n")


def ai_tips(subjects: List[Subject], cfg: PlannerConfig) -> str:
    """
    Lightweight 'AI' coaching without external dependencies.
    If you later add an LLM call, plug it in here.
    """
    tips: List[str] = []
    hard = sorted(subjects, key=lambda s: (s.difficulty, s.priority), reverse=True)[:2]
    urgent = sorted(
        [s for s in subjects if s.exam_date is not None],
        key=lambda s: s.exam_date or _today_local(),
    )[:2]

    tips.append("Use 2-minute rule: start with a tiny step.")
    if cfg.focus_time != "balanced":
        tips.append(f"Protect your {cfg.focus_time} sessions for the hardest topics.")
    if hard:
        tips.append(f"Hard focus picks: {', '.join(s.name for s in hard)}.")
    if urgent:
        tips.append(
            f"Nearest exams: {', '.join(f'{s.name} ({s.exam_date})' for s in urgent)}."
        )
    tips.append("End each session with a 3-line summary + 3 questions.")
    tips.append("If distracted: write it down, resume, handle later.")
    return "\n".join(f"- {t}" for t in tips)


def _prompt(text: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    value = input(text + suffix + ": ").strip()
    return value if value else (default or "")


def interactive_subjects() -> List[Subject]:
    subjects: List[Subject] = []
    print("Enter your subjects. Leave name empty to finish.\n")
    while True:
        name = _prompt("Subject name", default="").strip()
        if not name:
            break
        priority = _clamp_int(int(_prompt("Priority 1-5", default="3")), 1, 5)
        difficulty = _clamp_int(int(_prompt("Difficulty 1-5", default="3")), 1, 5)
        weekly_hours = float(_prompt("Weekly hours target", default="5"))
        exam_date_s = _prompt("Exam date (YYYY-MM-DD) optional", default="")
        exam_date = _parse_date(exam_date_s) if exam_date_s else None
        subjects.append(
            Subject(
                name=name,
                priority=priority,
                difficulty=difficulty,
                weekly_hours=weekly_hours,
                exam_date=exam_date,
            )
        )
        print("")
    return subjects


def interactive_config() -> PlannerConfig:
    print("Planner settings (press Enter to accept defaults).\n")
    horizon_days = int(_prompt("Days to plan ahead", default="14"))
    pomodoro_minutes = int(_prompt("Study block minutes", default="50"))
    break_minutes = int(_prompt("Break minutes", default="10"))
    max_switches = int(_prompt("Max subject switches/day", default="3"))
    focus_time = _prompt(
        "Best focus time (morning/afternoon/evening/balanced)", default="balanced"
    ).lower()
    if focus_time not in ("morning", "afternoon", "evening", "balanced"):
        focus_time = "balanced"

    wd_start = _parse_time(_prompt("Weekday start (HH:MM)", default="17:00"))
    wd_end = _parse_time(_prompt("Weekday end (HH:MM)", default="21:00"))
    we_start = _parse_time(_prompt("Weekend start (HH:MM)", default="10:00"))
    we_end = _parse_time(_prompt("Weekend end (HH:MM)", default="16:00"))

    return PlannerConfig(
        horizon_days=max(1, horizon_days),
        pomodoro_minutes=max(15, pomodoro_minutes),
        break_minutes=max(0, break_minutes),
        max_subject_switches_per_day=max(1, max_switches),
        focus_time=focus_time,
        availability_weekday=DailyAvailability(start=wd_start, end=wd_end),
        availability_weekend=DailyAvailability(start=we_start, end=we_end),
    )


def _subjects_from_json(path: str) -> List[Subject]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    out: List[Subject] = []
    for item in data.get("subjects", []):
        out.append(
            Subject(
                name=str(item["name"]),
                priority=_clamp_int(int(item.get("priority", 3)), 1, 5),
                difficulty=_clamp_int(int(item.get("difficulty", 3)), 1, 5),
                weekly_hours=float(item.get("weekly_hours", 5)),
                exam_date=_parse_date(str(item.get("exam_date", "")).strip())
                if str(item.get("exam_date", "")).strip()
                else None,
            )
        )
    return out


def _config_from_json(path: str) -> PlannerConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    cfg = data.get("config", {})

    def t(key: str, default: str) -> dt.time:
        return _parse_time(str(cfg.get(key, default)))

    return PlannerConfig(
        horizon_days=int(cfg.get("horizon_days", 14)),
        pomodoro_minutes=int(cfg.get("pomodoro_minutes", 50)),
        break_minutes=int(cfg.get("break_minutes", 10)),
        max_subject_switches_per_day=int(cfg.get("max_subject_switches_per_day", 3)),
        focus_time=str(cfg.get("focus_time", "balanced")),
        availability_weekday=DailyAvailability(
            start=t("weekday_start", "17:00"), end=t("weekday_end", "21:00")
        ),
        availability_weekend=DailyAvailability(
            start=t("weekend_start", "10:00"), end=t("weekend_end", "16:00")
        ),
    )


def _json_dumps(obj: object) -> bytes:
    return json.dumps(obj, ensure_ascii=True, indent=2).encode("utf-8")


def _blocks_to_payload(blocks: List[StudyBlock]) -> Dict[str, object]:
    items: List[Dict[str, str]] = []
    for b in blocks:
        items.append(
            {
                "start": b.start.isoformat(timespec="minutes"),
                "end": b.end.isoformat(timespec="minutes"),
                "subject": b.subject,
                "kind": b.kind,
                "notes": b.notes,
                "day": b.start.date().isoformat(),
                "start_hm": b.start.strftime("%H:%M"),
                "end_hm": b.end.strftime("%H:%M"),
            }
        )
    return {"blocks": items, "formatted": format_plan(blocks)}


_INDEX_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Study Planner</title>
    <link rel="stylesheet" href="/app.css" />
  </head>
  <body>
    <div class="bg">
      <div class="orb o1"></div>
      <div class="orb o2"></div>
      <div class="orb o3"></div>
    </div>

    <header class="top">
      <div class="brand">
        <div class="mark">SP</div>
        <div>
          <div class="title">Study Planner</div>
          <div class="subtitle">A focused, AI-style schedule builder (local)</div>
        </div>
      </div>
      <div class="actions">
        <button id="btnSample" class="btn ghost">Load sample</button>
        <button id="btnImport" class="btn ghost">Import</button>
        <button id="btnExport" class="btn ghost">Export</button>
        <button id="btnGenerate" class="btn primary">Generate plan</button>
      </div>
    </header>

    <main class="grid">
      <section class="card">
        <h2>Subjects</h2>
        <p class="muted">Add subjects, weekly targets, difficulty, and (optional) exam dates.</p>

        <div id="subjects" class="subjects"></div>

        <div class="row">
          <button id="btnAddSubject" class="btn">+ Add subject</button>
          <div class="hint">Tip: Keep weekly hours realistic.</div>
        </div>
      </section>

      <section class="card">
        <h2>Schedule settings</h2>
        <div class="form">
          <label>Days ahead
            <input id="horizonDays" type="number" min="1" value="14" />
          </label>
          <label>Study minutes
            <input id="pomodoroMinutes" type="number" min="15" value="50" />
          </label>
          <label>Break minutes
            <input id="breakMinutes" type="number" min="0" value="10" />
          </label>
          <label>Max switches/day
            <input id="maxSwitches" type="number" min="1" value="3" />
          </label>
          <label>Best focus time
            <select id="focusTime">
              <option value="balanced">Balanced</option>
              <option value="morning">Morning</option>
              <option value="afternoon">Afternoon</option>
              <option value="evening">Evening</option>
            </select>
          </label>
        </div>

        <h3>Availability</h3>
        <div class="form two">
          <label>Weekday start
            <input id="weekdayStart" type="time" value="17:00" />
          </label>
          <label>Weekday end
            <input id="weekdayEnd" type="time" value="21:00" />
          </label>
          <label>Weekend start
            <input id="weekendStart" type="time" value="10:00" />
          </label>
          <label>Weekend end
            <input id="weekendEnd" type="time" value="16:00" />
          </label>
        </div>
      </section>

      <section class="card wide">
        <div class="split">
          <div>
            <h2>Plan</h2>
            <p class="muted">Generated blocks appear here (study + spaced reviews).</p>
          </div>
          <div class="right">
            <label class="inline">Start date
              <input id="startDate" type="date" />
            </label>
          </div>
        </div>

        <div id="status" class="status">Ready.</div>
        <div id="plan" class="plan"></div>
      </section>

      <section class="card wide">
        <h2>AI coaching</h2>
        <div id="tips" class="tips muted">Generate a plan to see tips.</div>
      </section>
    </main>

    <footer class="foot">
      Runs locally on your computer. No accounts. No uploads.
    </footer>

    <script src="/app.js"></script>
  </body>
</html>
"""


_APP_CSS = """
:root{
  --bg0:#0b1020;
  --bg1:#101a34;
  --card:rgba(255,255,255,0.08);
  --stroke:rgba(255,255,255,0.14);
  --text:#f2f5ff;
  --muted:rgba(242,245,255,0.72);
  --accent:#ffcc66;
  --accent2:#6ee7ff;
  --shadow: 0 18px 60px rgba(0,0,0,0.45);
}
*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0;
  color:var(--text);
  font-family: "Palatino Linotype", "Book Antiqua", Palatino, serif;
  background: radial-gradient(1200px 800px at 20% 10%, #1a2a55 0%, transparent 55%),
              radial-gradient(900px 700px at 80% 10%, #2b1f45 0%, transparent 60%),
              linear-gradient(160deg, var(--bg0), var(--bg1));
  overflow-x:hidden;
}
.bg{position:fixed; inset:0; pointer-events:none; z-index:-1;}
.orb{
  position:absolute; width:520px; height:520px; border-radius:50%;
  filter: blur(40px);
  opacity:0.35;
  transform: translate3d(0,0,0);
  animation: float 10s ease-in-out infinite;
}
.o1{left:-160px; top:120px; background: radial-gradient(circle at 30% 30%, var(--accent2), transparent 55%);}
.o2{right:-180px; top:40px; background: radial-gradient(circle at 30% 30%, #ff6ea9, transparent 55%); animation-duration: 12s;}
.o3{left:18%; bottom:-260px; background: radial-gradient(circle at 30% 30%, var(--accent), transparent 55%); animation-duration: 14s;}
@keyframes float{
  0%,100%{ transform: translate(0,0) scale(1); }
  50%{ transform: translate(18px,-14px) scale(1.03); }
}

.top{
  max-width: 1120px;
  margin: 24px auto 0;
  padding: 12px 18px;
  display:flex; align-items:center; justify-content:space-between;
  backdrop-filter: blur(10px);
}
.brand{display:flex; gap:14px; align-items:center}
.mark{
  width:46px; height:46px; border-radius:14px;
  display:grid; place-items:center;
  background: linear-gradient(135deg, rgba(255,204,102,0.22), rgba(110,231,255,0.16));
  border:1px solid var(--stroke);
  box-shadow: var(--shadow);
  font-weight:700;
}
.title{font-size:22px; letter-spacing:0.4px}
.subtitle{font-size:13px; color:var(--muted)}
.actions{display:flex; gap:10px; align-items:center}
.btn{
  border:1px solid var(--stroke);
  background: rgba(255,255,255,0.06);
  color: var(--text);
  padding:10px 12px;
  border-radius: 14px;
  cursor:pointer;
  transition: transform 120ms ease, background 120ms ease;
}
.btn:hover{ transform: translateY(-1px); background: rgba(255,255,255,0.10); }
.btn.primary{
  border-color: rgba(255,204,102,0.45);
  background: linear-gradient(135deg, rgba(255,204,102,0.22), rgba(255,204,102,0.08));
}
.btn.ghost{ background: transparent; }

.grid{
  max-width:1120px;
  margin: 10px auto 28px;
  padding: 0 18px;
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap:16px;
}
.card{
  background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.05));
  border:1px solid var(--stroke);
  border-radius: 22px;
  padding: 16px 16px 14px;
  box-shadow: var(--shadow);
  animation: fadeUp 380ms ease both;
}
.card.wide{ grid-column: 1 / -1; }
@keyframes fadeUp{
  from{ opacity:0; transform: translateY(10px); }
  to{ opacity:1; transform: translateY(0); }
}
h2{margin:0 0 6px; font-size:18px}
h3{margin:12px 0 8px; font-size:15px; color: rgba(242,245,255,0.9)}
.muted{color:var(--muted)}
.row{display:flex; align-items:center; justify-content:space-between; gap:12px; margin-top:10px}
.hint{font-size:12px; color: rgba(242,245,255,0.6)}

.subjects{display:flex; flex-direction:column; gap:10px; margin-top:12px}
.subject{
  display:grid;
  grid-template-columns: 1.5fr 0.7fr 0.7fr 0.9fr 1fr auto;
  gap:10px;
  align-items:end;
  padding:12px;
  border-radius:18px;
  border:1px solid rgba(255,255,255,0.12);
  background: rgba(0,0,0,0.10);
}
.subject label{display:flex; flex-direction:column; gap:6px; font-size:12px; color: rgba(242,245,255,0.75)}
input,select{
  width:100%;
  padding:10px 10px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,0.16);
  background: rgba(255,255,255,0.06);
  color: var(--text);
  outline:none;
}
input:focus,select:focus{ border-color: rgba(110,231,255,0.45); }
.subject .remove{
  height:40px;
  border-radius: 14px;
  border:1px solid rgba(255,110,169,0.35);
  background: rgba(255,110,169,0.10);
}
.form{display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:10px}
.form.two{grid-template-columns: 1fr 1fr}
.form label{display:flex; flex-direction:column; gap:6px; font-size:12px; color: rgba(242,245,255,0.75)}

.split{display:flex; justify-content:space-between; gap:16px; align-items:flex-end}
.right{display:flex; gap:10px; align-items:center}
.inline{display:flex; gap:8px; align-items:center; font-size:12px; color: rgba(242,245,255,0.75)}
.inline input{width:auto; min-width: 160px}

.status{
  margin-top:10px;
  padding:10px 12px;
  border-radius: 16px;
  border:1px solid rgba(255,255,255,0.12);
  background: rgba(0,0,0,0.18);
  font-size: 13px;
  color: rgba(242,245,255,0.85);
}
.plan{margin-top:12px; display:flex; flex-direction:column; gap:12px}
.day{
  border-radius: 20px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(0,0,0,0.16);
  overflow:hidden;
}
.dayHead{
  display:flex; justify-content:space-between; align-items:center;
  padding:12px 14px;
  background: linear-gradient(90deg, rgba(255,204,102,0.10), rgba(110,231,255,0.08));
  border-bottom: 1px solid rgba(255,255,255,0.10);
}
.dayTitle{font-weight:700; letter-spacing:0.3px}
.pill{
  font-size:12px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.16);
  background: rgba(255,255,255,0.06);
  color: rgba(242,245,255,0.9);
}
.blocks{display:flex; flex-direction:column}
.block{
  display:grid;
  grid-template-columns: 130px 1fr 90px 44px;
  gap:12px;
  padding:10px 14px;
  border-top:1px solid rgba(255,255,255,0.08);
  transform: translateX(var(--jitter-x, 0px)) translateY(var(--jitter-y, 0px)) rotate(var(--tilt, 0deg));
  transition: transform 240ms ease, background 220ms ease;
  animation: settleIn 420ms ease both;
  animation-delay: var(--delay, 0ms);
}
.block:first-child{border-top:none}
.block:hover{
  transform: translateX(0) translateY(0) rotate(0deg);
  background: rgba(255,255,255,0.04);
}
@keyframes settleIn{
  from{ opacity:0; transform: translateX(calc(var(--jitter-x, 0px) * 2.2)) translateY(8px) rotate(calc(var(--tilt, 0deg) * 1.8)); }
  to{ opacity:1; transform: translateX(var(--jitter-x, 0px)) translateY(var(--jitter-y, 0px)) rotate(var(--tilt, 0deg)); }
}
.time{font-variant-numeric: tabular-nums; color: rgba(242,245,255,0.9)}
.subj{font-weight:700}
.note{font-size:12px; color: rgba(242,245,255,0.65); margin-top:2px}
.kind{
  justify-self:end;
  align-self:start;
  font-size:12px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.14);
  background: rgba(255,255,255,0.06);
}
.kind.study{border-color: rgba(255,204,102,0.35)}
.kind.review{border-color: rgba(110,231,255,0.35)}
.done{
  justify-self:end;
  align-self:start;
  width:34px;
  height:34px;
  border-radius: 999px;
  border: 1px solid rgba(110,231,255,0.35);
  background: rgba(110,231,255,0.12);
  color: var(--text);
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
}
.done:hover{ background: rgba(110,231,255,0.24); }

.tips{white-space:pre-wrap; line-height:1.35}
.foot{
  max-width:1120px;
  margin: 0 auto 24px;
  padding: 0 18px;
  color: rgba(242,245,255,0.55);
  font-size: 12px;
}

@media (max-width: 900px){
  .grid{grid-template-columns: 1fr}
  .subject{grid-template-columns: 1fr 1fr}
  .block{grid-template-columns: 1fr; gap:6px}
  .kind{justify-self:start}
  .actions{flex-wrap:wrap; justify-content:flex-end}
}
"""


_APP_JS = r"""
const elSubjects = document.getElementById('subjects');
const elTips = document.getElementById('tips');
const elPlan = document.getElementById('plan');
const elStatus = document.getElementById('status');

const elHorizonDays = document.getElementById('horizonDays');
const elPomodoroMinutes = document.getElementById('pomodoroMinutes');
const elBreakMinutes = document.getElementById('breakMinutes');
const elMaxSwitches = document.getElementById('maxSwitches');
const elFocusTime = document.getElementById('focusTime');

const elWeekdayStart = document.getElementById('weekdayStart');
const elWeekdayEnd = document.getElementById('weekdayEnd');
const elWeekendStart = document.getElementById('weekendStart');
const elWeekendEnd = document.getElementById('weekendEnd');

const elStartDate = document.getElementById('startDate');
const btnAddSubject = document.getElementById('btnAddSubject');
const btnGenerate = document.getElementById('btnGenerate');
const btnSample = document.getElementById('btnSample');
const btnImport = document.getElementById('btnImport');
const btnExport = document.getElementById('btnExport');
let lastGeneratedPlan = null;
let lastGeneratedTips = '';
const STORAGE_KEY = 'study_planner_state_v1';

function todayISO(){
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth()+1).padStart(2,'0');
  const dd = String(d.getDate()).padStart(2,'0');
  return `${yyyy}-${mm}-${dd}`;
}
elStartDate.value = todayISO();

function subjectRow(data){
  const wrap = document.createElement('div');
  wrap.className = 'subject';
  wrap.innerHTML = `
    <label>Name
      <input class="s_name" placeholder="e.g. Biology" value="${data?.name ?? ''}"/>
    </label>
    <label>Priority (1-5)
      <input class="s_priority" type="number" min="1" max="5" value="${data?.priority ?? 3}"/>
    </label>
    <label>Difficulty (1-5)
      <input class="s_difficulty" type="number" min="1" max="5" value="${data?.difficulty ?? 3}"/>
    </label>
    <label>Weekly hours
      <input class="s_hours" type="number" min="0" step="0.5" value="${data?.weekly_hours ?? 5}"/>
    </label>
    <label>Exam date (optional)
      <input class="s_exam" type="date" value="${data?.exam_date ?? ''}"/>
    </label>
    <button class="btn remove" title="Remove">Remove</button>
  `;
  wrap.querySelector('.remove').addEventListener('click', () => wrap.remove());
  return wrap;
}

function addSubject(data){
  elSubjects.appendChild(subjectRow(data));
}

function loadSample(){
  elSubjects.innerHTML = '';
  addSubject({name:'Math', priority:5, difficulty:4, weekly_hours:6, exam_date:''});
  addSubject({name:'English', priority:3, difficulty:2, weekly_hours:3, exam_date:''});
  addSubject({name:'Chemistry', priority:4, difficulty:5, weekly_hours:5, exam_date:''});
  elHorizonDays.value = 14;
  elPomodoroMinutes.value = 50;
  elBreakMinutes.value = 10;
  elMaxSwitches.value = 3;
  elFocusTime.value = 'balanced';
  elWeekdayStart.value = '17:00';
  elWeekdayEnd.value = '21:00';
  elWeekendStart.value = '10:00';
  elWeekendEnd.value = '16:00';
}

function collect(){
  const rows = Array.from(elSubjects.querySelectorAll('.subject'));
  const subjects = rows.map(r => ({
    name: r.querySelector('.s_name').value.trim(),
    priority: Number(r.querySelector('.s_priority').value || 3),
    difficulty: Number(r.querySelector('.s_difficulty').value || 3),
    weekly_hours: Number(r.querySelector('.s_hours').value || 0),
    exam_date: (r.querySelector('.s_exam').value || '').trim()
  })).filter(s => s.name.length > 0);

  const config = {
    horizon_days: Number(elHorizonDays.value || 14),
    pomodoro_minutes: Number(elPomodoroMinutes.value || 50),
    break_minutes: Number(elBreakMinutes.value || 10),
    max_subject_switches_per_day: Number(elMaxSwitches.value || 3),
    focus_time: elFocusTime.value,
    weekday_start: elWeekdayStart.value,
    weekday_end: elWeekdayEnd.value,
    weekend_start: elWeekendStart.value,
    weekend_end: elWeekendEnd.value
  };

  const start = (elStartDate.value || '').trim();
  return {subjects, config, start};
}

function setStatus(msg){
  elStatus.textContent = msg;
}

function saveState(){
  try{
    const payload = collect();
    payload.plan = lastGeneratedPlan;
    payload.tips = lastGeneratedTips;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  }catch(e){}
}

function loadState(){
  try{
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return false;
    const payload = JSON.parse(raw);
    applyData(payload);
    return true;
  }catch(e){
    return false;
  }
}

function applyData(payload){
  const subjects = Array.isArray(payload?.subjects) ? payload.subjects : [];
  const config = payload?.config || {};
  const start = String(payload?.start || '').trim();

  elSubjects.innerHTML = '';
  for (const s of subjects){
    addSubject({
      name: s?.name ?? '',
      priority: Number(s?.priority ?? 3),
      difficulty: Number(s?.difficulty ?? 3),
      weekly_hours: Number(s?.weekly_hours ?? 5),
      exam_date: String(s?.exam_date ?? '').trim()
    });
  }
  if (subjects.length === 0){
    addSubject();
  }

  if (config.horizon_days != null) elHorizonDays.value = Number(config.horizon_days);
  if (config.pomodoro_minutes != null) elPomodoroMinutes.value = Number(config.pomodoro_minutes);
  if (config.break_minutes != null) elBreakMinutes.value = Number(config.break_minutes);
  if (config.max_subject_switches_per_day != null) elMaxSwitches.value = Number(config.max_subject_switches_per_day);
  if (config.focus_time) elFocusTime.value = String(config.focus_time);
  if (config.weekday_start) elWeekdayStart.value = String(config.weekday_start);
  if (config.weekday_end) elWeekdayEnd.value = String(config.weekday_end);
  if (config.weekend_start) elWeekendStart.value = String(config.weekend_start);
  if (config.weekend_end) elWeekendEnd.value = String(config.weekend_end);
  elStartDate.value = start || todayISO();

  const importedPlan = payload?.plan;
  if (importedPlan && Array.isArray(importedPlan.blocks)){
    lastGeneratedPlan = importedPlan;
    renderPlan(importedPlan);
    const tips = String(payload?.tips || '').trim();
    lastGeneratedTips = tips;
    elTips.textContent = tips || 'Generate a plan to see tips.';
  }else{
    lastGeneratedPlan = null;
    lastGeneratedTips = '';
    elPlan.innerHTML = '';
    elTips.textContent = 'Generate a plan to see tips.';
  }
}

function groupByDay(blocks){
  const map = new Map();
  for (const b of blocks){
    if (!map.has(b.day)) map.set(b.day, []);
    map.get(b.day).push(b);
  }
  return Array.from(map.entries()).sort((a,b) => a[0].localeCompare(b[0]));
}

function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'
  })[c]);
}

function renderPlan(plan){
  elPlan.innerHTML = '';
  const groups = groupByDay(plan.blocks || []);
  if (groups.length === 0){
    elPlan.innerHTML = '<div class="muted">No blocks. Add availability or subjects.</div>';
    return;
  }

  for (const [day, blocks] of groups){
    const dayEl = document.createElement('div');
    dayEl.className = 'day';
    const studyCount = blocks.filter(b => b.kind === 'study').length;
    const reviewCount = blocks.filter(b => b.kind === 'review').length;
    dayEl.innerHTML = `
      <div class="dayHead">
        <div class="dayTitle">${day}</div>
        <div class="pill">${studyCount} study / ${reviewCount} review</div>
      </div>
      <div class="blocks"></div>
    `;
    const list = dayEl.querySelector('.blocks');
    blocks.sort((a,b) => a.start.localeCompare(b.start));
    for (let i = 0; i < blocks.length; i++){
      const b = blocks[i];
      const blockEl = document.createElement('div');
      blockEl.className = 'block';
      const k = b.kind === 'review' ? 'review' : 'study';
      const jitterX = (Math.random() * 6 - 3).toFixed(2);
      const jitterY = (Math.random() * 4 - 2).toFixed(2);
      const tilt = (Math.random() * 1.2 - 0.6).toFixed(2);
      const delay = Math.min(320, i * 24);
      blockEl.style.setProperty('--jitter-x', `${jitterX}px`);
      blockEl.style.setProperty('--jitter-y', `${jitterY}px`);
      blockEl.style.setProperty('--tilt', `${tilt}deg`);
      blockEl.style.setProperty('--delay', `${delay}ms`);
      blockEl.innerHTML = `
        <div class="time">${b.start_hm} - ${b.end_hm}</div>
        <div>
          <div class="subj">${escapeHtml(b.subject)}</div>
          <div class="note">${escapeHtml(b.notes || '')}</div>
        </div>
        <div class="kind ${k}">${k.toUpperCase()}</div>
        <button class="done" title="Mark studied">✓</button>
      `;
      blockEl.querySelector('.done').addEventListener('click', () => {
        if (!lastGeneratedPlan || !Array.isArray(lastGeneratedPlan.blocks)) return;
        lastGeneratedPlan.blocks = lastGeneratedPlan.blocks.filter(x =>
          !(
            x.start === b.start &&
            x.end === b.end &&
            x.subject === b.subject &&
            x.kind === b.kind &&
            (x.notes || '') === (b.notes || '')
          )
        );
        renderPlan(lastGeneratedPlan);
        saveState();
        setStatus('Block marked studied and removed.');
      });
      list.appendChild(blockEl);
    }
    elPlan.appendChild(dayEl);
  }
}

async function generate(){
  const payload = collect();
  if (payload.subjects.length === 0){
    setStatus('Add at least one subject.');
    return;
  }
  setStatus('Generating...');
  btnGenerate.disabled = true;
  try{
    const res = await fetch('/api/plan', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok){
      setStatus(data.error || 'Error generating plan.');
      return;
    }
    setStatus('Done.');
    lastGeneratedPlan = data.plan || null;
    lastGeneratedTips = data.tips || '';
    renderPlan(data.plan);
    elTips.textContent = data.tips || '';
    saveState();
  }catch(e){
    setStatus('Failed. Is the server running?');
  }finally{
    btnGenerate.disabled = false;
  }
}

btnGenerate.addEventListener('click', generate);
btnSample.addEventListener('click', () => { loadSample(); setStatus('Sample loaded.'); });
btnAddSubject.addEventListener('click', () => addSubject());
btnExport.addEventListener('click', () => {
  const payload = collect();
  payload.plan = lastGeneratedPlan;
  payload.tips = lastGeneratedTips;
  const blob = new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const stamp = todayISO().replaceAll('-', '');
  a.href = url;
  a.download = `study-planner-${stamp}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
  setStatus('Planner exported.');
});
btnImport.addEventListener('click', () => {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'application/json,.json';
  input.addEventListener('change', async () => {
    const file = input.files && input.files[0];
    if (!file) return;
    try{
      const text = await file.text();
      const payload = JSON.parse(text);
      applyData(payload);
      saveState();
      setStatus('Planner imported.');
    }catch(e){
      setStatus('Import failed: invalid JSON file.');
    }
  });
  input.click();
});

if (!loadState()){
  loadSample();
}
"""


class _StudyPlannerHandler(http.server.BaseHTTPRequestHandler):
    server_version = "StudyPlanner/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stdout.write(
            "%s - - [%s] %s\n"
            % (self.client_address[0], self.log_date_time_string(), fmt % args)
        )

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            self._send(200, _INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if self.path == "/app.css":
            self._send(200, _APP_CSS.encode("utf-8"), "text/css; charset=utf-8")
            return
        if self.path == "/app.js":
            self._send(
                200, _APP_JS.encode("utf-8"), "application/javascript; charset=utf-8"
            )
            return
        self._send(404, b"Not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        if self.path != "/api/plan":
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            data = json.loads(raw.decode("utf-8"))

            subjects: List[Subject] = []
            for item in data.get("subjects") or []:
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

            cfg_in = data.get("config") or {}

            def _t(key: str, default: str) -> dt.time:
                return _parse_time(str(cfg_in.get(key, default)))

            cfg = PlannerConfig(
                horizon_days=max(1, int(cfg_in.get("horizon_days", 14))),
                pomodoro_minutes=max(15, int(cfg_in.get("pomodoro_minutes", 50))),
                break_minutes=max(0, int(cfg_in.get("break_minutes", 10))),
                max_subject_switches_per_day=max(
                    1, int(cfg_in.get("max_subject_switches_per_day", 3))
                ),
                focus_time=str(cfg_in.get("focus_time", "balanced")).lower(),
                availability_weekday=DailyAvailability(
                    start=_t("weekday_start", "17:00"),
                    end=_t("weekday_end", "21:00"),
                ),
                availability_weekend=DailyAvailability(
                    start=_t("weekend_start", "10:00"),
                    end=_t("weekend_end", "16:00"),
                ),
            )

            start_s = str(data.get("start", "")).strip()
            start_day = _parse_date(start_s) if start_s else None

            plan = build_plan(subjects, cfg, start_day=start_day)
            payload = {"plan": _blocks_to_payload(plan), "tips": ai_tips(subjects, cfg)}
            self._send(200, _json_dumps(payload), "application/json; charset=utf-8")
        except Exception as e:
            self._send(
                400, _json_dumps({"error": str(e)}), "application/json; charset=utf-8"
            )


def run_web_ui(port: int = 8000, open_browser: bool = True) -> int:
    addr = ("127.0.0.1", int(port))
    httpd = socketserver.ThreadingTCPServer(addr, _StudyPlannerHandler)
    httpd.allow_reuse_address = True
    url = f"http://{addr[0]}:{addr[1]}/"
    print(f"Study Planner Web UI running on {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        try:
            webbrowser.open(url, new=2, autoraise=True)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="AI-style Study Planner (local heuristic)."
    )
    parser.add_argument(
        "--interactive", action="store_true", help="Prompt for subjects + settings."
    )
    parser.add_argument(
        "--json", dest="json_path", help="Load subjects/config from JSON file."
    )
    parser.add_argument("--days", type=int, default=None, help="Override horizon days.")
    parser.add_argument(
        "--start", default=None, help="Start date YYYY-MM-DD (default: today)."
    )
    parser.add_argument("--web", action="store_true", help="Run local web UI.")
    parser.add_argument(
        "--cli", action="store_true", help="Run CLI mode instead of web UI."
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open browser in web mode.",
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Web UI port (default: 8000)."
    )
    args = parser.parse_args(argv)

    if args.web or not args.cli:
        return run_web_ui(port=args.port, open_browser=not args.no_browser)

    subjects: List[Subject]
    cfg: PlannerConfig
    if args.json_path:
        subjects = _subjects_from_json(args.json_path)
        cfg = _config_from_json(args.json_path)
    else:
        subjects = (
            interactive_subjects() if args.interactive or sys.stdin.isatty() else []
        )
        cfg = (
            interactive_config()
            if args.interactive or sys.stdin.isatty()
            else PlannerConfig(
                horizon_days=14,
                pomodoro_minutes=50,
                break_minutes=10,
                max_subject_switches_per_day=3,
                focus_time="balanced",
                availability_weekday=DailyAvailability(
                    start=dt.time(17, 0), end=dt.time(21, 0)
                ),
                availability_weekend=DailyAvailability(
                    start=dt.time(10, 0), end=dt.time(16, 0)
                ),
            )
        )

    if not subjects:
        print(
            "No subjects provided. Run with `--interactive` or `--json yourfile.json` or `--web`."
        )
        return 2

    if args.days is not None:
        cfg = dataclasses.replace(cfg, horizon_days=max(1, args.days))

    start_day = _parse_date(args.start) if args.start else None
    plan = build_plan(subjects, cfg, start_day=start_day)

    print("")
    print(format_plan(plan))
    print("\nAI Coaching Tips")
    print("-" * 60)
    print(ai_tips(subjects, cfg))
    print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
