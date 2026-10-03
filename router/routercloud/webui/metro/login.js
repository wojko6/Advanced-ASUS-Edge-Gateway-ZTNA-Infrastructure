"use strict";

// ROUTERCLOUD_PASSWORD_RECOVERY_UI_V1

document.addEventListener("DOMContentLoaded", () => {
  const form =
    document.getElementById(
      "routercloud-login-form"
    );

  const username =
    document.getElementById(
      "routercloud-username"
    );

  const password =
    document.getElementById(
      "routercloud-password"
    );

  const error =
    document.getElementById(
      "routercloud-login-error"
    );

  const submit =
    form.querySelector(
      ".routercloud-login-submit"
    );

  const forgotPassword =
    document.getElementById(
      "routercloud-forgot-password"
    );

  const recoveryForm =
    document.getElementById(
      "routercloud-recovery-form"
    );

  const recoveryEmail =
    document.getElementById(
      "routercloud-recovery-email"
    );

  const recoveryStatus =
    document.getElementById(
      "routercloud-recovery-status"
    );

  const recoverySubmit =
    document.getElementById(
      "routercloud-recovery-submit"
    );

  const recoveryBack =
    document.getElementById(
      "routercloud-recovery-back"
    );

  const preview =
    window.ROUTERCLOUD_LOGIN_PREVIEW === true;

  const showError = message => {
    error.textContent = message;
    error.classList.remove("hidden");
  };

  const clearError = () => {
    error.textContent = "";
    error.classList.add("hidden");
  };

  const clearRecoveryStatus = () => {
    recoveryStatus.textContent = "";
    recoveryStatus.classList.add("hidden");
  };

  const showRecoveryStatus = message => {
    recoveryStatus.textContent = message;
    recoveryStatus.classList.remove(
      "hidden"
    );
  };

  const showLogin = () => {
    recoveryForm.classList.add("hidden");
    form.classList.remove("hidden");

    clearRecoveryStatus();
    clearError();

    username.focus();
  };

  const showRecovery = () => {
    form.classList.add("hidden");
    recoveryForm.classList.remove("hidden");

    clearError();
    clearRecoveryStatus();

    recoveryEmail.focus();
  };

  const safeNextUrl = () => {
    const next =
      new URLSearchParams(
        location.search
      ).get("next");

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

  form.addEventListener(
    "submit",
    async event => {
      event.preventDefault();
      clearError();

      if (!form.reportValidity()) {
        return;
      }

      if (preview) {
        showError(
          "Podgląd lokalny — logowanie nie jest wykonywane."
        );
        return;
      }

      submit.disabled = true;
      submit.textContent =
        "Logowanie...";

      try {
        const body =
          new URLSearchParams();

        body.set(
          "username",
          username.value
        );

        body.set(
          "password",
          password.value
        );

        const response =
          await fetch(
            "/__routercloud/login",
            {
              method: "POST",
              credentials: "same-origin",

              headers: {
                "Content-Type":
                  "application/x-www-form-urlencoded",
              },

              body,
            }
          );

        if (response.status === 401) {
          password.value = "";

          showError(
            "Nieprawidłowa nazwa użytkownika lub hasło."
          );

          password.focus();
          return;
        }

        if (!response.ok) {
          showError(
            "Nie udało się zalogować. Spróbuj ponownie."
          );

          return;
        }

        location.replace(
          safeNextUrl()
        );
      } catch {
        showError(
          "Nie można połączyć się z RouterCloud."
        );
      } finally {
        submit.disabled = false;
        submit.textContent =
          "Zaloguj";
      }
    }
  );

  recoveryForm.addEventListener(
    "submit",
    async event => {
      event.preventDefault();

      clearRecoveryStatus();

      if (!recoveryForm.reportValidity()) {
        return;
      }

      recoverySubmit.disabled = true;
      recoverySubmit.textContent =
        "Wysyłanie...";

      try {
        if (!preview) {
          const body =
            new URLSearchParams();

          body.set(
            "email",
            recoveryEmail.value
          );

          const response =
            await fetch(
              "/__routercloud/password-reset/request",
              {
                method: "POST",
                credentials: "same-origin",

                headers: {
                  "Content-Type":
                    "application/x-www-form-urlencoded",
                },

                body,
              }
            );

          if (!response.ok) {
            throw new Error(
              "password reset request failed"
            );
          }
        }

        /*
         * Komunikat jest celowo identyczny
         * niezależnie od tego, czy konto istnieje.
         */
        showRecoveryStatus(
          "Jeżeli ten adres jest powiązany z kontem, wysłaliśmy link do zmiany hasła."
        );
      } catch {
        showRecoveryStatus(
          "Nie udało się wysłać żądania. Spróbuj ponownie później."
        );
      } finally {
        recoverySubmit.disabled = false;
        recoverySubmit.textContent =
          "Wyślij link resetujący";
      }
    }
  );

  forgotPassword.addEventListener(
    "click",
    showRecovery
  );

  recoveryBack.addEventListener(
    "click",
    showLogin
  );

  username.addEventListener(
    "input",
    clearError
  );

  password.addEventListener(
    "input",
    clearError
  );

  recoveryEmail.addEventListener(
    "input",
    clearRecoveryStatus
  );

  username.focus();
});
