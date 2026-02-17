// Stateless shift panel renderer for volunteer portal

/**
 * Render a shift panel with Sign Up or Drop button.
 * @param {HTMLElement} container
 * @param {Object} shift - {id, date, type, capacity, signup_count}
 * @param {Set} signedUpShiftIds - Set of shift IDs volunteer is signed up for
 * @param {Map} signedUpMap - Map of shift_id -> signup_id
 * @param {{onSignUp: function, onDrop: function}} handlers
 */
export function renderShiftPanel(container, shift, signedUpShiftIds, signedUpMap, handlers) {
  container.innerHTML = "";

  const card = document.createElement("div");
  card.className = "shift-card";

  // Date and type header
  const header = document.createElement("div");
  header.className = "shift-card-header";
  const typeLabel = shift.type === "kakad" ? "Kakad" : "Robe";
  header.innerHTML = `
    <strong>${typeLabel}</strong>
    <span class="shift-capacity">${shift.signup_count}/${shift.capacity}</span>
  `;
  card.appendChild(header);

  // Date
  const dateEl = document.createElement("div");
  dateEl.className = "shift-date";
  dateEl.textContent = formatDate(shift.date);
  card.appendChild(dateEl);

  // Action button
  const isSignedUp = signedUpShiftIds.has(shift.id);
  const hasCapacity = shift.signup_count < shift.capacity;

  if (isSignedUp) {
    const dropBtn = document.createElement("button");
    dropBtn.className = "btn btn--drop";
    dropBtn.textContent = "Drop Shift";
    const signupId = signedUpMap.get(shift.id);
    dropBtn.addEventListener("click", async () => {
      try {
        await handlers.onDrop(signupId);
      } catch (err) {
        showError(card, parseErrorMessage(err.message));
      }
    });
    card.appendChild(dropBtn);
  } else if (hasCapacity) {
    const signupBtn = document.createElement("button");
    signupBtn.className = "btn btn--primary";
    signupBtn.textContent = "Sign Up";
    signupBtn.addEventListener("click", async () => {
      try {
        await handlers.onSignUp(shift.id);
      } catch (err) {
        showError(card, parseErrorMessage(err.message));
      }
    });
    card.appendChild(signupBtn);
  } else {
    const fullEl = document.createElement("div");
    fullEl.className = "shift-full";
    fullEl.textContent = "Shift Full";
    card.appendChild(fullEl);
  }

  container.appendChild(card);
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function parseErrorMessage(errMessage) {
  // Try to extract user-friendly error from API response
  // Format: "422: {...}"
  if (errMessage.includes("422:")) {
    try {
      const jsonStr = errMessage.substring(errMessage.indexOf("{"));
      const json = JSON.parse(jsonStr);

      // Handle detail array with reason field
      if (json.detail && Array.isArray(json.detail) && json.detail.length > 0) {
        if (json.detail[0].reason) {
          return json.detail[0].reason;
        }
      }

      // Handle generic detail string
      if (json.detail && typeof json.detail === "string") {
        return json.detail;
      }
    } catch (e) {
      // If JSON parsing fails, fall through to generic message
    }
  }

  // Check for duplicate signup
  if (errMessage.includes("409")) {
    return "You're already signed up for this shift.";
  }

  // Check for shift not found
  if (errMessage.includes("404")) {
    return "This shift is no longer available.";
  }

  // Fall back to original message
  return errMessage;
}

function showError(container, message) {
  // Remove any existing error message
  const existing = container.querySelector(".form-message--error");
  if (existing) existing.remove();

  const msg = document.createElement("div");
  msg.className = "form-message form-message--error";
  msg.textContent = message;
  container.appendChild(msg);
}
