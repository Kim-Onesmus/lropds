const csrftoken = document.querySelector("[name=csrfmiddlewaretoken]")?.value;
console.log("CSRF Token found:", csrftoken ? "YES" : "NO");

// Profile Details Form
document
  .querySelector('[data-form="profile"]')
  ?.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData(e.target);
    const data = {
      org_name: formData.get("org_name"),
      contact_person: formData.get("contact_person"),
      email: formData.get("email"),
      correspondence_phone: formData.get("correspondence_phone"),
    };

    try {
      const response = await fetch("/api/profile/update/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrftoken, // Add this line
        },
        body: JSON.stringify(data),
      });

      const result = await response.json();
      if (response.ok) {
        showSuccessMessage("Profile updated successfully");
      } else {
        showErrorMessage(result.message || "Failed to update profile");
      }
    } catch (error) {
      showErrorMessage("Failed to update profile");
    }
  });

// Password Change Form
document
  .querySelector('[data-form="password"]')
  ?.addEventListener("submit", async (e) => {
    e.preventDefault();

    const inputs = e.target.querySelectorAll('input[type="password"]');
    const currentPassword = inputs[0].value;
    const newPassword = inputs[1].value;
    const confirmPassword = inputs[2].value;

    console.log("Password inputs found:", inputs.length);

    if (newPassword !== confirmPassword) {
      showErrorMessage("Passwords do not match");
      return;
    }

    try {
      const response = await fetch("/api/password/change/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrftoken,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_new_password: confirmPassword, // Add this
        }),
      });

      const result = await response.json();
      console.log("Response Status:", response.status);
      console.log("Response Body:", result);

      if (response.ok) {
        showSuccessMessage("Password updated successfully");
        e.target.reset();
      } else {
        showErrorMessage(result.message || "Failed to update password");
      }
    } catch (error) {
      console.error("Fetch Error:", error);
      showErrorMessage("Failed to update password: " + error.message);
    }
  });

function showSuccessMessage(message) {
  showToast(message, "success");
}

function showErrorMessage(message) {
  showToast(message, "error");
}

function showToast(message, type = "info") {
  const toast = document.createElement("div");
  const bgColor = type === "success" ? "bg-green-500" : "bg-red-500";
  toast.className = `fixed bottom-6 right-6 z-[70] px-4 py-3 rounded-lg text-white text-sm font-medium ${bgColor}`;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 3000);
}

/******************** ORGANIZATION SEARCH ********************/

document.getElementById("orgSearch").addEventListener("keyup", function () {
  let search = this.value.toLowerCase();
  let cards = document.querySelectorAll(".org-card");

  cards.forEach((card) => {
    let name = card.getAttribute("data-name");

    if (name.includes(search)) {
      card.style.display = "block";
    } else {
      card.style.display = "none";
    }
  });
});

/******************** ORGANIZATION MODAL ********************/

function openOrgModal(name, contact, phone, email, logo) {
  document.getElementById("modalName").innerText = name;
  document.getElementById("modalContact").innerText = contact;
  document.getElementById("modalPhone").innerText = phone;
  document.getElementById("modalEmail").innerText = email;

  if (logo) {
    document.getElementById("modalLogo").src = logo;
  }

  let modal = document.getElementById("orgModal");
  let card = document.getElementById("orgModalCard");

  modal.classList.remove("hidden");

  setTimeout(() => {
    modal.classList.add("flex");
    card.classList.remove("scale-95", "opacity-0");
    card.classList.add("scale-100", "opacity-100");
  }, 10);
}

function closeOrgModal() {
  let modal = document.getElementById("orgModal");
  let card = document.getElementById("orgModalCard");

  card.classList.add("scale-95", "opacity-0");

  setTimeout(() => {
    modal.classList.remove("flex");
    modal.classList.add("hidden");
  }, 200);
}