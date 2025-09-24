// ErrorToast.js - contextual toast & inline error system (WP-UX-007)
(function(global){
  class ErrorToastManager {
    constructor() {
      this.queue = [];
      this.active = null;
      this.container = null;
      this.defaultTimeout = 6000;
      this.maxVisible = 3;
      this.idCounter = 0;
      this.ensureContainer();
    }

    ensureContainer() {
      if (!this.container) {
        this.container = document.createElement('div');
        this.container.className = 'toast-stack';
        this.container.setAttribute('role','region');
        this.container.setAttribute('aria-label','Notifications');
        document.body.appendChild(this.container);
      }
    }

    show(message, options = {}) {
      const {
        level = 'error', // info | warning | error | success
        autoDismiss = true,
        timeout = this.defaultTimeout,
        action,
        actionLabel = 'Retry',
        onDismiss,
        id = `toast-${++this.idCounter}`
      } = options;

      const toastEl = document.createElement('div');
      toastEl.className = `error-toast level-${level}`;
      toastEl.setAttribute('role','alert');
      toastEl.setAttribute('data-toast-id', id);
      toastEl.innerHTML = `
        <div class="toast-icon">${this.getIcon(level)}</div>
        <div class="toast-content">
          <div class="toast-message">${this.escape(message)}</div>
          ${action ? `<button class="toast-action" type="button">${actionLabel}</button>` : ''}
        </div>
        <button class="toast-close" type="button" aria-label="Dismiss">&times;</button>
        <div class="toast-progress"></div>
      `;

      const closeBtn = toastEl.querySelector('.toast-close');
      closeBtn.addEventListener('click', () => this.dismiss(id, onDismiss));

      if (action) {
        const actionBtn = toastEl.querySelector('.toast-action');
        actionBtn?.addEventListener('click', async () => {
          actionBtn.disabled = true;
            try {
              const res = await action();
              this.updateToast(id, { level: 'success', message: 'Success' });
              setTimeout(()=> this.dismiss(id, onDismiss), 1200);
              return res;
            } catch(err) {
              this.updateToast(id, { level: 'error', message: err?.message || 'Retry failed' });
              actionBtn.disabled = false;
            }
        });
      }

      // Progress bar + auto-dismiss
      if (autoDismiss) {
        const progressEl = toastEl.querySelector('.toast-progress');
        progressEl.style.transition = `width ${timeout}ms linear`;
        setTimeout(()=>{ progressEl.style.width = '0%'; }, 20);
        setTimeout(()=> this.dismiss(id, onDismiss), timeout + 50);
      }

      this.container.appendChild(toastEl);
      requestAnimationFrame(() => toastEl.classList.add('visible'));

      // Trim excess visible toasts
      this.trimVisible();
      return id;
    }

    updateToast(id, { message, level }) {
      const el = this.container.querySelector(`[data-toast-id="${id}"]`);
      if (!el) return;
      if (message) el.querySelector('.toast-message').textContent = message;
      if (level) {
        el.className = el.className.replace(/level-[a-z]+/, '');
        el.classList.add(`level-${level}`);
      }
    }

    dismiss(id, onDismiss) {
      const el = this.container.querySelector(`[data-toast-id="${id}"]`);
      if (!el) return;
      el.classList.remove('visible');
      el.addEventListener('transitionend', () => el.remove(), { once: true });
      if (onDismiss) try { onDismiss(); } catch(_) {}
    }

    trimVisible() {
      const toasts = Array.from(this.container.children);
      if (toasts.length <= this.maxVisible) return;
      const excess = toasts.slice(0, toasts.length - this.maxVisible);
      excess.forEach(el => this.dismiss(el.getAttribute('data-toast-id')));
    }

    fieldError(inputEl, message) {
      if (!inputEl) return;
      const wrap = inputEl.closest('.input-group, .setting-item') || inputEl.parentElement;
      if (!wrap) return;
      wrap.classList.add('has-error');
      inputEl.setAttribute('aria-invalid','true');
      let hint = wrap.querySelector('.error-hint');
      if (!hint) {
        hint = document.createElement('div');
        hint.className = 'error-hint';
        wrap.appendChild(hint);
      }
      hint.textContent = message;
    }

    clearFieldError(inputEl) {
      const wrap = inputEl.closest('.input-group, .setting-item') || inputEl.parentElement;
      if (!wrap) return;
      wrap.classList.remove('has-error');
      inputEl.removeAttribute('aria-invalid');
      const hint = wrap.querySelector('.error-hint');
      if (hint) hint.remove();
    }

    getIcon(level) {
      switch(level) {
        case 'info': return '<i class="fas fa-info-circle"></i>';
        case 'warning': return '<i class="fas fa-exclamation-triangle"></i>';
        case 'success': return '<i class="fas fa-check-circle"></i>';
        default: return '<i class="fas fa-times-circle"></i>';
      }
    }

    escape(str) {
      return String(str).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
    }
  }

  global.ErrorToastManager = ErrorToastManager;
})(window);
