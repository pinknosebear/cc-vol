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
  header.textContent = "Volunteers";
  card.appendChild(header);

  // Table
  const table = document.createElement("table");
  table.className = "vol-table";

  const thead = document.createElement("thead");
  thead.innerHTML = "<tr><th>Name</th><th>Phone</th><th>Role</th></tr>";
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  for (const vol of volunteers) {
    const tr = document.createElement("tr");
    const nameTd = document.createElement("td");
    nameTd.textContent = vol.name;
    const phoneTd = document.createElement("td");
    phoneTd.textContent = vol.phone;
    const roleTd = document.createElement("td");
    roleTd.textContent = vol.is_coordinator ? "Coordinator" : "Volunteer";
    tr.append(nameTd, phoneTd, roleTd);
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  card.appendChild(table);

  // Add form
  const form = document.createElement("div");
  form.style.marginTop = "16px";
  form.innerHTML = `
    <h4 style="margin-bottom: 8px;">Add Volunteer</h4>
    <div class="form-group">
      <label for="vol-name">Name</label>
      <input type="text" id="vol-name" placeholder="Full name">
    </div>
    <div class="form-group">
      <label for="vol-phone">Phone</label>
      <input type="tel" id="vol-phone" placeholder="Phone number">
    </div>
    <div class="form-group">
      <label><input type="checkbox" id="vol-coord"> Coordinator</label>
    </div>
    <button class="btn btn--primary" id="vol-add-btn">Add Volunteer</button>
    <div id="vol-form-msg"></div>
  `;
  card.appendChild(form);

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
  card.className = "card";
  card.style.marginTop = "16px";

  const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];

  card.innerHTML = `
    <h4>Seed Shifts</h4>
    <p style="font-size: 13px; color: var(--color-text-secondary); margin: 8px 0;">
      Generate shift slots for a month. Safe to run multiple times (idempotent).
    </p>
    <button class="btn btn--primary" id="seed-btn">Seed ${MONTHS[currentMonth - 1]} ${currentYear}</button>
    <div id="seed-msg"></div>
  `;

  container.appendChild(card);

  const seedBtn = container.querySelector("#seed-btn");
  const seedMsg = container.querySelector("#seed-msg");
  seedBtn.addEventListener("click", async () => {
    try {
      seedBtn.disabled = true;
      seedBtn.textContent = "Seeding...";
      const result = await onSeed(currentYear, currentMonth);
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
