import {
  fetchShifts,
  fetchMyShifts,
  createSignup,
  deleteSignup,
  notifyCoordinatorDroppedShift,
} from "./api.js";
import { renderMonthPicker } from "./month-picker.js";
import { renderCalendar } from "./calendar.js";
import { renderShiftPanel } from "./vol-shift-panel.js";

// State
const state = {
  year: new Date().getFullYear(),
  month: new Date().getMonth() + 1,
  phone: sessionStorage.getItem("volunteer_phone") || "",
  selectedDate: null,
  myShiftsLoaded: false,
  signedUpShiftIds: new Set(),
  signedUpMap: new Map(),
};

// DOM refs
const phoneInput = document.getElementById("phone-input");
const monthPickerEl = document.getElementById("month-picker");
const calendarEl = document.getElementById("calendar");
const myShiftsEl = document.getElementById("my-shifts");
const tabs = document.querySelectorAll(".tab");

let activeTab = "calendar";

// --- Phone input wiring ---
phoneInput.value = state.phone;
phoneInput.addEventListener("change", (e) => {
  state.phone = e.target.value;
  sessionStorage.setItem("volunteer_phone", state.phone);
  if (activeTab === "calendar") loadCalendar();
  if (activeTab === "my-shifts") loadMyShifts();
});

// --- Tab navigation ---
function showTab(tabName) {
  activeTab = tabName;
  tabs.forEach((t) => {
    t.classList.toggle("tab--active", t.dataset.tab === tabName);
  });

  calendarEl.style.display = tabName === "calendar" ? "" : "none";
  myShiftsEl.style.display = tabName === "my-shifts" ? "" : "none";
  monthPickerEl.style.display = tabName === "calendar" ? "" : "none";

  if (tabName === "calendar") loadCalendar();
  if (tabName === "my-shifts") loadMyShifts();
}

tabs.forEach((t) => {
  t.addEventListener("click", () => {
    showTab(t.dataset.tab);
  });
});

// --- Utilities ---
function monthStr() {
  return `${state.year}-${String(state.month).padStart(2, "0")}`;
}

// --- Data loading ---
async function loadCalendar() {
  if (!state.phone) {
    calendarEl.innerHTML =
      '<div class="card"><p>Enter your phone number to view the calendar.</p></div>';
    return;
  }

  try {
    const shifts = await fetchShifts(monthStr());

    // Try to load volunteer's shifts; if not found, they're a new phone number
    let myShifts = [];
    try {
      myShifts = await fetchMyShifts(state.phone, monthStr());
    } catch (err) {
      // Phone not registered yet is okay - they can still view and sign up
      if (!err.message.includes("404")) throw err;
    }

    // Rebuild signedUpShiftIds and signedUpMap from myShifts
    state.signedUpShiftIds.clear();
    state.signedUpMap.clear();
    if (myShifts && myShifts.length > 0) {
      for (const signup of myShifts) {
        state.signedUpShiftIds.add(signup.shift_id);
        state.signedUpMap.set(signup.shift_id, signup.signup_id);
      }
    }

    renderCalendar(calendarEl, shifts, {
      onDayClick: (date) => loadDayDetail(date),
    });
  } catch (err) {
    calendarEl.innerHTML = `<div class="card"><p>Error loading calendar: ${err.message}</p></div>`;
  }
}

async function loadDayDetail(date) {
  state.selectedDate = date;
  try {
    const shifts = await fetchShifts(monthStr());
    // Filter shifts for this date
    const dayShifts = shifts.filter((s) => s.date === date);

    if (dayShifts.length === 0) {
      calendarEl.innerHTML =
        '<div class="card"><p>No shifts on this date.</p></div>';
      return;
    }

    // Render shifts with Sign Up / Drop buttons
    calendarEl.innerHTML = "";
    const container = document.createElement("div");
    container.className = "day-shifts-container";

    const dateHeader = document.createElement("h3");
    dateHeader.textContent = formatDate(date);
    container.appendChild(dateHeader);

    for (const shift of dayShifts) {
      const shiftPanel = document.createElement("div");
      renderShiftPanel(shiftPanel, shift, state.signedUpShiftIds, state.signedUpMap, {
        onSignUp: handleSignUp,
        onDrop: (signupId) => handleDropWithNotification(signupId, shift.date, shift.type),
      });
      container.appendChild(shiftPanel);
    }

    const card = document.createElement("div");
    card.className = "card";
    card.appendChild(container);
    calendarEl.appendChild(card);
  } catch (err) {
    calendarEl.innerHTML = `<div class="card"><p>Error loading day detail: ${err.message}</p></div>`;
  }
}

async function loadMyShifts() {
  if (!state.phone) {
    myShiftsEl.innerHTML =
      '<div class="card"><p>Enter your phone number to view your shifts.</p></div>';
    return;
  }

  try {
    let myShifts = [];
    try {
      myShifts = await fetchMyShifts(state.phone, monthStr());
    } catch (err) {
      // Phone not registered yet is okay
      if (!err.message.includes("404")) throw err;
    }

    if (!myShifts || myShifts.length === 0) {
      myShiftsEl.innerHTML =
        '<div class="card"><p>You have no shifts this month.</p></div>';
      return;
    }

    // Build the display for my shifts
    renderMyShifts(myShifts);
  } catch (err) {
    myShiftsEl.innerHTML = `<div class="card"><p>Error loading your shifts: ${err.message}</p></div>`;
  }
}

async function handleSignUp(shiftId) {
  try {
    const signup = await createSignup(state.phone, shiftId);
    state.signedUpShiftIds.add(shiftId);
    state.signedUpMap.set(shiftId, signup.id);
    // Refresh calendar to update badge
    loadCalendar();
  } catch (err) {
    throw err;
  }
}

async function handleDropWithNotification(signupId, shiftDate, shiftType) {
  try {
    const daysUntilShift = daysUntil(shiftDate);

    // If within 7 days, notify coordinator via WhatsApp
    if (daysUntilShift <= 7) {
      try {
        await notifyCoordinatorDroppedShift(state.phone, shiftDate, shiftType);
      } catch (err) {
        // Notification failed but allow drop to proceed
        console.warn("Failed to notify coordinator:", err);
      }
    }

    // Always delete the signup
    await deleteSignup(signupId);

    // Remove from tracking
    for (const [shiftId, id] of state.signedUpMap.entries()) {
      if (id === signupId) {
        state.signedUpShiftIds.delete(shiftId);
        state.signedUpMap.delete(shiftId);
        break;
      }
    }

    // Refresh both calendar and my shifts
    if (activeTab === "calendar") loadCalendar();
    if (activeTab === "my-shifts") loadMyShifts();
  } catch (err) {
    throw err;
  }
}

function daysUntil(dateStr) {
  const shiftDate = new Date(dateStr + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = shiftDate - today;
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

function renderMyShifts(shifts) {
  myShiftsEl.innerHTML = "";

  const card = document.createElement("div");
  card.className = "card";

  const title = document.createElement("h3");
  title.textContent = `Your Shifts (${monthStr()})`;
  card.appendChild(title);

  const grid = document.createElement("div");
  grid.id = "my-shifts-grid";

  // Rebuild signedUpShiftIds and signedUpMap for accurate button state
  state.signedUpShiftIds.clear();
  state.signedUpMap.clear();
  for (const shiftDetail of shifts) {
    state.signedUpShiftIds.add(shiftDetail.shift_id);
    state.signedUpMap.set(shiftDetail.shift_id, shiftDetail.signup_id);
  }

  for (const shiftDetail of shifts) {
    // Transform API response to shift object with id field
    const shift = {
      id: shiftDetail.shift_id,
      date: shiftDetail.date,
      type: shiftDetail.type,
      capacity: shiftDetail.capacity,
      signup_count: 1, // Volunteer already signed up
    };
    const panel = document.createElement("div");
    renderShiftPanel(panel, shift, state.signedUpShiftIds, state.signedUpMap, {
      onSignUp: handleSignUp,
      onDrop: (signupId) => handleDropWithNotification(signupId, shift.date, shift.type),
    });
    grid.appendChild(panel);
  }

  card.appendChild(grid);
  myShiftsEl.appendChild(card);
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
      if (activeTab === "my-shifts") loadMyShifts();
    },
  });
}

// --- Initial load ---
showTab("calendar");
renderPicker();
