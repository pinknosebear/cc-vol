// Month picker component for dashboard navigation
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

/**
 * Render month picker into container.
 * @param {HTMLElement} container
 * @param {{ year: number, month: number, onChange: function }} opts
 */
export function renderMonthPicker(container, { year, month, onChange, onSeed }) {
  container.innerHTML = "";

  const wrap = document.createElement("div");
  wrap.className = "month-picker-wrap";

  const prev = document.createElement("button");
  prev.className = "month-picker-btn";
  prev.textContent = "‹";
  prev.addEventListener("click", () => {
    let newMonth = month - 1;
    let newYear = year;
    if (newMonth < 1) { newMonth = 12; newYear--; }
    onChange(newYear, newMonth);
  });

  const label = document.createElement("span");
  label.className = "month-picker-label";
  label.textContent = `${MONTHS[month - 1]} ${year}`;

  const next = document.createElement("button");
  next.className = "month-picker-btn";
  next.textContent = "›";
  next.addEventListener("click", () => {
    let newMonth = month + 1;
    let newYear = year;
    if (newMonth > 12) { newMonth = 1; newYear++; }
    onChange(newYear, newMonth);
  });

  const left = document.createElement("div");
  left.className = "month-picker-left";
  left.append(prev, label, next);

  wrap.appendChild(left);

  if (typeof onSeed === "function") {
    const seedBtn = document.createElement("button");
    seedBtn.className = "month-picker-seed";
    seedBtn.textContent = "✧ Seed Shifts for Selected Month";
    seedBtn.addEventListener("click", () => {
      onSeed(year, month);
    });
    wrap.appendChild(seedBtn);
  }

  container.appendChild(wrap);
}
