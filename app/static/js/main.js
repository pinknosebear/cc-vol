import { fetchShifts, fetchDayDetail, fetchGaps, fetchAvailable, fetchVolunteers, createVolunteer, seedMonth, deleteVolunteer } from "./api.js";
import { renderMonthPicker } from "./month-picker.js";
import { renderCalendar } from "./calendar.js";
import { renderDayDetail } from "./day-detail.js";
import { renderGaps } from "./gaps.js";
import { renderVolunteerList, renderSeedControls } from "./volunteers.js";

// State
const state = {
  year: new Date().getFullYear(),
  month: new Date().getMonth() + 1,
  selectedDate: null,
};

// DOM refs
const monthPickerEl = document.getElementById("month-picker");
const calendarEl = document.getElementById("calendar");
const dayDetailEl = document.getElementById("day-detail");
const gapsEl = document.getElementById("gaps");
const volunteersEl = document.getElementById("volunteers");
const tabs = document.querySelectorAll(".tab");

// --- Tab navigation ---
// Views: "calendar" shows month-picker + calendar + day-detail
//        "gaps" shows month-picker + gaps
//        "volunteers" shows volunteers + seed controls
let activeTab = "calendar";

function showTab(tabName) {
  activeTab = tabName;
  tabs.forEach(t => {
    t.classList.toggle("tab--active", t.dataset.tab === tabName);
  });

  // Hide/show sections
  calendarEl.style.display = tabName === "calendar" ? "" : "none";
  dayDetailEl.style.display = tabName === "calendar" ? "" : "none";
  gapsEl.style.display = tabName === "gaps" ? "" : "none";
  volunteersEl.style.display = tabName === "volunteers" ? "" : "none";

  // Month picker visible for calendar and gaps
  monthPickerEl.style.display = (tabName === "calendar" || tabName === "gaps") ? "" : "none";
}

tabs.forEach(t => {
  t.addEventListener("click", () => {
    showTab(t.dataset.tab);
    if (t.dataset.tab === "gaps") loadGaps();
    if (t.dataset.tab === "volunteers") loadVolunteers();
  });
});

// --- Data loading ---
function monthStr() {
  return `${state.year}-${String(state.month).padStart(2, "0")}`;
}

async function loadCalendar() {
  try {
    const shifts = await fetchShifts(monthStr());
    renderCalendar(calendarEl, shifts, {
      onDayClick: (date) => loadDayDetail(date),
    });
  } catch (err) {
    calendarEl.innerHTML = `<div class="card"><p>Error loading shifts: ${err.message}</p></div>`;
  }
}

async function loadDayDetail(date) {
  state.selectedDate = date;
  try {
    const [dayData, available] = await Promise.all([
      fetchDayDetail(date),
      fetchAvailable(date),
    ]);
    renderDayDetail(dayDetailEl, dayData, available);
  } catch (err) {
    dayDetailEl.innerHTML = `<div class="card day-detail"><p>Error: ${err.message}</p></div>`;
  }
}

async function loadGaps() {
  try {
    const gaps = await fetchGaps(monthStr());
    renderGaps(gapsEl, gaps);
  } catch (err) {
    gapsEl.innerHTML = `<div class="card"><p>Error loading gaps: ${err.message}</p></div>`;
  }
}

async function loadVolunteers() {
  try {
    const vols = await fetchVolunteers();
    renderVolunteerList(volunteersEl, vols, {
      onAdd: async (phone, name, isCoord) => {
        await createVolunteer(phone, name, isCoord);
        loadVolunteers();
      },
      onDelete: async (id) => {
        await deleteVolunteer(id);
        loadVolunteers();
      },
    });

    // Seed controls below volunteers
    const seedContainer = document.createElement("div");
    seedContainer.id = "seed-controls";
    volunteersEl.appendChild(seedContainer);
    renderSeedControls(seedContainer, {
      currentYear: state.year,
      currentMonth: state.month,
      onSeed: async (year, month) => {
        await seedMonth(year, month);
        // Refresh calendar if on that view
        if (activeTab === "calendar") loadCalendar();
      },
    });
  } catch (err) {
    volunteersEl.innerHTML = `<div class="card"><p>Error loading volunteers: ${err.message}</p></div>`;
  }
}

// --- Month picker wiring ---
function renderPicker() {
  renderMonthPicker(monthPickerEl, {
    year: state.year,
    month: state.month,
    onChange: (newYear, newMonth) => {
      state.year = newYear;
      state.month = newMonth;
      renderPicker();
      if (activeTab === "calendar") loadCalendar();
      if (activeTab === "gaps") loadGaps();
    },
  });
}

// --- Initial load ---
showTab("calendar");
renderPicker();
loadCalendar();
renderDayDetail(dayDetailEl, null, null); // Show placeholder
