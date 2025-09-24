// ErrorToast.js - contextual toast & inline error system (WP-UX-007)
(function (global) {
  class ErrorToastManager {
    constructor() {
      this.queue = [];
      this.active = null;
      this.container = null;
      this.defaultTimeout = 6000;
      this.maxVisible = 3;
      this.idCounter = 0;
      this.lastMessages = new Map(); // message -> timestamp for debounce
      this.debounceWindowMs = 4000;
      this.instrumentation = window.ErrorInstrumentation || null;
      this.ensureContainer();
    }

    ensureContainer() {
      if (!this.container) {
        this.container = document.createElement("div");
        this.container.className = "toast-stack";
        this.container.setAttribute("role", "region");
        this.container.setAttribute("aria-label", "Notifications");
        document.body.appendChild(this.container);
      }
    }

    show(message, options = {}) {
      const {
        level = "error", // info | warning | error | success
        autoDismiss = true,
        timeout = this.defaultTimeout,
        action,
        actionLabel = "Retry",
        onDismiss,
        id = `toast-${++this.idCounter}`,
      } = options;

      // Debounce duplicate messages
      const now = Date.now();
      const last = this.lastMessages.get(message);
      if (last && now - last < this.debounceWindowMs) {
        // Instead of ignoring entirely, gently pulse existing toast
        const existing = this.container
          .querySelector(".error-toast .toast-message")
          ?.closest(".error-toast");
        if (existing) {
          existing.classList.remove("pulse-dup");
          void existing.offsetWidth; // force reflow
          existing.classList.add("pulse-dup");
        }
        return null;
      }
      this.lastMessages.set(message, now);

      const toastEl = document.createElement("div");
      toastEl.className = `error-toast level-${level}`;
      toastEl.setAttribute("role", "alert");
      toastEl.setAttribute("data-toast-id", id);
      toastEl.innerHTML = `
        <div class="toast-icon">${this.getIcon(level)}</div>
        <div class="toast-content">
          <div class="toast-message">${this.escape(message)}</div>
          ${
            action
              ? `<button class="toast-action" type="button">${actionLabel}</button>`
              : ""
          }
        </div>
        <button class="toast-close" type="button" aria-label="Dismiss">&times;</button>
        <div class="toast-progress"></div>
      `;

      const closeBtn = toastEl.querySelector(".toast-close");
      closeBtn.addEventListener("click", () => this.dismiss(id, onDismiss));

      if (action) {
        const actionBtn = toastEl.querySelector(".toast-action");
        actionBtn?.addEventListener("click", async () => {
          actionBtn.disabled = true;
          try {
            const res = await action();
            this.updateToast(id, { level: "success", message: "Success" });
            setTimeout(() => this.dismiss(id, onDismiss), 1200);
            return res;
          } catch (err) {
            this.updateToast(id, {
              level: "error",
              message: err?.message || "Retry failed",
            });
            actionBtn.disabled = false;
          }
        });
      }

      // Progress bar + auto-dismiss
      if (autoDismiss) {
        const progressEl = toastEl.querySelector(".toast-progress");
        progressEl.style.transition = `width ${timeout}ms linear`;
        setTimeout(() => {
          progressEl.style.width = "0%";
        }, 20);
        setTimeout(() => this.dismiss(id, onDismiss), timeout + 50);
      }

      this.container.appendChild(toastEl);
      requestAnimationFrame(() => toastEl.classList.add("visible"));

      // Instrumentation hook
      try {
        this.instrumentation?.record?.("toast.shown", { id, level, message });
      } catch (_) {}

      // Trim excess visible toasts
      this.trimVisible();
      return id;
    }

    updateToast(id, { message, level }) {
      const el = this.container.querySelector(`[data-toast-id="${id}"]`);
      if (!el) return;
      if (message) el.querySelector(".toast-message").textContent = message;
      if (level) {
        el.className = el.className.replace(/level-[a-z]+/, "");
        el.classList.add(`level-${level}`);
      }
    }

    dismiss(id, onDismiss) {
      const el = this.container.querySelector(`[data-toast-id="${id}"]`);
      if (!el) return;
      el.classList.remove("visible");
      el.addEventListener("transitionend", () => el.remove(), { once: true });
      try {
        this.instrumentation?.record?.("toast.dismissed", { id });
      } catch (_) {}
      if (onDismiss)
        try {
          onDismiss();
        } catch (_) {}
    }

    trimVisible() {
      const toasts = Array.from(this.container.children);
      if (toasts.length <= this.maxVisible) return;
      const excess = toasts.slice(0, toasts.length - this.maxVisible);
      excess.forEach((el) => this.dismiss(el.getAttribute("data-toast-id")));
    }

    fieldError(inputEl, message) {
      if (!inputEl) return;
      const wrap =
        inputEl.closest(".input-group, .setting-item") || inputEl.parentElement;
      if (!wrap) return;
      wrap.classList.add("has-error");
      inputEl.setAttribute("aria-invalid", "true");
      let hint = wrap.querySelector(".error-hint");
      if (!hint) {
        hint = document.createElement("div");
        hint.className = "error-hint";
        wrap.appendChild(hint);
      }
      hint.textContent = message;
    }

    clearFieldError(inputEl) {
      const wrap =
        inputEl.closest(".input-group, .setting-item") || inputEl.parentElement;
      if (!wrap) return;
      wrap.classList.remove("has-error");
      inputEl.removeAttribute("aria-invalid");
      const hint = wrap.querySelector(".error-hint");
      if (hint) hint.remove();
    }

    getIcon(level) {
      switch (level) {
        case "info":
          return '<i class="fas fa-info-circle"></i>';
        case "warning":
          return '<i class="fas fa-exclamation-triangle"></i>';
        case "success":
          return '<i class="fas fa-check-circle"></i>';
        default:
          return '<i class="fas fa-times-circle"></i>';
      }
    }

    escape(str) {
      return String(str).replace(
        /[&<>"']/g,
        (c) =>
          ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;",
          }[c])
      );
    }
  }

  global.ErrorToastManager = ErrorToastManager;

  // Basic instrumentation stub (can be replaced by real analytics)
  if (!global.ErrorInstrumentation) {
    global.ErrorInstrumentation = {
      buffer: [],
      record(event, payload) {
        this.buffer.push({ event, payload, t: Date.now() });
        if (this.buffer.length > 200) this.buffer.shift();
        if (console && console.debug)
          console.debug("[ErrorInstrumentation]", event, payload);
      },
      export() {
        return [...this.buffer];
      },
    };
  }
})(window);
