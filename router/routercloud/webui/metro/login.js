"use strict";

// ROUTERCLOUD_PASSWORD_RECOVERY_UI_V1
// ROUTERCLOUD_PASSWORD_RESET_UI_V1

document.addEventListener("DOMContentLoaded", () => {
  const loginForm =
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

  const loginError =
    document.getElementById(
      "routercloud-login-error"
    );

  const loginSubmit =
    loginForm.querySelector(
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

  const resetForm =
    document.getElementById(
      "routercloud-reset-form"
    );

  const resetPassword =
    document.getElementById(
      "routercloud-reset-password"
    );

  const resetPasswordConfirm =
    document.getElementById(
      "routercloud-reset-password-confirm"
    );

  const resetStatus =
    document.getElementById(
      "routercloud-reset-status"
    );

  const resetSubmit =
    document.getElementById(
      "routercloud-reset-submit"
    );

  const resetBack =
    document.getElementById(
      "routercloud-reset-back"
    );

  const preview =
    window.ROUTERCLOUD_LOGIN_PREVIEW === true;

  const query =
    new URLSearchParams(
      location.search
    );

  /*
   * ROUTERCLOUD_PASSWORD_RESET_FRAGMENT_V1
   *
   * Reset token jest przekazywany wyłącznie
   * w URL fragment:
   *
   *   #reset_token=...
   *
   * Fragment nie jest wysyłany do serwera.
   *
   * Token odczytujemy także przy hashchange,
   * ponieważ zmiana samego fragmentu URL
   * nie przeładowuje dokumentu.
   */
  let resetToken = "";
  let validResetToken = false;

  const hideAllForms = () => {
    loginForm.classList.add(
      "hidden"
    );

    recoveryForm.classList.add(
      "hidden"
    );

    resetForm.classList.add(
      "hidden"
    );
  };

  const clearLoginError = () => {
    loginError.textContent = "";

    loginError.classList.add(
      "hidden"
    );
  };

  const showLoginError = message => {
    loginError.textContent = message;

    loginError.classList.remove(
      "hidden"
    );
  };

  const clearRecoveryStatus = () => {
    recoveryStatus.textContent = "";

    recoveryStatus.classList.add(
      "hidden"
    );
  };

  const showRecoveryStatus = message => {
    recoveryStatus.textContent =
      message;

    recoveryStatus.classList.remove(
      "hidden"
    );
  };

  const clearResetStatus = () => {
    resetStatus.textContent = "";

    resetStatus.classList.add(
      "hidden"
    );

    resetStatus.classList.remove(
      "routercloud-status-error",
      "routercloud-status-success"
    );
  };

  const showResetStatus = (
    message,
    kind
  ) => {
    resetStatus.textContent =
      message;

    resetStatus.classList.remove(
      "hidden",
      "routercloud-status-error",
      "routercloud-status-success"
    );

    if (kind === "error") {
      resetStatus.classList.add(
        "routercloud-status-error"
      );
    }

    if (kind === "success") {
      resetStatus.classList.add(
        "routercloud-status-success"
      );
    }
  };

  const showLogin = () => {
    hideAllForms();

    loginForm.classList.remove(
      "hidden"
    );

    clearLoginError();
    clearRecoveryStatus();
    clearResetStatus();

    username.focus();
  };

  const showRecovery = () => {
    hideAllForms();

    recoveryForm.classList.remove(
      "hidden"
    );

    clearLoginError();
    clearRecoveryStatus();
    clearResetStatus();

    recoveryEmail.focus();
  };

  const showReset = () => {
    hideAllForms();

    resetForm.classList.remove(
      "hidden"
    );

    clearLoginError();
    clearRecoveryStatus();
    clearResetStatus();

    resetPassword.focus();
  };

  const safeNextUrl = () => {
    const next =
      query.get("next");

    if (
      next &&
      next.startsWith("/") &&
      !next.startsWith("//") &&
      !next.startsWith(
        "/__routercloud/"
      )
    ) {
      return next;
    }

    return "/";
  };

  loginForm.addEventListener(
    "submit",
    async event => {
      event.preventDefault();

      clearLoginError();

      if (!loginForm.reportValidity()) {
        return;
      }

      if (preview) {
        showLoginError(
          "Podgląd lokalny — logowanie nie jest wykonywane."
        );

        return;
      }

      loginSubmit.disabled = true;

      loginSubmit.textContent =
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
              credentials:
                "same-origin",

              headers: {
                "Content-Type":
                  "application/x-www-form-urlencoded",
              },

              body,
            }
          );

        if (response.status === 401) {
          password.value = "";

          showLoginError(
            "Nieprawidłowa nazwa użytkownika lub hasło."
          );

          password.focus();

          return;
        }

        if (!response.ok) {
          showLoginError(
            "Nie udało się zalogować. Spróbuj ponownie."
          );

          return;
        }

        location.replace(
          safeNextUrl()
        );
      } catch {
        showLoginError(
          "Nie można połączyć się z RouterCloud."
        );
      } finally {
        loginSubmit.disabled =
          false;

        loginSubmit.textContent =
          "Zaloguj";
      }
    }
  );

  recoveryForm.addEventListener(
    "submit",
    async event => {
      event.preventDefault();

      clearRecoveryStatus();

      if (
        !recoveryForm.reportValidity()
      ) {
        return;
      }

      recoverySubmit.disabled =
        true;

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
                credentials:
                  "same-origin",

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

        showRecoveryStatus(
          "Jeżeli ten adres jest powiązany z kontem, wysłaliśmy link do zmiany hasła."
        );
      } catch {
        showRecoveryStatus(
          "Nie udało się wysłać żądania. Spróbuj ponownie później."
        );
      } finally {
        recoverySubmit.disabled =
          false;

        recoverySubmit.textContent =
          "Wyślij link resetujący";
      }
    }
  );

  resetForm.addEventListener(
    "submit",
    async event => {
      event.preventDefault();

      clearResetStatus();

      if (
        !resetForm.reportValidity()
      ) {
        return;
      }

      if (
        resetPassword.value
        !== resetPasswordConfirm.value
      ) {
        showResetStatus(
          "Podane hasła nie są identyczne.",
          "error"
        );

        resetPasswordConfirm.focus();

        return;
      }

      if (!validResetToken) {
        showResetStatus(
          "Link do zmiany hasła jest nieprawidłowy lub niekompletny.",
          "error"
        );

        return;
      }

      resetSubmit.disabled = true;

      resetSubmit.textContent =
        "Zmienianie hasła...";

      try {
        if (!preview) {
          const body =
            new URLSearchParams();

          body.set(
            "token",
            resetToken
          );

          body.set(
            "password",
            resetPassword.value
          );

          body.set(
            "password_confirm",
            resetPasswordConfirm.value
          );

          const response =
            await fetch(
              "/__routercloud/password-reset/confirm",
              {
                method: "POST",
                credentials:
                  "same-origin",

                headers: {
                  "Content-Type":
                    "application/x-www-form-urlencoded",
                },

                body,
              }
            );

          if (response.status === 400) {
            resetToken = "";

            showResetStatus(
              "Link jest nieprawidłowy, wygasł albo został już użyty.",
              "error"
            );

            return;
          }

          if (response.status === 422) {
            showResetStatus(
              "Hasło musi mieć od 12 do 128 znaków.",
              "error"
            );

            return;
          }

          if (!response.ok) {
            throw new Error(
              "password reset confirmation failed"
            );
          }
        }

        /*
         * Po udanym resecie raw token
         * nie jest już potrzebny w pamięci.
         */
        resetToken = "";

        resetPassword.value = "";
        resetPasswordConfirm.value = "";

        resetPassword.disabled = true;
        resetPasswordConfirm.disabled = true;
        resetSubmit.disabled = true;

        showResetStatus(
          "Hasło zostało zmienione. Możesz się teraz zalogować.",
          "success"
        );

        resetBack.textContent =
          "Przejdź do logowania";
      } catch {
        showResetStatus(
          "Nie udało się zmienić hasła. Spróbuj ponownie.",
          "error"
        );
      } finally {
        if (resetToken) {
          resetSubmit.disabled =
            false;
        }

        resetSubmit.textContent =
          "Zmień hasło";
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

  resetBack.addEventListener(
    "click",
    showLogin
  );

  username.addEventListener(
    "input",
    clearLoginError
  );

  password.addEventListener(
    "input",
    clearLoginError
  );

  recoveryEmail.addEventListener(
    "input",
    clearRecoveryStatus
  );

  resetPassword.addEventListener(
    "input",
    clearResetStatus
  );

  resetPasswordConfirm.addEventListener(
    "input",
    clearResetStatus
  );

  // ROUTERCLOUD_PASSWORD_RESET_HASHCHANGE_V1
  const activateResetFromHash = () => {
    const fragment =
      new URLSearchParams(
        location.hash.startsWith("#")
          ? location.hash.slice(1)
          : location.hash
      );

    const candidate =
      fragment.get(
        "reset_token"
      ) || "";

    if (!candidate) {
      return false;
    }

    resetToken = candidate;

    validResetToken =
      /^[0-9a-fA-F]{64}$/.test(
        resetToken
      );

    /*
     * Usuń sekret z paska adresu natychmiast
     * po skopiowaniu go do pamięci JS.
     *
     * replaceState nie powoduje kolejnego
     * hashchange.
     */
    history.replaceState(
      {},
      document.title,
      location.pathname
        + location.search
    );

    resetPassword.disabled = false;

    resetPasswordConfirm.disabled =
      false;

    resetBack.textContent =
      "Wróć do logowania";

    resetSubmit.disabled =
      !validResetToken;

    showReset();

    if (!validResetToken) {
      showResetStatus(
        "Link do zmiany hasła jest nieprawidłowy lub niekompletny.",
        "error"
      );
    }

    return true;
  };

  window.addEventListener(
    "hashchange",
    () => {
      activateResetFromHash();
    }
  );

  if (!activateResetFromHash()) {
    showLogin();
  }
});
