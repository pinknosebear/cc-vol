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
      '<div class="card day-panel"><p class="text-sm text-gray-500 text-center py-8">Select a day to manage shift assignments.</p></div>';
    return;
  }

  const card = document.createElement("div");
  card.className = "card day-panel";

  const date = dayData[0].date || "";
  const headWrap = document.createElement("div");
  headWrap.className = "day-panel-head";
  const header = document.createElement("h3");
  header.className = "day-panel-title";
  header.textContent = formatDate(date);
  const subtitle = document.createElement("p");
  subtitle.className = "day-panel-subtitle";
  subtitle.textContent = "Manage shift assignments";
  headWrap.append(header, subtitle);
  card.appendChild(headWrap);

  for (const shift of dayData) {
    const section = document.createElement("div");
    const label = shift.type === "kakad" ? "Kakad" : "Robe";
    section.className = `day-shift day-shift--${shift.type}`;

    const titleRow = document.createElement("div");
    titleRow.className = "day-shift-head";

    const left = document.createElement("div");
    left.className = "day-shift-title";
    left.innerHTML = `<span class="day-shift-icon">${shift.type === "kakad" ? "🌅" : "🌆"}</span><div><div class="day-shift-name">${label} Shift</div><div class="day-shift-meta">${shift.type === "kakad" ? "Early Morning" : "Evening"}</div></div>`;

    const countValue = shift.signup_count || (shift.volunteers || []).length;
    const count = document.createElement("span");
    count.className = `day-shift-count ${countValue >= shift.capacity ? "day-shift-count--ok" : "day-shift-count--gap"}`;
    count.textContent = `${countValue}/${shift.capacity} Volunteers`;

    titleRow.append(left, count);
    section.appendChild(titleRow);

    const volunteers = shift.volunteers || [];
    const labelRow = document.createElement("p");
    labelRow.className = "day-assigned-title";
    labelRow.textContent = "Assigned Volunteers";
    section.appendChild(labelRow);

    const list = document.createElement("div");
    list.className = "day-assigned-list";
    for (const vol of volunteers) {
      const div = document.createElement("div");
      div.className = "day-assigned-item";
      div.innerHTML = `<div class="day-assigned-name">${vol.name}</div><div class="day-assigned-phone">${vol.phone || ""}</div>`;
      list.appendChild(div);
    }

    const emptySlots = shift.capacity - countValue;
    for (let i = 0; i < emptySlots; i++) {
      const div = document.createElement("div");
      div.className = "day-assigned-item day-assigned-item--open";
      div.textContent = "Open slot";
      list.appendChild(div);
    }
    section.appendChild(list);

    if (availableVols && availableVols.length > 0) {
      const avTitle = document.createElement("p");
      avTitle.className = "day-assign-title";
      avTitle.textContent = "Assign Volunteer";
      section.appendChild(avTitle);

      const select = document.createElement("select");
      select.className = "day-assign-select";
      select.innerHTML = '<option>Choose a volunteer...</option>';
      for (const vol of availableVols) {
        const opt = document.createElement("option");
        opt.value = String(vol.id);
        opt.textContent = vol.name;
        select.appendChild(opt);
      }
      section.appendChild(select);

      const button = document.createElement("button");
      button.className = "day-assign-btn";
      button.disabled = true;
      button.textContent = `Assign to ${label} Shift`;
      section.appendChild(button);
    }

    card.appendChild(section);
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
