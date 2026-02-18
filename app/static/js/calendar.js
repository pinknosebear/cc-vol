// Calendar grid renderer for monthly shift view
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function badgeClass(signupCount, capacity) {
  if (signupCount >= capacity) return "shift-badge--filled";
  if (signupCount > 0) return "shift-badge--partial";
  return "shift-badge--empty";
}

/**
 * Render calendar grid into container.
 * @param {HTMLElement} container
 * @param {Array} shifts - from GET /api/shifts?month= (each: {id, date, type, capacity, signup_count})
 * @param {{ onDayClick: function }} opts
 */
export function renderCalendar(container, shifts, { onDayClick }) {
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
  grid.className = "card";

  const calGrid = document.createElement("div");
  calGrid.className = "cal-grid";

  // Day-of-week headers
  for (const d of DAYS) {
    const h = document.createElement("div");
    h.className = "text-xs font-semibold text-center py-2 text-gray-400 uppercase tracking-wide";
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
    const cell = document.createElement("div");
    cell.className = "cal-day border border-gray-200 rounded-lg p-1.5 min-h-[70px] cursor-pointer transition-shadow hover:shadow-md text-sm bg-white";
    if (dateStr === todayStr) cell.classList.add("cal-day--today");

    const num = document.createElement("div");
    num.className = "font-semibold text-sm mb-1 text-gray-700";
    num.textContent = day;
    cell.appendChild(num);

    const dayShifts = byDate[dateStr];
    if (dayShifts) {
      for (const type of ["kakad", "robe"]) {
        if (dayShifts[type]) {
          const s = dayShifts[type];
          const badge = document.createElement("div");
          badge.className = `shift-badge inline-block w-full px-1 py-0.5 rounded text-xs font-medium text-white mt-0.5 ${badgeClass(s.signup_count, s.capacity)}`;
          badge.textContent = `${type === "kakad" ? "K" : "R"}: ${s.signup_count}/${s.capacity}`;
          cell.appendChild(badge);
        }
      }
      cell.addEventListener("click", () => onDayClick(dateStr));
    }

    calGrid.appendChild(cell);
  }

  grid.appendChild(calGrid);
  container.appendChild(grid);
}
