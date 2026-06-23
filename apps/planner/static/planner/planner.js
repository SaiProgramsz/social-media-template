(function () {
  const root = document.getElementById("plannerRoot");
  if (!root) {
    return;
  }

  const stateKey = "study_net_planner_state_v2";
  const initialPayload = JSON.parse(
    document.getElementById("plannerInitialPayload").textContent || "{}"
  );

  const elSubjects = document.getElementById("subjects");
  const elPlan = document.getElementById("plan");
  const elTips = document.getElementById("tips");
  const elStatus = document.getElementById("status");
  const elGenerated = document.getElementById("generatedPayload");
  const elEmptyPlan = document.getElementById("emptyPlan");

  const elHorizonDays = document.getElementById("horizonDays");
  const elPomodoroMinutes = document.getElementById("pomodoroMinutes");
  const elBreakMinutes = document.getElementById("breakMinutes");
  const elMaxSwitches = document.getElementById("maxSwitches");
  const elFocusTime = document.getElementById("focusTime");
  const elWeekdayStart = document.getElementById("weekdayStart");
  const elWeekdayEnd = document.getElementById("weekdayEnd");
  const elWeekendStart = document.getElementById("weekendStart");
  const elWeekendEnd = document.getElementById("weekendEnd");
  const elStartDate = document.getElementById("startDate");

  const btnAddSubject = document.getElementById("btnAddSubject");
  const btnGenerate = document.getElementById("btnGenerate");
  const btnSample = document.getElementById("btnSample");
  const btnImport = document.getElementById("btnImport");
  const btnExport = document.getElementById("btnExport");

  let lastGeneratedPlan = null;
  let lastGeneratedTips = "";

  function todayISO() {
    const date = new Date();
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, "0");
    const dd = String(date.getDate()).padStart(2, "0");
    return `${yyyy}-${mm}-${dd}`;
  }

  function setStatus(message) {
    elStatus.textContent = message;
  }

  function getCsrfToken() {
    const tokenInput = document.querySelector("#plannerCsrfForm input[name=csrfmiddlewaretoken]");
    return tokenInput ? tokenInput.value : "";
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    })[char]);
  }

  function subjectRow(data) {
    const wrap = document.createElement("div");
    wrap.className = "planner-subject";
    wrap.innerHTML = `
      <label>Name
        <input class="planner-input s_name" placeholder="e.g. Biology" value="${escapeHtml(data?.name ?? "")}"/>
      </label>
      <label>Priority
        <input class="planner-input s_priority" type="number" min="1" max="5" value="${Number(data?.priority ?? 3)}"/>
      </label>
      <label>Difficulty
        <input class="planner-input s_difficulty" type="number" min="1" max="5" value="${Number(data?.difficulty ?? 3)}"/>
      </label>
      <label>Weekly hours
        <input class="planner-input s_hours" type="number" min="0" step="0.5" value="${Number(data?.weekly_hours ?? 5)}"/>
      </label>
      <label>Exam date
        <input class="planner-input s_exam" type="date" value="${escapeHtml(data?.exam_date ?? "")}"/>
      </label>
      <button class="planner-btn remove" title="Remove" type="button">Remove</button>
    `;
    wrap.querySelector(".remove").addEventListener("click", () => wrap.remove());
    return wrap;
  }

  function addSubject(data) {
    elSubjects.appendChild(subjectRow(data));
  }

  function todayFromInitial() {
    return initialPayload?.start || todayISO();
  }

  function loadSample() {
    const sample = initialPayload || {};
    const subjects = Array.isArray(sample.subjects) ? sample.subjects : [];
    const config = sample.config || {};
    elSubjects.innerHTML = "";
    if (subjects.length) {
      subjects.forEach((subject) => addSubject(subject));
    } else {
      addSubject();
    }
    elHorizonDays.value = Number(config.horizon_days ?? 14);
    elPomodoroMinutes.value = Number(config.pomodoro_minutes ?? 50);
    elBreakMinutes.value = Number(config.break_minutes ?? 10);
    elMaxSwitches.value = Number(config.max_subject_switches_per_day ?? 3);
    elFocusTime.value = String(config.focus_time ?? "balanced");
    elWeekdayStart.value = String(config.weekday_start ?? "17:00");
    elWeekdayEnd.value = String(config.weekday_end ?? "21:00");
    elWeekendStart.value = String(config.weekend_start ?? "10:00");
    elWeekendEnd.value = String(config.weekend_end ?? "16:00");
    elStartDate.value = todayFromInitial();
    renderEmptyPlan();
    elTips.textContent = "Generate a plan to see coaching tips.";
    setStatus("Sample loaded.");
  }

  function renderEmptyPlan() {
    elPlan.innerHTML = "";
    if (elEmptyPlan) {
      elEmptyPlan.style.display = "block";
    }
  }

  function collect() {
    const rows = Array.from(elSubjects.querySelectorAll(".planner-subject"));
    const subjects = rows
      .map((row) => ({
        name: row.querySelector(".s_name").value.trim(),
        priority: Number(row.querySelector(".s_priority").value || 3),
        difficulty: Number(row.querySelector(".s_difficulty").value || 3),
        weekly_hours: Number(row.querySelector(".s_hours").value || 0),
        exam_date: (row.querySelector(".s_exam").value || "").trim(),
      }))
      .filter((subject) => subject.name.length > 0);

    return {
      subjects,
      config: {
        horizon_days: Number(elHorizonDays.value || 14),
        pomodoro_minutes: Number(elPomodoroMinutes.value || 50),
        break_minutes: Number(elBreakMinutes.value || 10),
        max_subject_switches_per_day: Number(elMaxSwitches.value || 3),
        focus_time: elFocusTime.value,
        weekday_start: elWeekdayStart.value,
        weekday_end: elWeekdayEnd.value,
        weekend_start: elWeekendStart.value,
        weekend_end: elWeekendEnd.value,
      },
      start: (elStartDate.value || "").trim(),
    };
  }

  function saveState() {
    try {
      const payload = collect();
      payload.plan = lastGeneratedPlan;
      payload.tips = lastGeneratedTips;
      localStorage.setItem(stateKey, JSON.stringify(payload));
    } catch (error) {
      // Ignore storage failures.
    }
  }

  function applyData(payload) {
    const subjects = Array.isArray(payload?.subjects) ? payload.subjects : [];
    const config = payload?.config || {};
    const start = String(payload?.start || "").trim();

    elSubjects.innerHTML = "";
    subjects.forEach((subject) => {
      addSubject({
        name: subject?.name ?? "",
        priority: Number(subject?.priority ?? 3),
        difficulty: Number(subject?.difficulty ?? 3),
        weekly_hours: Number(subject?.weekly_hours ?? 5),
        exam_date: String(subject?.exam_date ?? "").trim(),
      });
    });
    if (!subjects.length) {
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
    if (importedPlan && Array.isArray(importedPlan.blocks)) {
      lastGeneratedPlan = importedPlan;
      lastGeneratedTips = String(payload?.tips || "");
      renderPlan(importedPlan);
      elTips.textContent = lastGeneratedTips || "Generate a plan to see coaching tips.";
      if (elGenerated) {
        elGenerated.textContent = JSON.stringify(importedPlan, null, 2);
      }
    } else {
      lastGeneratedPlan = null;
      lastGeneratedTips = "";
      renderEmptyPlan();
      elTips.textContent = "Generate a plan to see coaching tips.";
      if (elGenerated) {
        elGenerated.textContent = "";
      }
    }
  }

  function groupByDay(blocks) {
    const map = new Map();
    for (const block of blocks) {
      if (!map.has(block.day)) {
        map.set(block.day, []);
      }
      map.get(block.day).push(block);
    }
    return Array.from(map.entries()).sort((left, right) => left[0].localeCompare(right[0]));
  }

  function renderPlan(plan) {
    elPlan.innerHTML = "";
    const blocks = Array.isArray(plan?.blocks) ? plan.blocks : [];
    const groups = groupByDay(blocks);
    if (!groups.length) {
      renderEmptyPlan();
      return;
    }
    if (elEmptyPlan) {
      elEmptyPlan.style.display = "none";
    }

    groups.forEach(([day, dayBlocks]) => {
      const dayEl = document.createElement("div");
      dayEl.className = "planner-day";
      const studyCount = dayBlocks.filter((block) => block.kind === "study").length;
      const reviewCount = dayBlocks.filter((block) => block.kind === "review").length;
      dayEl.innerHTML = `
        <div class="planner-day-head">
          <div class="planner-day-title">${escapeHtml(day)}</div>
          <div class="planner-pill">${studyCount} study / ${reviewCount} review</div>
        </div>
        <div class="planner-blocks"></div>
      `;

      const list = dayEl.querySelector(".planner-blocks");
      dayBlocks.sort((left, right) => left.start.localeCompare(right.start));
      dayBlocks.forEach((block, index) => {
        const row = document.createElement("div");
        row.className = "planner-block";
        const kindClass = block.kind === "review" ? "review" : "study";
        row.style.setProperty("--delay", `${Math.min(320, index * 24)}ms`);
        row.innerHTML = `
          <div class="planner-time">${escapeHtml(block.start_hm)} - ${escapeHtml(block.end_hm)}</div>
          <div>
            <div class="planner-subj">${escapeHtml(block.subject)}</div>
            <div class="planner-note">${escapeHtml(block.notes || "")}</div>
          </div>
          <div class="planner-kind ${kindClass}">${kindClass.toUpperCase()}</div>
          <button class="planner-done" type="button" title="Mark studied">✓</button>
        `;

        row.querySelector(".planner-done").addEventListener("click", () => {
          if (!lastGeneratedPlan || !Array.isArray(lastGeneratedPlan.blocks)) {
            return;
          }
          lastGeneratedPlan.blocks = lastGeneratedPlan.blocks.filter((candidate) => {
            return !(
              candidate.start === block.start &&
              candidate.end === block.end &&
              candidate.subject === block.subject &&
              candidate.kind === block.kind &&
              (candidate.notes || "") === (block.notes || "")
            );
          });
          renderPlan(lastGeneratedPlan);
          if (elGenerated) {
            elGenerated.textContent = JSON.stringify(lastGeneratedPlan, null, 2);
          }
          saveState();
          setStatus("Block marked studied and removed.");
        });

        list.appendChild(row);
      });

      elPlan.appendChild(dayEl);
    });
  }

  async function generate() {
    const payload = collect();
    if (!payload.subjects.length) {
      setStatus("Add at least one subject.");
      return;
    }

    setStatus("Generating...");
    btnGenerate.disabled = true;
    try {
      const response = await fetch("/planner/api/plan/", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        setStatus(data.error || "Error generating plan.");
        return;
      }
      lastGeneratedPlan = data.plan || null;
      lastGeneratedTips = data.tips || "";
      renderPlan(data.plan);
      elTips.textContent = data.tips || "Generate a plan to see coaching tips.";
      if (elGenerated) {
        elGenerated.textContent = JSON.stringify(data.plan || {}, null, 2);
      }
      saveState();
      setStatus("Done.");
    } catch (error) {
      setStatus("Failed. Is the server running?");
    } finally {
      btnGenerate.disabled = false;
    }
  }

  function exportPayload() {
    const payload = collect();
    payload.plan = lastGeneratedPlan;
    payload.tips = lastGeneratedTips;
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const stamp = todayISO().replaceAll("-", "");
    anchor.href = url;
    anchor.download = `study-planner-${stamp}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    setStatus("Planner exported.");
  }

  function importPayload() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "application/json,.json";
    input.addEventListener("change", async () => {
      const file = input.files && input.files[0];
      if (!file) {
        return;
      }
      try {
        const text = await file.text();
        const payload = JSON.parse(text);
        applyData(payload);
        saveState();
        setStatus("Planner imported.");
      } catch (error) {
        setStatus("Import failed: invalid JSON file.");
      }
    });
    input.click();
  }

  function loadState() {
    try {
      const raw = localStorage.getItem(stateKey);
      if (!raw) {
        return false;
      }
      applyData(JSON.parse(raw));
      setStatus("Planner restored from browser storage.");
      return true;
    } catch (error) {
      return false;
    }
  }

  btnAddSubject.addEventListener("click", () => addSubject());
  btnGenerate.addEventListener("click", generate);
  btnSample.addEventListener("click", loadSample);
  btnImport.addEventListener("click", importPayload);
  btnExport.addEventListener("click", exportPayload);

  if (!loadState()) {
    applyData(initialPayload);
    setStatus("Sample loaded.");
  }
})();
