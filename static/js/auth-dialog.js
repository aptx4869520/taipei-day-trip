const authTriggers = document.querySelectorAll(
  "[data-auth-trigger]"
);

if (authTriggers.length > 0) {
  const overlay = document.createElement("div");

  overlay.className = "auth-overlay";
  overlay.hidden = true;

  overlay.innerHTML = `
    <section
      class="auth-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-dialog-title"
    >
      <div class="auth-dialog__decoration"></div>

      <div class="auth-dialog__content">
        <h2
          id="auth-dialog-title"
          class="auth-dialog__title"
        ></h2>

        <button
          class="auth-dialog__close"
          type="button"
          aria-label="關閉會員登入與註冊視窗"
        ></button>

        <form class="auth-dialog__form"></form>

        <p
          class="auth-dialog__message"
          role="status"
          aria-live="polite"
          hidden
        ></p>

        <p class="auth-dialog__switch"></p>
      </div>
    </section>
  `;

  document.body.appendChild(overlay);

  const dialog = overlay.querySelector(".auth-dialog");
  const title = overlay.querySelector(
    ".auth-dialog__title"
  );
  const closeButton = overlay.querySelector(
    ".auth-dialog__close"
  );
  const form = overlay.querySelector(
    ".auth-dialog__form"
  );
  const switchArea = overlay.querySelector(
    ".auth-dialog__switch"
  );
  const message = overlay.querySelector(
    ".auth-dialog__message"
  );

  let previousFocus = null;

  let isSignedIn = false;

  let isSubmitting = false;

async function checkSignInStatus() {
  const token = localStorage.getItem("token");
  const headers = {};

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  try {
    const response = await fetch("/api/user/auth", {
      method: "GET",
      headers
    });

    if (!response.ok) {
      throw new Error("登入狀態檢查失敗");
    }

    const result = await response.json();

    isSignedIn = result.data !== null;

    if (token && !isSignedIn) {
      localStorage.removeItem("token");
    }

    authTriggers.forEach((trigger) => {
      trigger.textContent = isSignedIn
        ? "登出系統"
        : "登入/註冊";
    });
  } catch (error) {
    console.error("檢查登入狀態失敗：", error);

    isSignedIn = false;

    authTriggers.forEach((trigger) => {
      trigger.textContent = "登入/註冊";
    });
  }
}

  function renderSignIn() {
    dialog.classList.remove("auth-dialog--signup");
    title.textContent = "登入會員帳號";

    form.innerHTML = `
      <input
        class="auth-dialog__input"
        name="email"
        type="email"
        placeholder="輸入電子信箱"
        autocomplete="email"
        required
      >
      <input
        class="auth-dialog__input"
        name="password"
        type="password"
        placeholder="輸入密碼"
        autocomplete="current-password"
        required
      >
      <button
        class="auth-dialog__submit"
        type="submit"
      >
        登入帳戶
      </button>
    `;

    switchArea.innerHTML = `
      還沒有帳戶？
      <button
        class="auth-dialog__switch-button"
        type="button"
        data-auth-mode="signup"
      >
        點此註冊
      </button>
    `;

   clearMessage();
  }

  function renderSignUp() {
    dialog.classList.add("auth-dialog--signup");
    title.textContent = "註冊會員帳號";

    form.innerHTML = `
      <input
        class="auth-dialog__input"
        name="name"
        type="text"
        placeholder="輸入姓名"
        autocomplete="name"
        required
      >
      <input
        class="auth-dialog__input"
        name="email"
        type="email"
        placeholder="輸入電子郵件"
        autocomplete="email"
        required
      >
      <input
        class="auth-dialog__input"
        name="password"
        type="password"
        placeholder="輸入密碼"
        autocomplete="new-password"
        required
      >
      <button
        class="auth-dialog__submit"
        type="submit"
      >
        註冊新帳戶
      </button>
    `;

    switchArea.innerHTML = `
      已經有帳戶了？
      <button
        class="auth-dialog__switch-button"
        type="button"
        data-auth-mode="signin"
      >
        點此登入
      </button>
    `;

   clearMessage();
  }

  function setSubmitting(submitting) {
    isSubmitting = submitting;

    const submitButton = form.querySelector(
        ".auth-dialog__submit"
    );
    const switchButton = switchArea.querySelector(
        ".auth-dialog__switch-button"
    );

    if (submitButton) {
        submitButton.disabled = submitting;
    }

    if (switchButton) {
        switchButton.disabled = submitting;
    }

    form.setAttribute(
        "aria-busy",
        String(submitting)
    );
  }

  function getFocusableElements() {
    return Array.from(
      dialog.querySelectorAll(
        [
          "button:not([disabled])",
          "input:not([disabled])",
          "a[href]",
          '[tabindex]:not([tabindex="-1"])'
        ].join(", ")
      )
    );
  }

  function openDialog() {
    previousFocus = document.activeElement;

    renderSignIn();

    overlay.hidden = false;
    document.body.classList.add("auth-dialog-open");

    form.querySelector("input")?.focus();
  }

  function closeDialog() {
    overlay.hidden = true;
    document.body.classList.remove("auth-dialog-open");

    if (previousFocus instanceof HTMLElement) {
      previousFocus.focus();
    }
  }

  authTriggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
      if (isSignedIn) {
        localStorage.removeItem("token");
        window.location.reload();
        return;
      }

      openDialog();
    });
  });

  closeButton.addEventListener("click", closeDialog);

  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) {
      closeDialog();
      return;
    }

    if (isSubmitting) {
        return;
    }

    const modeButton = event.target.closest(
      "[data-auth-mode]"
    );

    if (!modeButton) {
      return;
    }

    if (modeButton.dataset.authMode === "signup") {
      renderSignUp();
    } else {
      renderSignIn();
    }

    form.querySelector("input")?.focus();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

  setSubmitting(true);
    clearMessage();

    const formData = new FormData(form);
    const isSignUp = dialog.classList.contains(
      "auth-dialog--signup"
    );

    if (!isSignUp) {
      const payload = {
        email: formData.get("email"),
        password: formData.get("password")
      };

      try {
        const response = await fetch("/api/user/auth", {
          method: "PUT",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (response.ok && result.token) {
          localStorage.setItem("token", result.token);
          window.location.reload();
          return;
      }

      showMessage(
        result.message || "登入失敗，請稍後再試",
        "error"
      );
    } catch (error) {
      console.error("會員登入失敗：", error);

      showMessage(
        "連線失敗，請稍後再試",
        "error"
      );
    } finally {
        setSubmitting(false);
    }

    return;
  }

  const payload = {
    name: formData.get("name"),
    email: formData.get("email"),
    password: formData.get("password")
  };

  try {
    const response = await fetch("/api/user", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const result = await response.json();

    if (response.ok && result.ok === true) {
      showMessage(
        "註冊成功，請登入系統",
        "success"
      );
      form.reset();
      return;
    }

    showMessage(
      result.message || "註冊失敗，請稍後再試",
      "error"
    );
  } catch (error) {
    console.error("會員註冊失敗：", error);
    showMessage(
      "連線失敗，請稍後再試",
      "error"
    );
  } finally {
    setSubmitting(false);
  }
});

  document.addEventListener("keydown", (event) => {
    if (overlay.hidden) {
      return;
    }

    if (event.key === "Escape") {
        closeDialog();
      return;
    }

    if (event.key !== "Tab") {
      return;
    }

    const focusableElements = getFocusableElements();
    const firstElement = focusableElements[0];
    const lastElement =
      focusableElements[focusableElements.length - 1];

    if (
      event.shiftKey
      && document.activeElement === firstElement
    ) {
      event.preventDefault();
      lastElement.focus();
    } else if (
        !event.shiftKey
        && document.activeElement === lastElement
    ) {
        event.preventDefault();
        firstElement.focus();
    }
  });

  checkSignInStatus();

  function clearMessage() {
    message.hidden = true;
    message.textContent = "";
    message.classList.remove(
      "auth-dialog__message--success",
      "auth-dialog__message--error"
    );
    dialog.classList.remove("auth-dialog--has-message");
 }

  function showMessage(text, type) {
    message.textContent = text;
    message.hidden = false;
    message.classList.toggle(
      "auth-dialog__message--success",
      type === "success"
    );
    message.classList.toggle(
      "auth-dialog__message--error",
      type === "error"
    );
    dialog.classList.add("auth-dialog--has-message");
  }
}
