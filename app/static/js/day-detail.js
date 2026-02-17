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
      '<div class="card day-detail"><p>Select a day to view details.</p></div>';
    return;
  }

  const card = document.createElement("div");
  card.className = "card day-detail";

  // Date header
  const date = dayData[0].date || "";
  const header = document.createElement("h3");
  header.textContent = formatDate(date);
  card.appendChild(header);

  // Each shift (Kakad, Robe)
  for (const shift of dayData) {
    const section = document.createElement("div");
    section.className = "shift-section";

    const title = document.createElement("h4");
    const label = shift.type === "kakad" ? "Kakad" : "Robe";
    title.textContent = `${label} (${shift.signup_count || 0}/${shift.capacity})`;
    section.appendChild(title);

    // Signed-up volunteers
    const volunteers = shift.volunteers || [];
    for (const vol of volunteers) {
      const div = document.createElement("div");
      div.className = "vol-name";
      div.textContent = vol.name;
      section.appendChild(div);
    }

    // Empty slot indicators
    const emptySlots =
      shift.capacity - (shift.signup_count || volunteers.length || 0);
    for (let i = 0; i < emptySlots; i++) {
      const div = document.createElement("div");
      div.className = "empty-slot";
      div.textContent = "(open slot)";
      section.appendChild(div);
    }

    card.appendChild(section);
  }

  // Available volunteers section
  if (availableVols && availableVols.length > 0) {
    const avSection = document.createElement("div");
    avSection.className = "shift-section";
    const avTitle = document.createElement("h4");
    avTitle.textContent = "Available Volunteers";
    avSection.appendChild(avTitle);

    for (const vol of availableVols) {
      const div = document.createElement("div");
      div.className = "vol-name";
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
