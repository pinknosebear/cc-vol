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
  header.textContent = "Unfilled Shifts";
  card.appendChild(header);

  if (!gaps || gaps.length === 0) {
    const empty = document.createElement("p");
    empty.textContent = "All shifts filled! \uD83C\uDF89";
    empty.style.padding = "20px 0";
    empty.style.textAlign = "center";
    card.appendChild(empty);
    container.appendChild(card);
    return;
  }

  // Summary
  const summary = document.createElement("div");
  summary.className = "gaps-summary";
  const totalNeed = gaps.reduce((sum, g) => sum + (g.capacity - (g.signup_count || 0)), 0);
  summary.textContent = `${gaps.length} shifts need ${totalNeed} more volunteer${totalNeed !== 1 ? "s" : ""}`;
  card.appendChild(summary);

  // Sort by date
  const sorted = [...gaps].sort((a, b) => a.date.localeCompare(b.date));

  const today = new Date();
  const todayStr = today.toISOString().split("T")[0];
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const tomorrowStr = tomorrow.toISOString().split("T")[0];

  for (const gap of sorted) {
    const gapCard = document.createElement("div");
    gapCard.className = "gap-card";
    if (gap.date === todayStr || gap.date === tomorrowStr) {
      gapCard.classList.add("gap-card--urgent");
    }

    const left = document.createElement("div");
    const dateLabel = document.createElement("div");
    dateLabel.className = "gap-date";
    dateLabel.textContent = formatGapDate(gap.date);
    left.appendChild(dateLabel);

    const typeBadge = document.createElement("span");
    typeBadge.className = "shift-badge shift-badge--empty";
    typeBadge.textContent = gap.type === "kakad" ? "Kakad" : "Robe";
    left.appendChild(typeBadge);

    const right = document.createElement("div");
    right.className = "gap-need";
    const gapSize = gap.capacity - (gap.signup_count || 0);
    right.textContent = `Need ${gapSize} more`;

    gapCard.append(left, right);
    card.appendChild(gapCard);
  }

  container.appendChild(card);
}

function formatGapDate(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}
