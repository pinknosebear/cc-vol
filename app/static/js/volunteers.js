// Volunteer list and registration form renderer

/**
 * Render volunteer list with add form.
 * @param {HTMLElement} container
 * @param {Array} volunteers - from GET /api/volunteers
 * @param {{ onAdd: function }} opts - onAdd(phone, name, isCoordinator)
 */
export function renderVolunteerList(container, volunteers, { onAdd }) {
  container.innerHTML = "";

  const card = document.createElement("div");
  card.className = "card";

  const header = document.createElement("h3");
  header.className = "text-base font-semibold text-gray-900 mb-4";
  header.textContent = "Volunteers";
  card.appendChild(header);

  // Table
  const tableWrap = document.createElement("div");
  tableWrap.className = "overflow-x-auto";

  const table = document.createElement("table");
  table.className = "w-full text-sm";

  const thead = document.createElement("thead");
  thead.innerHTML = `
    <tr class="border-b border-gray-100">
      <th class="text-left py-2 px-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Name</th>
      <th class="text-left py-2 px-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Phone</th>
      <th class="text-left py-2 px-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Role</th>
    </tr>`;
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  for (const vol of volunteers) {
    const tr = document.createElement("tr");
    tr.className = "border-b border-gray-50 hover:bg-gray-50 transition-colors";

    const nameTd = document.createElement("td");
    nameTd.className = "py-2.5 px-3 text-gray-900 font-medium";
    nameTd.textContent = vol.name;

    const phoneTd = document.createElement("td");
    phoneTd.className = "py-2.5 px-3 text-gray-400 font-mono text-xs";
    phoneTd.textContent = vol.phone;

    const roleTd = document.createElement("td");
    roleTd.className = "py-2.5 px-3";
    const roleBadge = document.createElement("span");
    roleBadge.className = vol.is_coordinator
      ? "text-xs font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-full"
      : "text-xs text-gray-400";
    roleBadge.textContent = vol.is_coordinator ? "Coordinator" : "Volunteer";
    roleTd.appendChild(roleBadge);

    tr.append(nameTd, phoneTd, roleTd);
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  tableWrap.appendChild(table);
  card.appendChild(tableWrap);

  // Add volunteer form
  const formSection = document.createElement("div");
  formSection.className = "mt-6 pt-5 border-t border-gray-100";
  formSection.innerHTML = `
    <h4 class="text-sm font-semibold text-gray-700 mb-3">Add Volunteer</h4>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
      <div>
        <label for="vol-name" class="block text-xs font-medium text-gray-500 mb-1">Name</label>
        <input type="text" id="vol-name" placeholder="Full name"
          class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-indigo-400 transition-colors">
      </div>
      <div>
        <label for="vol-phone" class="block text-xs font-medium text-gray-500 mb-1">Phone</label>
        <input type="tel" id="vol-phone" placeholder="e.g. 919876543210"
          class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-indigo-400 transition-colors">
      </div>
    </div>
    <div class="flex items-center gap-2 mb-4">
      <input type="checkbox" id="vol-coord" class="rounded border-gray-300">
      <label for="vol-coord" class="text-sm text-gray-600 cursor-pointer">Mark as Coordinator</label>
    </div>
    <button id="vol-add-btn"
      class="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors cursor-pointer">
      Add Volunteer
    </button>
    <div id="vol-form-msg"></div>
  `;
  card.appendChild(formSection);
  container.appendChild(card);

  // Wire up form
  const addBtn = container.querySelector("#vol-add-btn");
  const msgDiv = container.querySelector("#vol-form-msg");
  addBtn.addEventListener("click", async () => {
    const name = container.querySelector("#vol-name").value.trim();
    const phone = container.querySelector("#vol-phone").value.trim();
    const isCoord = container.querySelector("#vol-coord").checked;
    if (!name || !phone) {
      msgDiv.className = "form-message form-message--error";
      msgDiv.textContent = "Name and phone are required.";
      return;
    }
    try {
      await onAdd(phone, name, isCoord);
      msgDiv.className = "form-message form-message--success";
      msgDiv.textContent = `Added ${name} successfully.`;
      container.querySelector("#vol-name").value = "";
      container.querySelector("#vol-phone").value = "";
      container.querySelector("#vol-coord").checked = false;
    } catch (err) {
      msgDiv.className = "form-message form-message--error";
      msgDiv.textContent = err.message;
    }
  });
}

/**
 * Render seed controls.
 * @param {HTMLElement} container
 * @param {{ currentYear: number, currentMonth: number, onSeed: function }} opts
 */
export function renderSeedControls(container, { currentYear, currentMonth, onSeed }) {
  container.innerHTML = "";

  const card = document.createElement("div");
  card.className = "card mt-4";

  const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];

  card.innerHTML = `
    <h4 class="text-sm font-semibold text-gray-700 mb-1">Seed Shifts</h4>
    <p class="text-xs text-gray-400 mb-3">Generate shift slots for a month. Safe to run multiple times (idempotent).</p>
    <button id="seed-btn"
      class="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors cursor-pointer disabled:opacity-50">
      Seed ${MONTHS[currentMonth - 1]} ${currentYear}
    </button>
    <div id="seed-msg"></div>
  `;
  container.appendChild(card);

  const seedBtn = container.querySelector("#seed-btn");
  const seedMsg = container.querySelector("#seed-msg");
  seedBtn.addEventListener("click", async () => {
    try {
      seedBtn.disabled = true;
      seedBtn.textContent = "Seeding...";
      await onSeed(currentYear, currentMonth);
      seedMsg.className = "form-message form-message--success";
      seedMsg.textContent = `Done! Created shifts for ${MONTHS[currentMonth - 1]} ${currentYear}.`;
    } catch (err) {
      seedMsg.className = "form-message form-message--error";
      seedMsg.textContent = err.message;
    } finally {
      seedBtn.disabled = false;
      seedBtn.textContent = `Seed ${MONTHS[currentMonth - 1]} ${currentYear}`;
    }
  });
}
