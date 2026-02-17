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
export function renderMonthPicker(container, { year, month, onChange }) {
  container.innerHTML = "";

  const wrap = document.createElement("div");
  wrap.className = "month-picker";

  const prev = document.createElement("button");
  prev.className = "btn btn--secondary";
  prev.textContent = "\u25C0";
  prev.addEventListener("click", () => {
    let newMonth = month - 1;
    let newYear = year;
    if (newMonth < 1) { newMonth = 12; newYear--; }
    onChange(newYear, newMonth);
  });

  const label = document.createElement("span");
  label.className = "month-label";
  label.textContent = `${MONTHS[month - 1]} ${year}`;

  const today = new Date();
  if (year === today.getFullYear() && month === today.getMonth() + 1) {
    label.style.color = "var(--color-primary)";
  }

  const next = document.createElement("button");
  next.className = "btn btn--secondary";
  next.textContent = "\u25B6";
  next.addEventListener("click", () => {
    let newMonth = month + 1;
    let newYear = year;
    if (newMonth > 12) { newMonth = 1; newYear++; }
    onChange(newYear, newMonth);
  });

  wrap.append(prev, label, next);
  container.appendChild(wrap);
}
