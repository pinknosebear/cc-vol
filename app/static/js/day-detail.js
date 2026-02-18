// Day detail panel renderer

/**
 * Render day detail panel.
 * @param {HTMLElement} container
 * @param {Array} dayData - from GET /api/shifts/{date} (shifts with volunteer arrays)
 * @param {Array|null} availableVols - from GET /api/coordinator/volunteers/available?date=
 */
export function renderDayDetail(container, dayData, availableVols) {
  container.innerHTML = "";

  if (!dayData || dayData.length === 0) {
    container.innerHTML =
      '<div class="card"><p class="text-sm text-gray-400 text-center py-6">Select a day to view details.</p></div>';
    return;
  }

  const card = document.createElement("div");
  card.className = "card";

  const date = dayData[0].date || "";
  const header = document.createElement("h3");
  header.className = "text-base font-semibold text-gray-900 mb-4";
  header.textContent = formatDate(date);
  card.appendChild(header);

  for (const shift of dayData) {
    const section = document.createElement("div");
    section.className = "mb-5";

    const titleRow = document.createElement("div");
    titleRow.className = "flex items-center gap-2 mb-2";

    const label = shift.type === "kakad" ? "Kakad" : "Robe";
    const badgeColor = shift.type === "kakad" ? "bg-amber-500" : "bg-violet-500";
    const badge = document.createElement("span");
    badge.className = `text-xs font-bold text-white px-2.5 py-0.5 rounded-full ${badgeColor}`;
    badge.textContent = label;

    const count = document.createElement("span");
    count.className = "text-sm text-gray-400";
    count.textContent = `${shift.signup_count || 0} / ${shift.capacity}`;

    titleRow.append(badge, count);
    section.appendChild(titleRow);

    const volunteers = shift.volunteers || [];
    for (const vol of volunteers) {
      const div = document.createElement("div");
      div.className = "flex items-center gap-2 py-1 text-sm text-gray-800";
      div.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0 inline-block"></span>${vol.name}`;
      section.appendChild(div);
    }

    const emptySlots = shift.capacity - (shift.signup_count || volunteers.length || 0);
    for (let i = 0; i < emptySlots; i++) {
      const div = document.createElement("div");
      div.className = "flex items-center gap-2 py-1 text-sm text-gray-400 italic";
      div.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-gray-300 flex-shrink-0 inline-block"></span>open slot`;
      section.appendChild(div);
    }

    card.appendChild(section);
  }

  if (availableVols && availableVols.length > 0) {
    const sep = document.createElement("hr");
    sep.className = "border-gray-100 my-3";
    card.appendChild(sep);

    const avSection = document.createElement("div");
    const avTitle = document.createElement("p");
    avTitle.className = "text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2";
    avTitle.textContent = "Available Volunteers";
    avSection.appendChild(avTitle);

    for (const vol of availableVols) {
      const div = document.createElement("div");
      div.className = "text-sm text-gray-700 py-0.5";
      div.textContent = vol.name;
      avSection.appendChild(div);
    }
    card.appendChild(avSection);
  }

  container.appendChild(card);
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}
