// Gaps list renderer
/**
 * Render gaps list.
 * @param {HTMLElement} container
 * @param {Array} gaps - from GET /api/coordinator/gaps?month= (date, type, capacity, signup_count)
 */
export function renderGaps(container, gaps) {
  container.innerHTML = "";

  const card = document.createElement("div");
  card.className = "card";

  const header = document.createElement("h3");
  header.className = "text-base font-semibold text-gray-900 mb-3";
  header.textContent = "Unfilled Shifts";
  card.appendChild(header);

  if (!gaps || gaps.length === 0) {
    const empty = document.createElement("p");
    empty.className = "text-center text-gray-400 text-sm py-8";
    empty.textContent = "All shifts filled! 🎉";
    card.appendChild(empty);
    container.appendChild(card);
    return;
  }

  const totalNeed = gaps.reduce((sum, g) => sum + (g.capacity - (g.signup_count || 0)), 0);
  const summary = document.createElement("div");
  summary.className = "text-sm text-gray-400 mb-4";
  summary.textContent = `${gaps.length} shifts need ${totalNeed} more volunteer${totalNeed !== 1 ? "s" : ""}`;
  card.appendChild(summary);

  const sorted = [...gaps].sort((a, b) => a.date.localeCompare(b.date));

  const today = new Date();
  const todayStr = today.toISOString().split("T")[0];
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const tomorrowStr = tomorrow.toISOString().split("T")[0];

  for (const gap of sorted) {
    const isUrgent = gap.date === todayStr || gap.date === tomorrowStr;
    const gapCard = document.createElement("div");
    gapCard.className = "gap-card flex justify-between items-center px-3 py-2.5 border border-gray-200 rounded-lg mb-2 bg-white";
    if (isUrgent) gapCard.classList.add("gap-card--urgent");

    const left = document.createElement("div");
    left.className = "flex items-center gap-2";

    const dateLabel = document.createElement("span");
    dateLabel.className = "font-medium text-sm text-gray-800";
    dateLabel.textContent = formatGapDate(gap.date);

    const isKakad = gap.type === "kakad";
    const typeBadge = document.createElement("span");
    typeBadge.className = `text-xs font-bold text-white px-2 py-0.5 rounded-full ${isKakad ? "bg-amber-500" : "bg-violet-500"}`;
    typeBadge.textContent = isKakad ? "Kakad" : "Robe";

    left.append(dateLabel, typeBadge);

    const right = document.createElement("div");
    right.className = "text-sm text-red-500 font-medium";
    right.textContent = `Need ${gap.capacity - (gap.signup_count || 0)} more`;

    gapCard.append(left, right);
    card.appendChild(gapCard);
  }

  container.appendChild(card);
}

function formatGapDate(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}
