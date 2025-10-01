// video_editor_timeline_bindings.js
// Timeline initialization, overlay positioning, drag & edit helpers extracted from video_editor.js

(function () {
  if (!window.VideoEditorModule) return;
  window.FaceSeqEditorModules = window.FaceSeqEditorModules || {};
  window.FaceSeqEditorModules.timeline = true;
  const proto = window.VideoEditorModule.prototype;

  proto._applyOverlayPosition = function () {
    if (!this.overlayElement || !this.videoPreview) return;
    const rect = this.videoPreview.getBoundingClientRect();
    const x = (this.overlayPosition.xPercent / 100) * rect.width;
    const y = (this.overlayPosition.yPercent / 100) * rect.height;
    this.overlayElement.style.left = x + "px";
    this.overlayElement.style.top = y + "px";
    this.overlayElement.style.transform = "translate(-50%, -50%)";
    const coord = this.overlayElement.querySelector?.(".subtitle-coords");
    if (coord)
      coord.textContent = `${this.overlayPosition.xPercent.toFixed(
        1
      )}%, ${this.overlayPosition.yPercent.toFixed(1)}%`;
  };

  proto.enableOverlayDragging = function (overlay, handle) {
    if (!overlay) return;
    let dragging = false;
    let startX = 0,
      startY = 0,
      startXP = 0,
      startYP = 0;
    const down = (e) => {
      if (handle && e.target !== handle && !handle.contains(e.target)) return;
      dragging = true;
      const rect = overlay.getBoundingClientRect();
      startX = e.clientX;
      startY = e.clientY;
      const videoRect = this.videoPreview.getBoundingClientRect();
      startXP =
        ((rect.left + rect.width / 2 - videoRect.left) / videoRect.width) * 100;
      startYP =
        ((rect.top + rect.height / 2 - videoRect.top) / videoRect.height) * 100;
      overlay.classList.add("dragging");
      e.preventDefault();
    };
    const move = (e) => {
      if (!dragging) return;
      const videoRect = this.videoPreview.getBoundingClientRect();
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      const newXP = startXP + (dx / videoRect.width) * 100;
      const newYP = startYP + (dy / videoRect.height) * 100;
      this.overlayPosition.xPercent = Math.min(95, Math.max(5, newXP));
      this.overlayPosition.yPercent = Math.min(95, Math.max(5, newYP));
      this.overlayPosition.custom = true;
      this._applyOverlayPosition();
    };
    const up = () => {
      if (dragging) {
        dragging = false;
        overlay.classList.remove("dragging");
        try {
          localStorage.setItem(
            "subtitleOverlayPosition",
            JSON.stringify(this.overlayPosition)
          );
        } catch (_) {}
      }
    };
    overlay.addEventListener("mousedown", down);
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
  };

  proto._computeDynamicVerticalPosition = function (style) {
    const controls = document.querySelector(
      ".video-controls, .player-controls"
    );
    if (controls && this.videoPreview) {
      const videoRect = this.videoPreview.getBoundingClientRect();
      const controlsRect = controls.getBoundingClientRect();
      if (
        controlsRect.top < videoRect.bottom &&
        controlsRect.top > videoRect.bottom - videoRect.height * 0.25
      ) {
        return "top";
      }
    }
    return style.verticalPosition || "bottom";
  };

  proto._formatSubtitleLines = function (text, style) {
    if (!text) return "";
    const words = text.split(/\s+/);
    if (words.length <= 6) return this._escapeHtml(text);
    const targetChars = Math.ceil(text.length / 2);
    let line1 = "",
      line2 = "",
      acc = 0;
    for (const w of words) {
      if (acc + w.length + 1 < targetChars || line1.length === 0) {
        line1 += (line1 ? " " : "") + w;
        acc += w.length + 1;
      } else {
        line2 += (line2 ? " " : "") + w;
      }
    }
    if (!line2) return this._escapeHtml(line1);
    return `${this._escapeHtml(line1)}<br/>${this._escapeHtml(line2)}`;
  };

  proto._escapeHtml = function (str) {
    return str.replace(
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
  };

  proto.hexToRgba = function (hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };
})();
