// API client for cc-vol coordinator dashboard
const BASE = window.location.origin;

async function request(url) {
  const resp = await fetch(url);
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`${resp.status}: ${body}`);
  }
  return resp.json();
}

async function postJSON(url, data) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`${resp.status}: ${body}`);
  }
  return resp.json();
}

export function fetchShifts(month) {
  return request(`${BASE}/api/shifts?month=${month}`);
}

export function fetchDayDetail(date) {
  return request(`${BASE}/api/shifts/${date}`);
}

export function fetchGaps(month) {
  return request(`${BASE}/api/coordinator/gaps?month=${month}`);
}

export function fetchAvailable(date) {
  return request(`${BASE}/api/coordinator/volunteers/available?date=${date}`);
}

export function fetchVolunteers() {
  return request(`${BASE}/api/volunteers`);
}

export function createVolunteer(phone, name, isCoordinator) {
  return postJSON(`${BASE}/api/volunteers`, {
    phone,
    name,
    is_coordinator: isCoordinator,
  });
}

export function seedMonth(year, month) {
  return postJSON(`${BASE}/api/coordinator/seed/${year}/${month}`, {});
}
