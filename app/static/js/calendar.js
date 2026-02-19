// Calendar grid renderer for monthly shift view
const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

function isShiftCovered(shift) {
  return shift && shift.signup_count >= shift.capacity;
}

function rowBorderClass(type) {
  return type === "kakad" ? "cal-role-row--kakad" : "cal-role-row--robe";
}

function countClass(shift) {
  return isShiftCovered(shift) ? "cal-count-pill--covered" : "cal-count-pill--needed";
}

function renderRoleRow(parent, type, shift) {
  const row = document.createElement("div");
  row.className = `cal-role-row ${rowBorderClass(type)}`;

  const left = document.createElement("div");
  left.className = "cal-role-left";

  const dot = document.createElement("span");
  dot.className = `cal-dot ${isShiftCovered(shift) ? "cal-dot--covered" : "cal-dot--needed"}`;

  const label = document.createElement("span");
  label.className = "cal-role-label";
  label.textContent = type === "kakad" ? "Kakad" : "Robe";

  left.append(dot, label);

  const count = document.createElement("span");
  count.className = `cal-count-pill ${countClass(shift)}`;
  count.textContent = `${shift.signup_count}/${shift.capacity}`;

  row.append(left, count);
  parent.appendChild(row);
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

  const byDate = {};
  for (const s of shifts) {
    if (!byDate[s.date]) byDate[s.date] = {};
    byDate[s.date][s.type] = s;
  }

  const dates = Object.keys(byDate).sort();
  const firstDate = new Date(`${dates[0]}T00:00:00`);
  const year = firstDate.getFullYear();
  const month = firstDate.getMonth();

  const card = document.createElement("div");
  card.className = "card";

  const calGrid = document.createElement("div");
  calGrid.className = "cal-grid cal-grid--timeline";

  for (const d of DAYS) {
    const h = document.createElement("div");
    h.className = "cal-weekday";
    h.textContent = d;
    calGrid.appendChild(h);
  }

  const firstOfMonth = new Date(year, month, 1);
  const startDay = firstOfMonth.getDay();
  for (let i = 0; i < startDay; i++) {
    const empty = document.createElement("div");
    empty.className = "cal-day cal-day--empty";
    calGrid.appendChild(empty);
  }

  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const today = new Date();
  const todayStr = today.toISOString().split("T")[0];

  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const dayShifts = byDate[dateStr] || {};
    const kakad = dayShifts.kakad;
    const robe = dayShifts.robe;
    const hasShift = Boolean(kakad || robe);
    const allCovered =
      hasShift &&
      (!kakad || isShiftCovered(kakad)) &&
      (!robe || isShiftCovered(robe));
    const hasGap = hasShift && !allCovered;

    const cell = document.createElement("div");
    cell.className = `cal-day cal-day--timeline ${hasGap ? "cal-day--needs-help" : "cal-day--covered"}`;
    if (dateStr === todayStr) cell.classList.add("cal-day--today");

    const top = document.createElement("div");
    top.className = "cal-day-top";
    if (hasGap) {
      const alert = document.createElement("span");
      alert.className = "cal-alert-dot";
      alert.textContent = "!";
      top.appendChild(alert);
    }
    if (dateStr === todayStr) {
      const todayBadge = document.createElement("span");
      todayBadge.className = "cal-today-pill";
      todayBadge.textContent = "Today";
      top.appendChild(todayBadge);
    }
    cell.appendChild(top);

    const num = document.createElement("div");
    num.className = "cal-day-number";
    num.textContent = day;
    cell.appendChild(num);

    const rows = document.createElement("div");
    rows.className = "cal-rows";
    if (kakad) renderRoleRow(rows, "kakad", kakad);
    if (robe) renderRoleRow(rows, "robe", robe);
    cell.appendChild(rows);

    if (kakad || robe) {
      cell.addEventListener("click", () => onDayClick(dateStr));
    }

    calGrid.appendChild(cell);
  }

  card.appendChild(calGrid);
  container.appendChild(card);
}
