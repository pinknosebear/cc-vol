// Weekly gaps renderer inspired by the Figma layout

const weekOffsetByMonth = new Map();
const WEEK_DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

/**
 * Render weekly gaps overview.
 * @param {HTMLElement} container
 * @param {Array} shifts - from GET /api/shifts?month= (full month shifts)
 * @param {{ year: number, month: number }} opts
 */
export function renderGaps(container, shifts, { year, month }) {
  container.innerHTML = "";

  if (!shifts || shifts.length === 0) {
    container.innerHTML = '<div class="card"><p class="text-sm text-gray-500 text-center py-4">No shifts found for this month.</p></div>';
    return;
  }

  const monthKey = `${year}-${String(month).padStart(2, "0")}`;
  const byDate = new Map();
  for (const s of shifts) {
    if (!byDate.has(s.date)) byDate.set(s.date, {});
    byDate.get(s.date)[s.type] = s;
  }

  const weeks = getWeeksInMonth(year, month);
  let weekOffset = weekOffsetByMonth.get(monthKey) || 0;
  weekOffset = Math.max(0, Math.min(weekOffset, weeks.length - 1));
  weekOffsetByMonth.set(monthKey, weekOffset);
  const currentWeek = weeks[weekOffset];

  const totalGaps = shifts.reduce((sum, s) => {
    return sum + Math.max(0, (s.capacity || 0) - (s.signup_count || 0));
  }, 0);

  const wrap = document.createElement("div");
  wrap.className = "gaps-wrap";

  if (totalGaps > 0) {
    const summary = document.createElement("div");
    summary.className = "gaps-summary";
    summary.textContent = `${totalGaps} Volunteer Gap${totalGaps === 1 ? "" : "s"} This Month`;
    wrap.appendChild(summary);
  }

  const nav = document.createElement("div");
  nav.className = "gaps-week-nav";

  const navLeft = document.createElement("div");
  const title = document.createElement("div");
  title.className = "gaps-week-title";
  title.textContent = "Weekly Gap Overview";
  const range = document.createElement("div");
  range.className = "gaps-week-range";
  range.textContent = formatWeekRange(currentWeek);
  navLeft.append(title, range);

  const navRight = document.createElement("div");
  navRight.className = "gaps-week-controls";
  const prev = document.createElement("button");
  prev.className = "gaps-week-btn";
  prev.textContent = "‹";
  prev.disabled = weekOffset === 0;
  prev.addEventListener("click", () => {
    weekOffsetByMonth.set(monthKey, weekOffset - 1);
    renderGaps(container, shifts, { year, month });
  });
  const label = document.createElement("span");
  label.textContent = `Week ${weekOffset + 1} of ${weeks.length}`;
  const next = document.createElement("button");
  next.className = "gaps-week-btn";
  next.textContent = "›";
  next.disabled = weekOffset >= weeks.length - 1;
  next.addEventListener("click", () => {
    weekOffsetByMonth.set(monthKey, weekOffset + 1);
    renderGaps(container, shifts, { year, month });
  });
  navRight.append(prev, label, next);
  nav.append(navLeft, navRight);
  wrap.appendChild(nav);

  const grid = document.createElement("div");
  grid.className = "gaps-grid";

  for (let i = 0; i < currentWeek.length; i++) {
    const d = currentWeek[i];
    const dateStr = toDateKey(d);
    const dayShifts = byDate.get(dateStr) || {};
    const kakad = dayShifts.kakad || null;
    const robe = dayShifts.robe || null;
    const inMonth = d.getMonth() + 1 === month && d.getFullYear() === year;

    const kakadGap = kakad ? Math.max(0, kakad.capacity - (kakad.signup_count || 0)) : 0;
    const robeGap = robe ? Math.max(0, robe.capacity - (robe.signup_count || 0)) : 0;
    const hasGap = kakadGap > 0 || robeGap > 0;

    const card = document.createElement("div");
    card.className = "gaps-day";
    if (!inMonth) card.classList.add("gaps-day--outside");
    if (!hasGap) card.classList.add("gaps-day--filled");

    const dow = document.createElement("div");
    dow.className = "gaps-dow";
    dow.textContent = WEEK_DAYS[i];
    const num = document.createElement("div");
    num.className = "gaps-date";
    num.textContent = d.getDate();
    card.append(dow, num);

    if (!kakad && !robe) {
      const empty = document.createElement("div");
      empty.className = "gaps-ok";
      empty.textContent = "No shifts";
      card.appendChild(empty);
    } else {
      if (kakad) card.appendChild(renderShiftBlock("Kakad", kakad));
      if (robe) card.appendChild(renderShiftBlock("Robe", robe));
    }

    grid.appendChild(card);
  }

  wrap.appendChild(grid);

  if (totalGaps === 0) {
    const done = document.createElement("div");
    done.className = "gaps-empty";
    done.textContent = "All shifts covered for this month.";
    wrap.appendChild(done);
  }

  container.appendChild(wrap);
}

function renderShiftBlock(label, shift) {
  const gap = Math.max(0, shift.capacity - (shift.signup_count || 0));

  const section = document.createElement("div");
  section.className = "gaps-shift";

  const row = document.createElement("div");
  row.className = "gaps-shift-row";
  const name = document.createElement("div");
  name.className = "gaps-shift-name";
  name.textContent = label;

  const count = document.createElement("span");
  count.className = "gaps-count";
  if (gap === 0) count.classList.add("gaps-count--filled");
  count.textContent = `${shift.signup_count || 0}/${shift.capacity || 0}`;
  row.append(name, count);
  section.appendChild(row);

  if (gap > 0) {
    const need = document.createElement("div");
    need.className = "gaps-need";
    need.textContent = `Need ${gap} more`;
    section.appendChild(need);

    const quickAssign = document.createElement("button");
    quickAssign.className = "gaps-assign";
    quickAssign.textContent = "Quick Assign";
    quickAssign.disabled = true;
    section.appendChild(quickAssign);
  } else {
    const ok = document.createElement("div");
    ok.className = "gaps-ok";
    ok.textContent = "Covered";
    section.appendChild(ok);
  }

  return section;
}

function getWeeksInMonth(year, month) {
  const first = new Date(year, month - 1, 1);
  const last = new Date(year, month, 0);
  const weeks = [];
  let cursor = new Date(first);

  while (cursor <= last) {
    const week = [];
    const start = new Date(cursor);
    start.setDate(start.getDate() - start.getDay());
    for (let i = 0; i < 7; i++) {
      const day = new Date(start);
      day.setDate(start.getDate() + i);
      week.push(day);
    }
    weeks.push(week);
    cursor.setDate(cursor.getDate() + 7);
  }

  return weeks;
}

function formatWeekRange(week) {
  if (!week || week.length !== 7) return "";
  const start = week[0];
  const end = week[6];
  return `${start.toLocaleDateString("en-US", { month: "short", day: "numeric" })} - ${end.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`;
}

function toDateKey(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
