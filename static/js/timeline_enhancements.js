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
    this.init();
  }

  init() {
    const container = document.querySelector('.timeline-container');
    if (!container) return;

    // Insert toolbar
    this.toolbar = document.createElement('div');
    this.toolbar.className = 'timeline-toolbar';
    this.toolbar.innerHTML = `
      <button type="button" data-action="zoom-out" title="Zoom Out (-)">-</button>
      <button type="button" data-action="zoom-in" title="Zoom In (+)">+</button>
      <span class="zoom-level-badge" id="zoomLevelBadge">100%</span>
      <button type="button" data-action="toggle-snap" title="Toggle Snap" class="snap-btn">Snap</button>
      <div class="spacer"></div>
      <span class="snap-indicator">SNAP</span>
    `;
    container.prepend(this.toolbar);
    this.toolbar.addEventListener('click', (e) => {
      const btn = e.target.closest('button');
      if (!btn) return;
      const action = btn.dataset.action;
      if (action === 'zoom-in') this.setZoom(this.zoom * 1.25);
      else if (action === 'zoom-out') this.setZoom(this.zoom / 1.25);
      else if (action === 'toggle-snap') this.toggleSnap();
    });

    // Time ruler wrapper
    const rulerWrapper = document.createElement('div');
    rulerWrapper.className = 'time-ruler-wrapper';
    this.rulerEl = document.createElement('div');
    this.rulerEl.className = 'time-ruler';
    rulerWrapper.appendChild(this.rulerEl);
    container.insertBefore(rulerWrapper, container.querySelector('.timeline-frames'));

    // Waveform overlay
    const overlay = document.createElement('div');
    overlay.className = 'timeline-waveform-overlay';
    this.waveformCanvas = document.createElement('canvas');
    overlay.appendChild(this.waveformCanvas);
    container.appendChild(overlay);

    this.refresh();
  }

  setZoom(z) {
    this.zoom = Math.min(this.maxZoom, Math.max(this.minZoom, z));
    document.documentElement.style.setProperty('--timeline-scale', this.zoom.toString());
    const badge = document.getElementById('zoomLevelBadge');
    if (badge) badge.textContent = `${Math.round(this.zoom * 100)}%`;
    this.applyZoom();
    this.renderRuler();
  }

  applyZoom() {
    const framesContainer = document.getElementById('timelineFrames');
    if (framesContainer) {
      framesContainer.style.transform = `scale(var(--timeline-scale))`;
      framesContainer.classList.add('scaled');
    }
  }

  toggleSnap() {
    this.snapEnabled = !this.snapEnabled;
    document.body.classList.toggle('snap-enabled', this.snapEnabled);
  }

  getTotalDurationMs() {
    return this.app.state.sequence.reduce((acc, f) => acc + (f.ms || f.duration || this.app.state.project.settings.frame_duration), 0);
  }

  refresh() {
    this.renderRuler();
    this.drawWaveform();
    this.renderBeatMarkers();
  }

  renderRuler() {
    if (!this.rulerEl) return;
    this.rulerEl.innerHTML = '';
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
      const tick = document.createElement('div');
      tick.className = `tick ${isMajor ? 'major' : 'minor'}`;
      tick.style.left = `${t * pxPerMs}px`;
      this.rulerEl.appendChild(tick);
      if (isMajor) {
        const label = document.createElement('div');
        label.className = 'label';
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
    const s = (sec % 60).toFixed(2).padStart(5,'0');
    return m ? `${m}:${s}` : s;
  }

  drawWaveform() {
    if (!this.waveformCanvas) return;
    const ctx = this.waveformCanvas.getContext('2d');
    const framesContainer = document.getElementById('timelineFrames');
    if (!framesContainer) return;
    const width = framesContainer.scrollWidth || framesContainer.clientWidth;
    const height = framesContainer.clientHeight || 120;
    this.waveformCanvas.width = width;
    this.waveformCanvas.height = height;
    ctx.clearRect(0,0,width,height);

    // If we have audio peaks from WaveSurfer backend
    const ws = this.app.audioManager?.wavesurfer;
    const backend = ws?._backend;
    if (backend && backend.buffer) {
      const channelData = backend.buffer.getChannelData(0);
      const samples = 800;
      const step = Math.floor(channelData.length / samples);
      ctx.fillStyle = 'rgba(37,99,235,0.5)';
      for (let i=0;i<samples;i++) {
        const sliceStart = i*step;
        let peak = 0;
        for (let j=0;j<step;j++) peak = Math.max(peak, Math.abs(channelData[sliceStart+j]||0));
        const x = (i / samples) * width;
        const barH = peak * height * 0.8;
        ctx.fillRect(x, (height - barH)/2, 2, barH);
      }
    } else {
      // Fallback decorative pattern
      const gradient = ctx.createLinearGradient(0,0,width,height);
      gradient.addColorStop(0,'rgba(37,99,235,0.25)');
      gradient.addColorStop(1,'rgba(16,185,129,0.25)');
      ctx.fillStyle = gradient;
      ctx.fillRect(0,0,width,height);
    }
  }

  renderBeatMarkers() {
    // Placeholder: could use alignment tokens to show phoneme boundaries
    // For now we derive pseudo-beats every 500ms
    const container = document.querySelector('.timeline-container');
    if (!container) return;
    container.querySelectorAll('.timeline-beat-marker').forEach(e => e.remove());
    const total = this.getTotalDurationMs();
    if (!total) return;
    const pxPerMsBase = 0.12 * this.zoom;
    for (let t = 0; t <= total; t += 500) {
      const marker = document.createElement('div');
      marker.className = 'timeline-beat-marker';
      marker.style.left = `${t * pxPerMsBase}px`;
      container.appendChild(marker);
    }
  }
}

// Expose globally for app integration
window.TimelineEnhancer = TimelineEnhancer;
