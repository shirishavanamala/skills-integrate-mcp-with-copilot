document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const signupNotice = document.getElementById("signup-notice");
  const messageDiv = document.getElementById("message");
  const loginButton = document.getElementById("admin-login-button");
  const logoutButton = document.getElementById("admin-logout-button");
  const loginDialog = document.getElementById("admin-login-dialog");
  const loginForm = document.getElementById("admin-login-form");
  const loginError = document.getElementById("login-error");
  const adminStatus = document.getElementById("admin-status");
  let isAdmin = false;

  function showMessage(message, kind) {
    messageDiv.textContent = message;
    messageDiv.className = kind;
    setTimeout(() => messageDiv.classList.add("hidden"), 5000);
  }

  async function responseData(response) {
    return response.json().catch(() => ({}));
  }

  function updateAdminControls() {
    signupForm.hidden = !isAdmin;
    signupNotice.hidden = isAdmin;
    loginButton.hidden = isAdmin;
    logoutButton.hidden = !isAdmin;
    adminStatus.textContent = isAdmin
      ? "Signed in as staff"
      : "Staff sign-in required to manage registrations";
  }

  async function refreshAdminSession() {
    const response = await fetch("/admin/session");
    if (!response.ok) throw new Error("Staff session check failed");
    const session = await responseData(response);
    isAdmin = session.authenticated === true;
    updateAdminControls();
  }

  function makeParticipantList(participants, activityName) {
    const container = document.createElement("div");
    container.className = "participants-container";

    const heading = document.createElement("h5");
    heading.textContent = "Participants:";
    container.appendChild(heading);

    if (participants.length === 0) {
      const empty = document.createElement("p");
      empty.textContent = "No participants yet";
      container.appendChild(empty);
      return container;
    }

    const list = document.createElement("ul");
    list.className = "participants-list";
    participants.forEach((email) => {
      const item = document.createElement("li");
      const label = document.createElement("span");
      label.className = "participant-email";
      label.textContent = email;
      item.appendChild(label);

      if (isAdmin) {
        const removeButton = document.createElement("button");
        removeButton.className = "delete-btn";
        removeButton.type = "button";
        removeButton.textContent = "Unregister";
        removeButton.dataset.activity = activityName;
        removeButton.dataset.email = email;
        item.appendChild(removeButton);
      }
      list.appendChild(item);
    });
    container.appendChild(list);
    return container;
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) throw new Error("Activity request failed");
      const activities = await response.json();

      activitiesList.replaceChildren();
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("article");
        activityCard.className = "activity-card";

        const title = document.createElement("h4");
        title.textContent = name;
        activityCard.appendChild(title);

        const description = document.createElement("p");
        description.textContent = details.description;
        activityCard.appendChild(description);

        const schedule = document.createElement("p");
        const scheduleLabel = document.createElement("strong");
        scheduleLabel.textContent = "Schedule: ";
        schedule.append(scheduleLabel, document.createTextNode(details.schedule));
        activityCard.appendChild(schedule);

        const availability = document.createElement("p");
        const availabilityLabel = document.createElement("strong");
        availabilityLabel.textContent = "Availability: ";
        availability.append(
          availabilityLabel,
          document.createTextNode(
            `${details.max_participants - details.participants.length} spots left`
          )
        );
        activityCard.appendChild(availability);
        activityCard.appendChild(
          makeParticipantList(details.participants, name)
        );
        activitiesList.appendChild(activityCard);

        activitySelect.add(new Option(name, name));
      });
    } catch (error) {
      activitiesList.textContent =
        "Failed to load activities. Please try again later.";
      console.error("Error fetching activities:", error);
    }
  }

  loginButton.addEventListener("click", () => {
    loginError.textContent = "";
    loginError.classList.add("hidden");
    loginDialog.showModal();
  });

  document.getElementById("admin-login-cancel").addEventListener("click", () => {
    loginDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginError.classList.add("hidden");
    const formData = new FormData(loginForm);

    try {
      const response = await fetch("/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await responseData(response);
      if (!response.ok) {
        loginError.textContent = result.detail || "Sign-in failed";
        loginError.classList.remove("hidden");
        return;
      }

      loginForm.reset();
      loginDialog.close();
      await refreshAdminSession();
      await fetchActivities();
    } catch (error) {
      loginError.textContent = "Unable to sign in. Please try again.";
      loginError.classList.remove("hidden");
      console.error("Error signing in:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/admin/logout", { method: "POST" });
      if (!response.ok) throw new Error("Sign-out request failed");
      isAdmin = false;
      updateAdminControls();
      await fetchActivities();
    } catch (error) {
      showMessage("Failed to sign out. Please try again.", "error");
      console.error("Error signing out:", error);
    }
  });

  activitiesList.addEventListener("click", async (event) => {
    const button = event.target.closest(".delete-btn");
    if (!button || !isAdmin) return;

    const { activity, email } = button.dataset;
    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        { method: "DELETE" }
      );
      const result = await responseData(response);
      if (!response.ok) {
        showMessage(result.detail || "An error occurred", "error");
        return;
      }
      showMessage(result.message, "success");
      await fetchActivities();
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("email").value;
    const activity = activitySelect.value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        { method: "POST" }
      );
      const result = await responseData(response);
      if (!response.ok) {
        showMessage(result.detail || "An error occurred", "error");
        return;
      }

      showMessage(result.message, "success");
      signupForm.reset();
      await fetchActivities();
    } catch (error) {
      showMessage("Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  updateAdminControls();
  async function initialize() {
    try {
      await refreshAdminSession();
    } catch (error) {
      showMessage("Unable to check staff sign-in status.", "error");
      console.error("Error checking staff session:", error);
    }
    await fetchActivities();
  }

  initialize();
});
