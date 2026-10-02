"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("routercloud-login-form");
  const username = document.getElementById("routercloud-username");
  const password = document.getElementById("routercloud-password");
  const error = document.getElementById("routercloud-login-error");
  const submit = form.querySelector(".routercloud-login-submit");

  const showError = message => {
    error.textContent = message;
    error.classList.remove("hidden");
  };

  const clearError = () => {
    error.textContent = "";
    error.classList.add("hidden");
  };

  const safeNextUrl = () => {
    const next = new URLSearchParams(location.search).get("next");

    if (
      next &&
      next.startsWith("/") &&
      !next.startsWith("//") &&
      !next.startsWith("/__routercloud/")
    ) {
      return next;
    }

    return "/";
  };

  form.addEventListener("submit", async event => {
    event.preventDefault();
    clearError();

    if (!form.reportValidity()) {
      return;
    }

    submit.disabled = true;
    submit.textContent = "Logowanie...";

    try {
      const body = new URLSearchParams();
      body.set("username", username.value);
      body.set("password", password.value);

      const response = await fetch("/__routercloud/login", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body,
      });

      if (response.status === 401) {
        password.value = "";
        showError("Nieprawidłowa nazwa użytkownika lub hasło.");
        password.focus();
        return;
      }

      if (!response.ok) {
        showError(
          "Nie udało się zalogować. Spróbuj ponownie."
        );
        return;
      }

      location.replace(safeNextUrl());
    } catch {
      showError(
        "Nie można połączyć się z RouterCloud."
      );
    } finally {
      submit.disabled = false;
      submit.textContent = "Zaloguj";
    }
  });

  username.addEventListener("input", clearError);
  password.addEventListener("input", clearError);

  username.focus();
});
