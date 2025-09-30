// timeline_enhancements.js - WP-UX-004 Enhanced timeline utilities
class TimelineEnhancer {
  constructor(app) {
    this.app = app;
    this.zoom = 1; // multiplier
    this.minZoom = 0.25;
    this.maxZoom = 4;
    this.snapEnabled = true;
    this.snapIntervalMs = 40; // snap every 40ms by default
    this.waveformCanvas = null;
    this.rulerEl = null;
    this.toolbar = null;
    this.beatMarkers = [];
    this.playbackLine = null;
    this.regionSelection = null;
    this.selection = null; // {startMs, endMs}
    this.pxPerMsBase = 0.12;
    this.init();
  }

  init() {
    const container = document.querySelector(".timeline-container");
    if (!container) {
      console.log("Timeline container not found, retrying...");
      setTimeout(() => this.init(), 500);
      return;
    }

    // Insert toolbar
    this.toolbar = document.createElement("div");
    this.toolbar.className = "timeline-toolbar";
    this.toolbar.innerHTML = `
      <button type="button" data-action="zoom-out" title="Zoom Out (-)">-</button>
      <button type="button" data-action="zoom-in" title="Zoom In (+)">+</button>
      <span class="zoom-level-badge" id="zoomLevelBadge">100%</span>
      <button type="button" data-action="toggle-snap" title="Toggle Snap" class="snap-btn">Snap</button>
      <div class="spacer"></div>
      <span class="snap-indicator">SNAP</span>
    `;
    container.prepend(this.toolbar);
    this.toolbar.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (!btn) return;
      const action = btn.dataset.action;
      if (action === "zoom-in") this.setZoom(this.zoom * 1.25);
      else if (action === "zoom-out") this.setZoom(this.zoom / 1.25);
      else if (action === "toggle-snap") this.toggleSnap();
    });

    // Time ruler wrapper - with safety check
    const rulerWrapper = document.createElement("div");
    rulerWrapper.className = "time-ruler-wrapper";
    this.rulerEl = document.createElement("div");
    this.rulerEl.className = "time-ruler";
    rulerWrapper.appendChild(this.rulerEl);

    // Safe insertion - check if timeline-frames exists and is a child
    const timelineFrames =
      container.querySelector(".timeline-frames") ||
      container.querySelector(".timeline-frames-wrapper") ||
      container.querySelector(".timeline-content") ||
      container.firstElementChild;

    if (timelineFrames && container.contains(timelineFrames)) {
      try {
        container.insertBefore(rulerWrapper, timelineFrames);
      } catch (error) {
        console.warn("Timeline insertion failed, using fallback:", error);
        container.appendChild(rulerWrapper);
      }
    } else {
      // Fallback: append to container
      container.appendChild(rulerWrapper);
      console.log(
        "Timeline frames not found or not a child, appending ruler to container"
      );
    }

    // Waveform overlay
    const overlay = document.createElement("div");
    overlay.className = "timeline-waveform-overlay";
    this.waveformCanvas = document.createElement("canvas");
    overlay.appendChild(this.waveformCanvas);
    container.appendChild(overlay);

    // Restore persisted preferences
    try {
      const storedZoom = parseFloat(localStorage.getItem("timelineZoom"));
      if (!isNaN(storedZoom)) this.zoom = storedZoom;
      const storedSnap = localStorage.getItem("timelineSnap");
      if (storedSnap !== null) this.snapEnabled = storedSnap === "1";
      document.body.classList.toggle("snap-enabled", this.snapEnabled);
    } catch (_) {}

    // Playback line
    this.playbackLine = document.createElement("div");
    this.playbackLine.className = "timeline-playback-line";
    container.appendChild(this.playbackLine);

    // Region selection overlay
    this.regionSelection = document.createElement("div");
    this.regionSelection.className = "timeline-region-selection";
    container.appendChild(this.regionSelection);

    // Selection toolbar (hidden until selection exists)
    this.selectionToolbar = document.createElement("div");
    this.selectionToolbar.className = "timeline-selection-toolbar";
    this.selectionToolbar.style.display = "none";
    this.selectionToolbar.innerHTML = `
      <button data-act="trim" class="danger" title="Trim sequence to selection">Trim</button>
      <button data-act="dup" title="Duplicate selection">Duplicate</button>
      <button data-act="export-json" class="secondary" title="Export selection as JSON">Export JSON</button>
      <button data-act="export-video" class="secondary" title="Export selection video">Export Video</button>
      <span class="sel-meta" style="color:#9ca3af;margin-left:4px;"></span>
    `;
    container.appendChild(this.selectionToolbar);

    this.selectionToolbar.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-act]");
      if (!btn) return;
      const act = btn.getAttribute("data-act");
      if (!this.selection) return;
      if (act === "trim") this.trimToSelection();
      else if (act === "dup") this.duplicateSelection();
      else if (act === "export-json") this.exportSelectionJSON();
      else if (act === "export-video") this.exportSelectionVideo();
    });

    // Context menu
    this.contextMenu = document.createElement("div");
    this.contextMenu.className = "timeline-context-menu";
    this.contextMenu.innerHTML = `
      <button data-act="trim">Trim to Selection</button>
      <button data-act="dup">Duplicate Selection</button>
      <button data-act="export-json">Export Selection JSON</button>
      <button data-act="export-video">Export Selection Video</button>
      <button data-act="clear">Clear Selection</button>
    `;
    document.body.appendChild(this.contextMenu);
    this.contextMenu.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-act]");
      if (!b) return;
      const a = b.getAttribute("data-act");
      this.handleContextAction(a);
      this.hideContextMenu();
    });
    window.addEventListener("click", () => this.hideContextMenu());
    window.addEventListener("contextmenu", (e) => {
      if (
        e.target === this.regionSelection ||
        this.regionSelection.contains(e.target)
      ) {
        e.preventDefault();
        this.showContextMenu(e.clientX, e.clientY);
      }
    });

    // Keyboard shortcuts for next/prev token
    window.addEventListener("keydown", (e) => {
      if (["INPUT", "TEXTAREA"].includes(document.activeElement.tagName))
        return;
      if (!this.app.alignmentTokens) return;
      if (e.key === "[") {
        this.jumpToken(-1);
        e.preventDefault();
      } else if (e.key === "]") {
        this.jumpToken(1);
        e.preventDefault();
      }
    });

    // Region selection interaction (on ruler)
    let selecting = false;
    let startX = 0;
    let startMs = 0;
    const rulerWrapperEl = container.querySelector(".time-ruler-wrapper");
    rulerWrapperEl.addEventListener("mousedown", (e) => {
      if (e.button !== 0) return; // left only
      const total = this.getTotalDurationMs();
      if (!total) return;
      selecting = true;
      startX = e.clientX;
      startMs = this.pxToMs(this.getRelativeX(e, rulerWrapperEl));
      this.selection = { startMs, endMs: startMs };
      this.updateRegionSelection();
      e.preventDefault();
    });
    window.addEventListener("mousemove", (e) => {
      if (!selecting) return;
      const currentMs = this.pxToMs(this.getRelativeX(e, rulerWrapperEl));
      this.selection.endMs = Math.max(
        0,
        Math.min(this.getTotalDurationMs(), currentMs)
      );
      this.updateRegionSelection();
    });
    window.addEventListener("mouseup", () => {
      if (selecting) {
        selecting = false;
        this.normalizeSelection();
      }
    });

    this.refresh();
  }

  setZoom(z) {
    this.zoom = Math.min(this.maxZoom, Math.max(this.minZoom, z));
    document.documentElement.style.setProperty(
      "--timeline-scale",
      this.zoom.toString()
    );
    const badge = document.getElementById("zoomLevelBadge");
    if (badge) badge.textContent = `${Math.round(this.zoom * 100)}%`;
    this.applyZoom();
    this.renderRuler();
    try {
      localStorage.setItem("timelineZoom", this.zoom.toString());
    } catch (_) {}
    this.updatePlaybackLine();
    this.updateRegionSelection();
  }

  applyZoom() {
    const framesContainer = document.getElementById("timelineFrames");
    if (framesContainer) {
      framesContainer.style.transform = `scale(var(--timeline-scale))`;
      framesContainer.classList.add("scaled");
    }
  }

  toggleSnap() {
    this.snapEnabled = !this.snapEnabled;
    document.body.classList.toggle("snap-enabled", this.snapEnabled);
    try {
      localStorage.setItem("timelineSnap", this.snapEnabled ? "1" : "0");
    } catch (_) {}
  }

  getTotalDurationMs() {
    return this.app.state.sequence.reduce(
      (acc, f) =>
        acc +
        (f.ms || f.duration || this.app.state.project.settings.frame_duration),
      0
    );
  }

  refresh() {
    this.renderRuler();
    this.drawWaveform();
    this.renderTokenMarkers();
    this.updatePlaybackLine();
    this.updateRegionSelection();
  }

  renderRuler() {
    if (!this.rulerEl) return;
    this.rulerEl.innerHTML = "";
    const total = this.getTotalDurationMs();
    if (!total) return;
    const pxPerMsBase = 0.12; // baseline scale
    const pxPerMs = pxPerMsBase * this.zoom;
    const majorEveryMs = this.chooseMajorTick(total);
    const minorEveryMs = majorEveryMs / 4;
    const totalPx = total * pxPerMs;
    this.rulerEl.style.width = `${totalPx}px`;

    for (let t = 0; t <= total; t += minorEveryMs) {
      const isMajor = t % majorEveryMs === 0;
      const tick = document.createElement("div");
      tick.className = `tick ${isMajor ? "major" : "minor"}`;
      tick.style.left = `${t * pxPerMs}px`;
      this.rulerEl.appendChild(tick);
      if (isMajor) {
        const label = document.createElement("div");
        label.className = "label";
        label.style.left = `${t * pxPerMs}px`;
        label.textContent = this.formatTimeMs(t);
        this.rulerEl.appendChild(label);
      }
    }
  }

  chooseMajorTick(totalMs) {
    const candidates = [200, 250, 500, 1000, 2000, 5000];
    for (const c of candidates) {
      if (totalMs / c <= 16) return c; // aim for up to 16 major ticks
    }
    return 10000;
  }

  formatTimeMs(ms) {
    const sec = ms / 1000;
    if (sec < 1) return `${ms}ms`;
    const m = Math.floor(sec / 60);
    const s = (sec % 60).toFixed(2).padStart(5, "0");
    return m ? `${m}:${s}` : s;
  }

  drawWaveform() {
    if (!this.waveformCanvas) return;
    const ctx = this.waveformCanvas.getContext("2d");
    const framesContainer = document.getElementById("timelineFrames");
    if (!framesContainer) return;
    const width = framesContainer.scrollWidth || framesContainer.clientWidth;
    const height = framesContainer.clientHeight || 120;
    this.waveformCanvas.width = width;
    this.waveformCanvas.height = height;
    ctx.clearRect(0, 0, width, height);

    // If we have audio peaks from WaveSurfer backend
    const ws = this.app.audioManager?.wavesurfer;
    const backend = ws?._backend;
    if (backend && backend.buffer) {
      const channelData = backend.buffer.getChannelData(0);
      const samples = 800;
      const step = Math.floor(channelData.length / samples);
      ctx.fillStyle = "rgba(37,99,235,0.5)";
      for (let i = 0; i < samples; i++) {
        const sliceStart = i * step;
        let peak = 0;
        for (let j = 0; j < step; j++)
          peak = Math.max(peak, Math.abs(channelData[sliceStart + j] || 0));
        const x = (i / samples) * width;
        const barH = peak * height * 0.8;
        ctx.fillRect(x, (height - barH) / 2, 2, barH);
      }
    } else {
      // Fallback decorative pattern
      const gradient = ctx.createLinearGradient(0, 0, width, height);
      gradient.addColorStop(0, "rgba(37,99,235,0.25)");
      gradient.addColorStop(1, "rgba(16,185,129,0.25)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);
    }
  }

  renderTokenMarkers() {
    const container = document.querySelector(".timeline-container");
    if (!container) return;
    container
      .querySelectorAll(".timeline-beat-marker, .timeline-token-marker")
      .forEach((e) => e.remove());
    const total = this.getTotalDurationMs();
    if (!total) return;
    const tokens =
      this.app.alignmentTokens || this.app.audioManager?.alignmentTokens;
    const pxPerMs = this.pxPerMsBase * this.zoom;
    if (Array.isArray(tokens) && tokens.length) {
      // Density management: if zoomed out, skip some phoneme markers
      let phonemeSkip = 0;
      if (this.zoom < 0.5) phonemeSkip = 3;
      else if (this.zoom < 0.8) phonemeSkip = 1;
      let phonemeIndex = 0;
      tokens.forEach((tok) => {
        const start = tok.start_ms ?? tok.start ?? null;
        if (start == null) return;
        if (
          tok.type === "phoneme" &&
          phonemeSkip &&
          phonemeIndex++ % (phonemeSkip + 1) !== 0
        )
          return;
        const marker = document.createElement("div");
        marker.className = `timeline-token-marker ${tok.type || "token"}`;
        marker.style.left = `${start * pxPerMs}px`;
        marker.title = tok.text || tok.type;
        container.appendChild(marker);
        if (tok.type === "word") {
          const label = document.createElement("div");
          label.className = "timeline-token-label";
          label.textContent = tok.text;
          label.style.left = `${start * pxPerMs}px`;
          container.appendChild(label);
        }
      });
    } else {
      // fallback pseudo markers every 500ms
      for (let t = 0; t <= total; t += 500) {
        const marker = document.createElement("div");
        marker.className = "timeline-beat-marker";
        marker.style.left = `${t * pxPerMs}px`;
        container.appendChild(marker);
      }
    }
  }

  updatePlaybackPositionByFrame(frameIndex) {
    // derive ms using cumulative frame durations if available on app
    if (!this.app.frameStartTimes || frameIndex < 0) return;
    const ms = this.app.frameStartTimes[frameIndex] || 0;
    this.updatePlaybackLine(ms);
  }

  updatePlaybackLine(ms) {
    if (!this.playbackLine) return;
    const total = this.getTotalDurationMs();
    if (!total) {
      this.playbackLine.style.display = "none";
      return;
    }
    if (typeof ms !== "number") {
      // attempt current frame start
      if (this.app.frameStartTimes)
        ms = this.app.frameStartTimes[this.app.state.currentFrame] || 0;
      else ms = 0;
    }
    const pxPerMs = this.pxPerMsBase * this.zoom;
    this.playbackLine.style.display = "block";
    this.playbackLine.style.left = `${ms * pxPerMs}px`;
  }

  getRelativeX(e, el) {
    const rect = el.getBoundingClientRect();
    return e.clientX - rect.left;
  }

  pxToMs(px) {
    return px / (this.pxPerMsBase * this.zoom);
  }

  normalizeSelection() {
    if (!this.selection) return;
    const { startMs, endMs } = this.selection;
    if (endMs < startMs) {
      this.selection = { startMs: endMs, endMs: startMs };
    }
  }

  updateRegionSelection() {
    if (!this.regionSelection || !this.selection) {
      if (this.regionSelection) this.regionSelection.style.display = "none";
      return;
    }
    const { startMs, endMs } = this.selection;
    const pxPerMs = this.pxPerMsBase * this.zoom;
    const left = Math.min(startMs, endMs) * pxPerMs;
    const width = Math.abs(endMs - startMs) * pxPerMs;
    this.regionSelection.style.display = "block";
    this.regionSelection.style.left = `${left}px`;
    this.regionSelection.style.width = `${width}px`;
    // Position toolbar centered above selection
    if (this.selectionToolbar) {
      this.selectionToolbar.style.display = "flex";
      this.selectionToolbar.style.left = `${left + width / 2}px`;
      this.selectionToolbar.style.transform = "translateX(-50%)";
      this.updateSelectionMeta();
    }
  }

  updateSelectionMeta() {
    if (!this.selection || !this.selectionToolbar) return;
    const { startMs, endMs } = this.selection;
    const dur = Math.abs(endMs - startMs);
    // Estimate frame count via frameStartTimes
    let frames = 0;
    if (this.app.frameStartTimes) {
      const sIdx = this.app.getFrameIndexForMs
        ? this.app.getFrameIndexForMs(startMs)
        : this.binaryFrameIndex(startMs);
      const eIdx = this.app.getFrameIndexForMs
        ? this.app.getFrameIndexForMs(endMs)
        : this.binaryFrameIndex(endMs);
      frames = eIdx - sIdx + 1;
    }
    const metaEl = this.selectionToolbar.querySelector(".sel-meta");
    if (metaEl) metaEl.textContent = `${dur.toFixed(0)}ms / ${frames}f`;
    // Also push to status bar
    const statusMessage = document.getElementById("statusMessage");
    if (statusMessage)
      statusMessage.textContent = `Selection: ${dur.toFixed(
        0
      )}ms (${frames} frames)`;
  }

  hideContextMenu() {
    if (this.contextMenu) this.contextMenu.style.display = "none";
  }
  showContextMenu(x, y) {
    if (!this.selection) return;
    this.contextMenu.style.display = "block";
    this.contextMenu.style.left = x + "px";
    this.contextMenu.style.top = y + "px";
  }
  handleContextAction(act) {
    if (!this.selection) return;
    if (act === "trim") this.trimToSelection();
    else if (act === "dup") this.duplicateSelection();
    else if (act === "export-json") this.exportSelectionJSON();
    else if (act === "export-video") this.exportSelectionVideo();
    else if (act === "clear") {
      this.selection = null;
      this.updateRegionSelection();
      this.selectionToolbar.style.display = "none";
    }
  }

  binaryFrameIndex(ms) {
    // fallback binary search
    const starts = this.app.frameStartTimes;
    if (!starts) return 0;
    let lo = 0,
      hi = starts.length - 1,
      ans = 0;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (starts[mid] <= ms) {
        ans = mid;
        lo = mid + 1;
      } else hi = mid - 1;
    }
    return ans;
  }

  getSelectionFrameRange() {
    if (!this.selection || !this.app.frameStartTimes) return null;
    const { startMs, endMs } = this.selection;
    const startIdx = this.binaryFrameIndex(Math.min(startMs, endMs));
    const endIdx = this.binaryFrameIndex(Math.max(startMs, endMs));
    return { startIdx, endIdx };
  }

  trimToSelection() {
    const range = this.getSelectionFrameRange();
    if (!range) return;
    const { startIdx, endIdx } = range;
    this.app.state.sequence = this.app.state.sequence.slice(
      startIdx,
      endIdx + 1
    );
    this.selection = null;
    this.selectionToolbar.style.display = "none";
    this.app.updateTimeline();
    this.app.reportError("Sequence trimmed to selection", {
      level: "success",
      autoDismiss: true,
    });
  }

  duplicateSelection() {
    const range = this.getSelectionFrameRange();
    if (!range) return;
    const { startIdx, endIdx } = range;
    const segment = this.app.state.sequence
      .slice(startIdx, endIdx + 1)
      .map((f) => ({ ...f }));
    // Insert immediately after endIdx
    this.app.state.sequence.splice(endIdx + 1, 0, ...segment);
    this.app.updateTimeline();
    this.app.reportError("Selection duplicated", {
      level: "success",
      autoDismiss: true,
    });
  }

  exportSelectionJSON() {
    const range = this.getSelectionFrameRange();
    if (!range) return;
    const { startIdx, endIdx } = range;
    const frames = this.app.state.sequence.slice(startIdx, endIdx + 1);
    const payload = { selection: { startIdx, endIdx }, frames };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    this.downloadBlob(blob, `selection_${startIdx}-${endIdx}.json`);
    this.app.reportError("Selection JSON exported", {
      level: "success",
      autoDismiss: true,
    });
  }

  exportSelectionVideo() {
    const range = this.getSelectionFrameRange();
    if (!range) return;
    const { startIdx, endIdx } = range;
    // Simple client-side export request (assuming backend can accept indices)
    this.app
      .apiCall("/export/selection", "POST", { start: startIdx, end: endIdx })
      .then(() => {
        this.app.reportError("Selection video export started", {
          level: "info",
          autoDismiss: true,
        });
      })
      .catch((err) => {
        /* apiCall already reports */
      });
  }

  downloadBlob(blob, filename) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(a.href);
      a.remove();
    }, 0);
  }

  jumpToken(direction) {
    const tokens =
      this.app.alignmentTokens || this.app.audioManager?.alignmentTokens;
    if (!Array.isArray(tokens) || !tokens.length) return;
    if (!this.app.frameStartTimes) return;
    // Current ms
    const currentMs =
      this.app.frameStartTimes[this.app.state.currentFrame] || 0;
    const starts = tokens
      .map((t) => t.start_ms ?? t.start ?? 0)
      .filter((v) => typeof v === "number")
      .sort((a, b) => a - b);
    if (!starts.length) return;
    if (direction > 0) {
      const next = starts.find((s) => s > currentMs + 1);
      if (next != null) {
        const idx = this.app.getFrameIndexForMs
          ? this.app.getFrameIndexForMs(next)
          : this.binaryFrameIndex(next);
        this.app.selectFrame(idx);
      }
    } else {
      for (let i = starts.length - 1; i >= 0; i--) {
        if (starts[i] < currentMs - 1) {
          const idx = this.app.getFrameIndexForMs
            ? this.app.getFrameIndexForMs(starts[i])
            : this.binaryFrameIndex(starts[i]);
          this.app.selectFrame(idx);
          break;
        }
      }
    }
  }
}

// Expose globally for app integration
window.TimelineEnhancer = TimelineEnhancer;
