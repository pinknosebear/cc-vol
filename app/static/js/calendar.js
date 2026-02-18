// Calendar grid renderer for monthly shift view
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/**
 * Render calendar grid into container.
 * @param {HTMLElement} container
 * @param {Array} shifts - from GET /api/shifts?month= (each: {id, date, type, capacity, signup_count})
 * @param {{ onDayClick: function, selectedDate?: string }} opts
 */
export function renderCalendar(container, shifts, { onDayClick, selectedDate = null }) {
  container.innerHTML = "";

  if (!shifts || shifts.length === 0) {
    container.innerHTML = '<div class="card"><p class="text-sm text-gray-400 text-center py-4">No shifts found. Seed this month first.</p></div>';
    return;
  }

  // Group shifts by date
  const byDate = {};
  for (const s of shifts) {
    if (!byDate[s.date]) byDate[s.date] = {};
    byDate[s.date][s.type] = s;
  }

  // Determine month from first shift
  const dates = Object.keys(byDate).sort();
  const firstDate = new Date(dates[0] + "T00:00:00");
  const year = firstDate.getFullYear();
  const month = firstDate.getMonth();

  const grid = document.createElement("div");
  grid.className = "card calendar-shell";

  const calGrid = document.createElement("div");
  calGrid.className = "cal-grid";

  // Day-of-week headers
  for (const d of DAYS) {
    const h = document.createElement("div");
    h.className = "cal-dow";
    h.textContent = d;
    calGrid.appendChild(h);
  }

  // Empty leading cells
  const firstOfMonth = new Date(year, month, 1);
  const startDay = firstOfMonth.getDay();
  for (let i = 0; i < startDay; i++) {
    const empty = document.createElement("div");
    empty.className = "cal-day cal-day--empty";
    calGrid.appendChild(empty);
  }

  // Days in month
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const today = new Date();
  const todayStr = today.toISOString().split("T")[0];

  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const dayShifts = byDate[dateStr];
    const kakad = dayShifts?.kakad || null;
    const robe = dayShifts?.robe || null;
    const kakadGap = kakad ? Math.max(0, kakad.capacity - (kakad.signup_count || 0)) : 0;
    const robeGap = robe ? Math.max(0, robe.capacity - (robe.signup_count || 0)) : 0;
    const hasGap = kakadGap > 0 || robeGap > 0;

    const cell = document.createElement("div");
    cell.className = "cal-day";
    if (dateStr === todayStr) cell.classList.add("cal-day--today");
    if (dateStr === selectedDate) cell.classList.add("cal-day--selected");
    if (hasGap) cell.classList.add("cal-day--gap");

    const num = document.createElement("div");
    num.className = "cal-day-num";
    num.textContent = day;
    cell.appendChild(num);

    if (hasGap) {
      const ping = document.createElement("span");
      ping.className = "cal-day-alert";
      ping.textContent = "!";
      cell.appendChild(ping);
    }

    if (kakad) {
      cell.appendChild(renderShiftBadge("Kakad", kakad.signup_count || 0, kakad.capacity));
    }
    if (robe) {
      cell.appendChild(renderShiftBadge("Robe", robe.signup_count || 0, robe.capacity));
    }

    if (dayShifts) {
      cell.addEventListener("click", () => onDayClick(dateStr));
    }

    calGrid.appendChild(cell);
  }

  grid.appendChild(calGrid);
  container.appendChild(grid);
}

function renderShiftBadge(label, signupCount, capacity) {
  const filled = signupCount >= capacity;
  const badge = document.createElement("div");
  badge.className = "cal-shift";

  const left = document.createElement("div");
  left.className = "cal-shift-label";
  const dot = document.createElement("span");
  dot.className = `cal-shift-dot ${filled ? "cal-shift-dot--ok" : "cal-shift-dot--gap"}`;
  const name = document.createElement("span");
  name.textContent = label;
  left.append(dot, name);

  const count = document.createElement("span");
  count.className = `cal-shift-count ${filled ? "cal-shift-count--ok" : "cal-shift-count--gap"}`;
  count.textContent = `${signupCount}/${capacity}`;

  badge.append(left, count);
  return badge;
}
