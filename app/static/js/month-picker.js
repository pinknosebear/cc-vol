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
  wrap.className = "flex items-center gap-4 justify-center py-2";

  const prev = document.createElement("button");
  prev.className = "w-8 h-8 flex items-center justify-center rounded-full border border-gray-200 bg-white hover:bg-gray-50 transition-colors cursor-pointer text-gray-500 text-xs";
  prev.textContent = "◀";
  prev.addEventListener("click", () => {
    let newMonth = month - 1;
    let newYear = year;
    if (newMonth < 1) { newMonth = 12; newYear--; }
    onChange(newYear, newMonth);
  });

  const label = document.createElement("span");
  const today = new Date();
  const isCurrent = year === today.getFullYear() && month === today.getMonth() + 1;
  label.className = `text-lg font-semibold min-w-[160px] text-center ${isCurrent ? "text-indigo-600" : "text-gray-800"}`;
  label.textContent = `${MONTHS[month - 1]} ${year}`;

  const next = document.createElement("button");
  next.className = "w-8 h-8 flex items-center justify-center rounded-full border border-gray-200 bg-white hover:bg-gray-50 transition-colors cursor-pointer text-gray-500 text-xs";
  next.textContent = "▶";
  next.addEventListener("click", () => {
    let newMonth = month + 1;
    let newYear = year;
    if (newMonth > 12) { newMonth = 1; newYear++; }
    onChange(newYear, newMonth);
  });

  wrap.append(prev, label, next);
  container.appendChild(wrap);
}
