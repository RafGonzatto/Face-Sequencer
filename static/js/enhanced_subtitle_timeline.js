/**
 * Enhanced Subtitle Timeline UI - Phase 2 Implementation
 * Interactive timeline for subtitle segment editing with advanced features
 */

class EnhancedSubtitleTimeline extends EventTarget {
  constructor(container, videoEditor) {
    super();
    this.container = container;
    this.videoEditor = videoEditor;
    this.segments = [];
    this.selectedSegments = [];
    this.dragState = null;
    this.zoomLevel = 1;
    this.scrollPosition = 0;
    this.pixelsPerSecond = 50;
    this.snappingEnabled = true;
    this.snapThreshold = 0.1; // 100ms
    this.currentTime = 0;

    // Audio waveform integration
    this.waveformData = null;
    this.waveformCanvas = null;

    this.initializeUI();
    this.bindEvents();

    console.log("🎬 Enhanced Subtitle Timeline initialized");
  }

  initializeUI() {
    // Clear existing content
    this.container.innerHTML = "";

    // Create timeline structure
    const timelineHTML = `
      <div class="subtitle-timeline-header">
        <div class="timeline-controls">
          <button class="timeline-btn" id="zoomIn" title="Zoom In">
            <i class="fas fa-search-plus"></i>
          </button>
          <button class="timeline-btn" id="zoomOut" title="Zoom Out">
            <i class="fas fa-search-minus"></i>
          </button>
          <button class="timeline-btn" id="fitToView" title="Fit to View">
            <i class="fas fa-expand-arrows-alt"></i>
          </button>
          <div class="timeline-divider"></div>
          <button class="timeline-btn" id="enableSnapping" class="active" title="Toggle Snapping">
            <i class="fas fa-magnet"></i>
          </button>
          <button class="timeline-btn" id="autoAlign" title="Auto-align Segments">
            <i class="fas fa-align-center"></i>
          </button>
        </div>
        <div class="timeline-info">
          <span class="zoom-level">Zoom: <span id="zoomDisplay">100%</span></span>
          <span class="timeline-duration">Duration: <span id="timelineDuration">00:00</span></span>
        </div>
      </div>
      
      <div class="subtitle-timeline-content">
        <!-- Time ruler -->
        <div class="timeline-ruler" id="timelineRuler">
          <canvas class="ruler-canvas" id="rulerCanvas"></canvas>
        </div>
        
        <!-- Waveform display -->
        <div class="timeline-waveform" id="timelineWaveform">
          <canvas class="waveform-canvas" id="waveformCanvas"></canvas>
        </div>
        
        <!-- Subtitle tracks -->
        <div class="subtitle-tracks" id="subtitleTracks">
          <div class="subtitle-track" id="mainSubtitleTrack">
            <div class="track-header">
              <span class="track-title">Subtitles</span>
              <button class="track-toggle" title="Toggle Track">
                <i class="fas fa-eye"></i>
              </button>
            </div>
            <div class="track-content" id="trackContent">
              <!-- Subtitle segments will be rendered here -->
            </div>
          </div>
        </div>
        
        <!-- Playhead -->
        <div class="timeline-playhead" id="timelinePlayhead">
          <div class="playhead-line"></div>
          <div class="playhead-handle"></div>
        </div>
        
        <!-- Selection overlay -->
        <div class="timeline-selection" id="timelineSelection" style="display: none;"></div>
      </div>
      
      <!-- Subtitle editing panel -->
      <div class="subtitle-edit-panel" id="subtitleEditPanel" style="display: none;">
        <div class="edit-panel-header">
          <h3>Edit Subtitle</h3>
          <button class="close-edit-panel" id="closeEditPanel">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="edit-panel-content">
          <div class="edit-field">
            <label for="segmentText">Text:</label>
            <textarea id="segmentText" rows="3" placeholder="Enter subtitle text..."></textarea>
            <div class="char-count">
              <span id="charCount">0</span> / <span id="maxChars">50</span> characters
            </div>
          </div>
          <div class="edit-timing">
            <div class="timing-field">
              <label for="startTime">Start Time:</label>
              <input type="number" id="startTime" step="0.1" min="0">
            </div>
            <div class="timing-field">
              <label for="endTime">End Time:</label>
              <input type="number" id="endTime" step="0.1" min="0">
            </div>
            <div class="timing-field">
              <label for="duration">Duration:</label>
              <input type="number" id="duration" step="0.1" min="0.1" readonly>
            </div>
          </div>
          <div class="edit-actions">
            <button class="btn-secondary" id="cancelEdit">Cancel</button>
            <button class="btn-primary" id="applyEdit">Apply</button>
            <button class="btn-danger" id="deleteSegment">Delete</button>
          </div>
        </div>
      </div>
    `;

    this.container.innerHTML = timelineHTML;

    // Get references to elements
    this.elements = {
      zoomIn: document.getElementById("zoomIn"),
      zoomOut: document.getElementById("zoomOut"),
      fitToView: document.getElementById("fitToView"),
      enableSnapping: document.getElementById("enableSnapping"),
      autoAlign: document.getElementById("autoAlign"),
      zoomDisplay: document.getElementById("zoomDisplay"),
      timelineDuration: document.getElementById("timelineDuration"),
      rulerCanvas: document.getElementById("rulerCanvas"),
      waveformCanvas: document.getElementById("waveformCanvas"),
      trackContent: document.getElementById("trackContent"),
      playhead: document.getElementById("timelinePlayhead"),
      selection: document.getElementById("timelineSelection"),
      editPanel: document.getElementById("subtitleEditPanel"),
      segmentText: document.getElementById("segmentText"),
      startTime: document.getElementById("startTime"),
      endTime: document.getElementById("endTime"),
      duration: document.getElementById("duration"),
      charCount: document.getElementById("charCount"),
      maxChars: document.getElementById("maxChars"),
    };

    // Initialize canvases
    this.initializeCanvases();
  }

  initializeCanvases() {
    // Set up ruler canvas
    const rulerCanvas = this.elements.rulerCanvas;
    const waveformCanvas = this.elements.waveformCanvas;

    // Set canvas dimensions
    this.resizeCanvases();

    // Set up resize observer
    const resizeObserver = new ResizeObserver(() => {
      this.resizeCanvases();
      this.render();
    });

    resizeObserver.observe(this.container);
  }

  resizeCanvases() {
    const containerWidth = this.container.clientWidth;
    const rulerHeight = 30;
    const waveformHeight = 80;

    // Ruler canvas
    this.elements.rulerCanvas.width = containerWidth * 2; // 2x for retina
    this.elements.rulerCanvas.height = rulerHeight * 2;
    this.elements.rulerCanvas.style.width = `${containerWidth}px`;
    this.elements.rulerCanvas.style.height = `${rulerHeight}px`;

    // Waveform canvas
    this.elements.waveformCanvas.width = containerWidth * 2;
    this.elements.waveformCanvas.height = waveformHeight * 2;
    this.elements.waveformCanvas.style.width = `${containerWidth}px`;
    this.elements.waveformCanvas.style.height = `${waveformHeight}px`;
  }

  bindEvents() {
    // Timeline controls
    this.elements.zoomIn.addEventListener("click", () => this.zoomIn());
    this.elements.zoomOut.addEventListener("click", () => this.zoomOut());
    this.elements.fitToView.addEventListener("click", () => this.fitToView());
    this.elements.enableSnapping.addEventListener("click", () =>
      this.toggleSnapping()
    );
    this.elements.autoAlign.addEventListener("click", () =>
      this.autoAlignSegments()
    );

    // Track content interactions
    this.elements.trackContent.addEventListener("mousedown", (e) =>
      this.handleMouseDown(e)
    );
    this.elements.trackContent.addEventListener("mousemove", (e) =>
      this.handleMouseMove(e)
    );
    this.elements.trackContent.addEventListener("mouseup", (e) =>
      this.handleMouseUp(e)
    );
    this.elements.trackContent.addEventListener("dblclick", (e) =>
      this.handleDoubleClick(e)
    );

    // Keyboard shortcuts
    document.addEventListener("keydown", (e) => this.handleKeyDown(e));

    // Edit panel events
    this.elements.segmentText.addEventListener("input", () =>
      this.updateCharCount()
    );
    this.elements.startTime.addEventListener("input", () =>
      this.updateDuration()
    );
    this.elements.endTime.addEventListener("input", () =>
      this.updateDuration()
    );

    document
      .getElementById("applyEdit")
      .addEventListener("click", () => this.applySegmentEdit());
    document
      .getElementById("cancelEdit")
      .addEventListener("click", () => this.closeEditPanel());
    document
      .getElementById("deleteSegment")
      .addEventListener("click", () => this.deleteSelectedSegment());
    document
      .getElementById("closeEditPanel")
      .addEventListener("click", () => this.closeEditPanel());
  }

  loadSegments(segments) {
    this.segments = segments || [];
    this.selectedSegments = [];
    this.render();

    // Update timeline duration
    const maxTime = Math.max(...this.segments.map((s) => s.end_time), 0);
    this.elements.timelineDuration.textContent = this.formatTime(maxTime);

    console.log(`📊 Loaded ${this.segments.length} subtitle segments`);
  }

  loadWaveform(waveformData) {
    this.waveformData = waveformData;
    this.renderWaveform();
    console.log("🌊 Waveform data loaded");
  }

  render() {
    this.renderRuler();
    this.renderWaveform();
    this.renderSegments();
    this.renderPlayhead();
  }

  renderRuler() {
    const canvas = this.elements.rulerCanvas;
    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Set up drawing context
    ctx.scale(2, 2); // For retina displays
    const drawWidth = width / 2;
    const drawHeight = height / 2;

    // Calculate time range
    const timeRange = drawWidth / (this.pixelsPerSecond * this.zoomLevel);
    const startTime =
      this.scrollPosition / (this.pixelsPerSecond * this.zoomLevel);

    // Draw ruler background
    ctx.fillStyle = "#2a2a2a";
    ctx.fillRect(0, 0, drawWidth, drawHeight);

    // Draw time marks
    ctx.fillStyle = "#ffffff";
    ctx.font = "11px Inter, sans-serif";
    ctx.textAlign = "center";

    const majorInterval = this.getMajorInterval(timeRange);
    const minorInterval = majorInterval / 5;

    for (
      let time = Math.floor(startTime / minorInterval) * minorInterval;
      time <= startTime + timeRange;
      time += minorInterval
    ) {
      const x = (time - startTime) * this.pixelsPerSecond * this.zoomLevel;

      if (time % majorInterval === 0) {
        // Major tick
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(x, drawHeight - 12, 1, 12);
        ctx.fillText(this.formatTime(time), x, drawHeight - 15);
      } else {
        // Minor tick
        ctx.fillStyle = "#666666";
        ctx.fillRect(x, drawHeight - 6, 1, 6);
      }
    }
  }

  renderWaveform() {
    if (!this.waveformData) return;

    const canvas = this.elements.waveformCanvas;
    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Set up drawing context
    ctx.scale(2, 2);
    const drawWidth = width / 2;
    const drawHeight = height / 2;

    // Draw waveform background
    ctx.fillStyle = "#1a1a1a";
    ctx.fillRect(0, 0, drawWidth, drawHeight);

    // Draw waveform
    ctx.fillStyle = "#3b82f6";
    ctx.strokeStyle = "#60a5fa";
    ctx.lineWidth = 1;

    const timeRange = drawWidth / (this.pixelsPerSecond * this.zoomLevel);
    const startTime =
      this.scrollPosition / (this.pixelsPerSecond * this.zoomLevel);

    // Sample waveform data
    const samplesPerPixel = Math.max(
      1,
      Math.floor(this.waveformData.length / drawWidth)
    );

    ctx.beginPath();
    for (let x = 0; x < drawWidth; x++) {
      const time = startTime + (x / drawWidth) * timeRange;
      const sampleIndex = Math.floor(
        (time * this.waveformData.length) / timeRange
      );

      if (sampleIndex >= 0 && sampleIndex < this.waveformData.length) {
        const amplitude =
          Math.abs(this.waveformData[sampleIndex]) * drawHeight * 0.4;
        const y = drawHeight / 2;

        ctx.moveTo(x, y - amplitude);
        ctx.lineTo(x, y + amplitude);
      }
    }
    ctx.stroke();
  }

  renderSegments() {
    const container = this.elements.trackContent;
    container.innerHTML = "";

    const timeRange =
      container.clientWidth / (this.pixelsPerSecond * this.zoomLevel);
    const startTime =
      this.scrollPosition / (this.pixelsPerSecond * this.zoomLevel);

    this.segments.forEach((segment, index) => {
      // Check if segment is visible
      if (
        segment.end_time < startTime ||
        segment.start_time > startTime + timeRange
      ) {
        return;
      }

      const segmentElement = this.createSegmentElement(segment, index);
      container.appendChild(segmentElement);
    });
  }

  createSegmentElement(segment, index) {
    const element = document.createElement("div");
    element.className = "subtitle-segment";
    element.dataset.segmentId = segment.id;
    element.dataset.segmentIndex = index;

    // Calculate position and size
    const startTime =
      this.scrollPosition / (this.pixelsPerSecond * this.zoomLevel);
    const left =
      (segment.start_time - startTime) * this.pixelsPerSecond * this.zoomLevel;
    const width =
      (segment.end_time - segment.start_time) *
      this.pixelsPerSecond *
      this.zoomLevel;

    element.style.left = `${left}px`;
    element.style.width = `${Math.max(width, 20)}px`; // Minimum width

    // Add content
    const content = document.createElement("div");
    content.className = "segment-content";

    const text = document.createElement("div");
    text.className = "segment-text";
    text.textContent = segment.text.replace("\n", " ");
    content.appendChild(text);

    const timing = document.createElement("div");
    timing.className = "segment-timing";
    timing.textContent = `${this.formatTime(
      segment.start_time
    )} - ${this.formatTime(segment.end_time)}`;
    content.appendChild(timing);

    element.appendChild(content);

    // Add resize handles
    const leftHandle = document.createElement("div");
    leftHandle.className = "segment-handle segment-handle-left";
    element.appendChild(leftHandle);

    const rightHandle = document.createElement("div");
    rightHandle.className = "segment-handle segment-handle-right";
    element.appendChild(rightHandle);

    // Add selection state
    if (this.selectedSegments.includes(index)) {
      element.classList.add("selected");
    }

    return element;
  }

  handleMouseDown(e) {
    const segmentElement = e.target.closest(".subtitle-segment");

    if (segmentElement) {
      const segmentIndex = parseInt(segmentElement.dataset.segmentIndex);
      const isHandle = e.target.classList.contains("segment-handle");

      if (isHandle) {
        // Handle resize
        this.startResize(
          segmentIndex,
          e.target.classList.contains("segment-handle-left"),
          e
        );
      } else {
        // Handle move or selection
        if (!e.ctrlKey && !e.shiftKey) {
          this.selectedSegments = [segmentIndex];
        } else if (e.ctrlKey) {
          this.toggleSelection(segmentIndex);
        } else if (e.shiftKey) {
          this.extendSelection(segmentIndex);
        }

        this.startMove(e);
      }

      this.render();
      e.preventDefault();
    }
  }

  handleDoubleClick(e) {
    const segmentElement = e.target.closest(".subtitle-segment");

    if (segmentElement) {
      const segmentIndex = parseInt(segmentElement.dataset.segmentIndex);
      this.openEditPanel(segmentIndex);
    }
  }

  handleKeyDown(e) {
    // Handle keyboard shortcuts for timeline
    if (e.key === "Delete" || e.key === "Backspace") {
      if (this.selectedSegments.length > 0) {
        this.deleteSelectedSegments();
        e.preventDefault();
      }
    } else if (e.key === "Escape") {
      // Clear selection or close edit panel
      if (this.elements.editPanel.style.display === "block") {
        this.closeEditPanel();
      } else {
        this.clearSelection();
      }
      e.preventDefault();
    } else if (e.key === "Enter") {
      // Apply changes in edit panel
      if (this.elements.editPanel.style.display === "block") {
        this.saveEditedSegment();
        e.preventDefault();
      }
    }
  }

  deleteSelectedSegments() {
    // Sort indices in descending order to avoid index shifting issues
    const indices = [...this.selectedSegments].sort((a, b) => b - a);
    indices.forEach((index) => {
      this.segments.splice(index, 1);
    });
    this.selectedSegments = [];
    this.render();
    this.dispatchEvent(
      new CustomEvent("segmentsChanged", { detail: this.segments })
    );
  }

  clearSelection() {
    this.selectedSegments = [];
    this.render();
  }

  closeEditPanel() {
    this.elements.editPanel.style.display = "none";
    this.editingSegmentIndex = -1;
  }

  saveEditedSegment() {
    if (
      this.editingSegmentIndex === -1 ||
      !this.segments[this.editingSegmentIndex]
    )
      return;

    const segment = this.segments[this.editingSegmentIndex];

    // Update segment data from edit panel
    segment.text = this.elements.segmentText.value;
    segment.start_time = parseFloat(this.elements.startTime.value);
    segment.end_time = parseFloat(this.elements.endTime.value);

    // Emit update event
    this.dispatchEvent(
      new CustomEvent("segmentUpdated", {
        detail: { segment, index: this.editingSegmentIndex },
      })
    );

    this.render();
    this.closeEditPanel();
  }

  openEditPanel(segmentIndex) {
    const segment = this.segments[segmentIndex];
    if (!segment) return;

    this.editingSegmentIndex = segmentIndex;

    // Populate edit panel
    this.elements.segmentText.value = segment.text;
    this.elements.startTime.value = segment.start_time.toFixed(1);
    this.elements.endTime.value = segment.end_time.toFixed(1);

    this.updateCharCount();
    this.updateDuration();

    // Show panel
    this.elements.editPanel.style.display = "block";
    this.elements.segmentText.focus();
  }

  closeEditPanel() {
    this.elements.editPanel.style.display = "none";
    this.editingSegmentIndex = null;
  }

  applySegmentEdit() {
    if (this.editingSegmentIndex === null) return;

    const segment = this.segments[this.editingSegmentIndex];

    // Update segment data
    segment.text = this.elements.segmentText.value;
    segment.start_time = parseFloat(this.elements.startTime.value);
    segment.end_time = parseFloat(this.elements.endTime.value);

    // Emit update event
    this.dispatchEvent(
      new CustomEvent("segmentUpdated", {
        detail: { segment, index: this.editingSegmentIndex },
      })
    );

    this.render();
    this.closeEditPanel();
  }

  deleteSelectedSegment() {
    if (this.editingSegmentIndex === null) return;

    this.segments.splice(this.editingSegmentIndex, 1);

    this.dispatchEvent(
      new CustomEvent("segmentDeleted", {
        detail: { index: this.editingSegmentIndex },
      })
    );

    this.render();
    this.closeEditPanel();
  }

  updateCharCount() {
    const text = this.elements.segmentText.value;
    const charCount = text.length;
    const maxChars = parseInt(this.elements.maxChars.textContent);

    this.elements.charCount.textContent = charCount;

    if (charCount > maxChars) {
      this.elements.charCount.style.color = "#ef4444";
    } else {
      this.elements.charCount.style.color = "#6b7280";
    }
  }

  updateDuration() {
    const startTime = parseFloat(this.elements.startTime.value) || 0;
    const endTime = parseFloat(this.elements.endTime.value) || 0;
    const duration = Math.max(0, endTime - startTime);

    this.elements.duration.value = duration.toFixed(1);
  }

  zoomIn() {
    this.zoomLevel = Math.min(this.zoomLevel * 1.5, 10);
    this.elements.zoomDisplay.textContent = `${Math.round(
      this.zoomLevel * 100
    )}%`;
    this.render();
  }

  zoomOut() {
    this.zoomLevel = Math.max(this.zoomLevel / 1.5, 0.1);
    this.elements.zoomDisplay.textContent = `${Math.round(
      this.zoomLevel * 100
    )}%`;
    this.render();
  }

  fitToView() {
    if (this.segments.length === 0) return;

    const maxTime = Math.max(...this.segments.map((s) => s.end_time));
    const containerWidth = this.elements.trackContent.clientWidth;

    this.zoomLevel = containerWidth / (maxTime * this.pixelsPerSecond);
    this.scrollPosition = 0;

    this.elements.zoomDisplay.textContent = `${Math.round(
      this.zoomLevel * 100
    )}%`;
    this.render();
  }

  toggleSnapping() {
    this.snappingEnabled = !this.snappingEnabled;
    this.elements.enableSnapping.classList.toggle(
      "active",
      this.snappingEnabled
    );
  }

  autoAlignSegments() {
    // Intelligent auto-alignment based on audio peaks and pauses
    console.log("🎯 Auto-aligning subtitle segments");

    this.dispatchEvent(new CustomEvent("autoAlignRequested"));
  }

  getMajorInterval(timeRange) {
    if (timeRange < 10) return 1;
    if (timeRange < 60) return 5;
    if (timeRange < 300) return 30;
    return 60;
  }

  formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, "0")}:${remainingSeconds
      .toFixed(1)
      .padStart(4, "0")}`;
  }

  // Export methods for integration
  getSegments() {
    return this.segments;
  }

  timeToPixels(time) {
    return (
      (time - this.scrollPosition / (this.pixelsPerSecond * this.zoomLevel)) *
      this.pixelsPerSecond *
      this.zoomLevel
    );
  }

  renderPlayhead() {
    // Create or update playhead element
    let playhead = this.container.querySelector(".timeline-playhead");
    if (!playhead) {
      playhead = document.createElement("div");
      playhead.className = "timeline-playhead";
      playhead.style.cssText = `
        position: absolute;
        top: 0;
        bottom: 0;
        width: 2px;
        background-color: #ff4444;
        pointer-events: none;
        z-index: 100;
        display: none;
      `;
      this.container.appendChild(playhead);
    }

    // Position playhead based on current time
    if (this.currentTime !== undefined && this.currentTime >= 0) {
      const position = this.timeToPixels(this.currentTime);
      playhead.style.left = `${position}px`;
      playhead.style.display = "block";
    } else {
      playhead.style.display = "none";
    }
  }

  updateSegment(index, updatedSegment) {
    if (index >= 0 && index < this.segments.length) {
      this.segments[index] = updatedSegment;
      this.render();
    }
  }

  addSegment(segment) {
    this.segments.push(segment);
    this.segments.sort((a, b) => a.start_time - b.start_time);
    this.render();
  }
}

// Export for use in video editor
window.EnhancedSubtitleTimeline = EnhancedSubtitleTimeline;
