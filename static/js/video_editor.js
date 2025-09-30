// video_editor.js - Video Editor Module for Face Sequencer Pro
console.log("🎬 Loading VideoEditorModule class...");

class VideoEditorModule extends EventTarget {
  constructor(app) {
    console.log("🎬 VideoEditorModule constructor called");
    super();
    this.app = app;
    this.videoFile = null;
    this.subtitles = [];
    this.currentPreset = null;
    this.isVideoLoaded = false;
    this.isDragging = false;
    // History / undo-redo
    this._undoStack = [];
    this._redoStack = [];
    this._maxHistory = 60;
    // Snapping configuration
    this._snapThresholdMs = 120;
    this._frameRate = 30;
    this._frameSnapStep = 10; // default: consider every 10 frames for visual markers
    this._snappingEnabled = true;
    this._showFrameGrid = true; // will be overridden by persisted value if present
    this._strictSnapMode = false;
    this._snapTooltip = null;
    // Restore persisted snap step if available
    try {
      const savedStep = localStorage.getItem("frameSnapStep");
      if (savedStep) {
        const parsed = parseInt(savedStep, 10);
        if (!isNaN(parsed) && parsed > 0) this._frameSnapStep = parsed;
      }
    } catch (e) {
      /* ignore */
    }
    // External audio support placeholder
    this.externalAudioBlob = null;
    // Bind shortcuts later after DOM ready
    setTimeout(() => this.attachUndoRedoShortcuts(), 0);

    // Initialize UI elements
    this.initializeElements();
    this.bindEvents();
    this.setupFileDrop();

    console.log("🎬 Video Editor Module initialized");
  }

  initializeElements() {
    console.log("🔍 VideoEditor - Initializing elements...");

    // Mode switching
    this.faceAnimationMode = document.getElementById("faceAnimationMode");
    this.videoEditorMode = document.getElementById("videoEditorMode");
    this.faceAnimationInterface = document.getElementById(
      "faceAnimationInterface"
    );
    this.videoEditorInterface = document.getElementById("videoEditorInterface");

    console.log("Elements found:");
    console.log("- faceAnimationMode:", this.faceAnimationMode);
    console.log("- videoEditorMode:", this.videoEditorMode);
    console.log("- faceAnimationInterface:", this.faceAnimationInterface);
    console.log("- videoEditorInterface:", this.videoEditorInterface);

    // Video elements
    this.loadVideoBtn = document.getElementById("loadVideoBtn");
    this.videoPreview = document.getElementById("videoPreview");
    this.videoPlaceholder = document.getElementById("videoPlaceholder");
    this.playPauseBtn = document.getElementById("playPauseBtn");
    this.stopVideoBtn = document.getElementById("stopVideoBtn");

    // Subtitle elements
    this.generateSubtitlesBtn = document.getElementById("generateSubtitlesBtn");
    this.clearSubtitlesBtn = document.getElementById("clearSubtitlesBtn");
    this.frameSnapStepSelect = document.getElementById("frameSnapStep");
    this.videoTranscript = document.getElementById("videoTranscript");
    this.subtitleTimeline = document.getElementById("subtitleTimeline");
    this.segmentsList = document.getElementById("segmentsList");
    this.previewSubtitles = document.getElementById("previewSubtitles");
    this.exportVideoWithSubtitles = document.getElementById(
      "exportVideoWithSubtitles"
    );
    this.externalAudioInput = document.getElementById("externalAudioInput");

    // Initialize enhanced timeline
    this.enhancedTimeline = null;
    this.initializeEnhancedTimeline();

    // Style controls
    this.presetButtons = document.querySelectorAll(".preset-btn");
    this.fontFamily = document.getElementById("fontFamily");
    this.fontSize = document.getElementById("fontSize");
    this.fontWeight = document.getElementById("fontWeight");
    this.textColor = document.getElementById("textColor");
    this.backgroundColor = document.getElementById("backgroundColor");
    this.backgroundOpacity = document.getElementById("backgroundOpacity");
    this.outlineColor = document.getElementById("outlineColor");
    this.outlineWidth = document.getElementById("outlineWidth");
    this.verticalPosition = document.getElementById("verticalPosition");
    this.horizontalAlign = document.getElementById("horizontalAlign");
    this.maxWidth = document.getElementById("maxWidth");

    // Create hidden file input for video upload
    this.videoInput = document.createElement("input");
    this.videoInput.type = "file";
    this.videoInput.accept = "video/*";
    this.videoInput.style.display = "none";
    document.body.appendChild(this.videoInput);
  }

  bindEvents() {
    console.log("🔧 VideoEditor - Binding events...");
    console.log("Video Editor Mode button:", !!this.videoEditorMode);
    console.log("Face Animation Mode button:", !!this.faceAnimationMode);

    // Mode switching
    if (this.faceAnimationMode) {
      this.faceAnimationMode.addEventListener("click", () => {
        console.log("🎭 Face Animation Mode button clicked");
        this.switchToFaceAnimationMode();
      });
    } else {
      console.warn("⚠️ faceAnimationMode button not found");
    }

    if (this.videoEditorMode) {
      this.videoEditorMode.addEventListener("click", (e) => {
        e.preventDefault();
        console.log("🎬 Video Editor Mode button clicked!");
        this.switchToVideoMode();

        // Enforce theme and visibility after a small delay
        setTimeout(() => {
          document.body.classList.add("video-editor-active");
          if (this.videoEditorInterface) {
            this.videoEditorInterface.style.display = "flex";
            this.videoEditorInterface.classList.add("active");
          }
          if (this.faceAnimationInterface) {
            this.faceAnimationInterface.style.display = "none";
          }
        }, 10);
      });
    } else {
      console.warn("⚠️ videoEditorMode button not found");
    } // Video controls
    this.loadVideoBtn?.addEventListener("click", () => this.videoInput.click());
    this.videoInput?.addEventListener("change", (e) =>
      this.handleVideoUpload(e)
    );
    this.playPauseBtn?.addEventListener("click", () => this.togglePlayPause());
    this.stopVideoBtn?.addEventListener("click", () => this.stopVideo());
    this.externalAudioInput?.addEventListener("change", (e) => {
      const file = e.target.files?.[0];
      if (file) {
        this.externalAudioBlob = file;
        this.app?.showStatus?.("External audio attached");
        this.updateGenerateButton();
      }
    });

    // Subtitle controls
    this.generateSubtitlesBtn?.addEventListener("click", () =>
      this.generateSubtitles()
    );
    this.clearSubtitlesBtn?.addEventListener("click", () =>
      this.clearSubtitles()
    );
    this.frameSnapStepSelect?.addEventListener("change", () => {
      const v = parseInt(this.frameSnapStepSelect.value, 10);
      if (!isNaN(v) && v > 0) {
        this._frameSnapStep = v;
        try {
          localStorage.setItem("frameSnapStep", String(v));
        } catch (e) {}
        if (this._snappingEnabled)
          this.app?.showStatus?.(`Snap step: every ${v} frame(s)`);
      }
    });
    // Snapping preference panel bindings
    const toggleSnapping = document.getElementById("toggleSnapping");
    const toggleFrameGrid = document.getElementById("toggleFrameGrid");
    const toggleStrictSnap = document.getElementById("toggleStrictSnap");
    const snapThresholdRange = document.getElementById("snapThresholdRange");
    if (toggleSnapping) {
      toggleSnapping.checked = this._snappingEnabled;
      toggleSnapping.addEventListener("change", () => {
        this._snappingEnabled = toggleSnapping.checked;
        this.app?.showStatus?.(
          this._snappingEnabled ? "Snapping ON" : "Snapping OFF"
        );
      });
    }
    if (toggleFrameGrid) {
      try {
        const saved = localStorage.getItem("showFrameGrid");
        if (saved) this._showFrameGrid = saved === "1";
      } catch (e) {}
      toggleFrameGrid.checked = this._showFrameGrid;
      toggleFrameGrid.addEventListener("change", () => {
        this._showFrameGrid = toggleFrameGrid.checked;
        try {
          localStorage.setItem(
            "showFrameGrid",
            this._showFrameGrid ? "1" : "0"
          );
        } catch (e) {}
        this.app?.showStatus?.(
          this._showFrameGrid ? "Frame grid ON" : "Frame grid OFF"
        );
        if (this._snapLayer) this._clearSnapMarkers();
      });
    }
    if (toggleStrictSnap) {
      try {
        const saved = localStorage.getItem("strictSnapMode");
        if (saved) this._strictSnapMode = saved === "1";
      } catch (e) {}
      toggleStrictSnap.checked = this._strictSnapMode;
      toggleStrictSnap.addEventListener("change", () => {
        this._strictSnapMode = toggleStrictSnap.checked;
        try {
          localStorage.setItem(
            "strictSnapMode",
            this._strictSnapMode ? "1" : "0"
          );
        } catch (e) {}
        this.app?.showStatus?.(
          this._strictSnapMode ? "Strict snap ON" : "Strict snap OFF"
        );
      });
    }
    if (snapThresholdRange) {
      try {
        const saved = localStorage.getItem("snapThresholdMs");
        if (saved) {
          const p = parseInt(saved, 10);
          if (!isNaN(p)) this._snapThresholdMs = p;
        }
      } catch (e) {}
      snapThresholdRange.value = this._snapThresholdMs;
      snapThresholdRange.addEventListener("input", () => {
        const v = parseInt(snapThresholdRange.value, 10);
        if (!isNaN(v)) {
          this._snapThresholdMs = v;
          try {
            localStorage.setItem("snapThresholdMs", String(v));
          } catch (e) {}
        }
      });
    }
    this.previewSubtitles?.addEventListener("click", () =>
      this.previewWithSubtitles()
    );
    this.exportVideoWithSubtitles?.addEventListener("click", () =>
      this.exportVideo()
    );

    // Transcript input
    this.videoTranscript?.addEventListener("input", () =>
      this.updateGenerateButton()
    );

    // Style controls
    this.presetButtons?.forEach((btn) => {
      btn.addEventListener("click", () => this.applyPreset(btn.dataset.preset));
    });

    // Range inputs with value display
    this.bindRangeInputs();

    // Video events
    if (this.videoPreview) {
      this.videoPreview.addEventListener("loadedmetadata", () =>
        this.onVideoLoaded()
      );
      this.videoPreview.addEventListener("timeupdate", () =>
        this.updateVideoTime()
      );
      this.videoPreview.addEventListener("play", () =>
        this.updatePlayButton(true)
      );
      this.videoPreview.addEventListener("pause", () =>
        this.updatePlayButton(false)
      );
    }
  }

  bindRangeInputs() {
    const rangeInputs = [
      { input: this.fontSize, display: "px" },
      { input: this.backgroundOpacity, display: "%" },
      { input: this.outlineWidth, display: "px" },
      { input: this.maxWidth, display: "%" },
    ];

    rangeInputs.forEach(({ input, display }) => {
      if (input) {
        const valueDisplay =
          input.parentElement.querySelector(".value-display");
        if (valueDisplay) {
          input.addEventListener("input", () => {
            valueDisplay.textContent = input.value + display;
            this.updateSubtitleStyle();
          });
        }
      }
    });

    // Color and select inputs
    [
      this.fontFamily,
      this.fontWeight,
      this.textColor,
      this.backgroundColor,
      this.outlineColor,
      this.verticalPosition,
      this.horizontalAlign,
    ].forEach((input) => {
      if (input) {
        input.addEventListener("change", () => this.updateSubtitleStyle());
      }
    });
  }

  setupFileDrop() {
    const dropZone = this.videoEditorInterface;
    if (!dropZone) return;

    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(eventName, this.preventDefaults, false);
    });

    ["dragenter", "dragover"].forEach((eventName) => {
      dropZone.addEventListener(
        eventName,
        () => this.highlight(dropZone),
        false
      );
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(
        eventName,
        () => this.unhighlight(dropZone),
        false
      );
    });

    dropZone.addEventListener("drop", (e) => this.handleDrop(e), false);
  }

  preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  highlight(element) {
    element.classList.add("drag-over");
  }

  unhighlight(element) {
    element.classList.remove("drag-over");
  }

  handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;

    if (files.length > 0 && files[0].type.startsWith("video/")) {
      this.loadVideo(files[0]);
    } else {
      this.app.showError("Please drop a valid video file");
    }
  }

  // Mode Switching
  switchToVideoMode() {
    console.log("🎬 switchToVideoMode called");
    const alreadyActive = this.videoEditorMode?.classList.contains("active");
    // Even if already active, we still re-apply body class / layout to ensure theme

    console.log("🎬 Switching to Video Editor mode");

    // Update mode buttons
    if (this.faceAnimationMode)
      this.faceAnimationMode.classList.remove("active");
    if (this.videoEditorMode) this.videoEditorMode.classList.add("active");

    // Switch interfaces with animation
    if (this.faceAnimationInterface && this.videoEditorInterface) {
      console.log("🎬 Updating interface visibility");
      this.faceAnimationInterface.classList.remove("active");
      this.videoEditorInterface.classList.add("active");
      this.faceAnimationInterface.style.display = "none";
      this.videoEditorInterface.style.display = "flex"; // fallback until all code uses class
    } else {
      console.warn("Missing interface elements for mode switch");
    }
    document.body.classList.add("video-editor-active");

    // Save mode preference
    localStorage.setItem("faceSequencerMode", "video-editor");

    this.dispatchEvent(
      new CustomEvent("modeChanged", {
        detail: { mode: "video-editor" },
      })
    );

    // Garantir reinicialização da timeline se não existir (caso antes estivesse em modal oculto)
    if (!this.enhancedTimeline) {
      console.log(
        "♻️ Re-initializing enhanced subtitle timeline after DOM relocation..."
      );
      try {
        this.initializeEnhancedTimeline();
      } catch (e) {
        console.warn("Failed to reinitialize enhanced timeline:", e);
      }
    }
  }

  switchToFaceAnimationMode() {
    if (this.faceAnimationMode?.classList.contains("active")) return;

    console.log("🎭 Switching to Face Animation mode");

    // Update mode buttons
    this.videoEditorMode?.classList.remove("active");
    this.faceAnimationMode?.classList.add("active");

    // Switch interfaces
    if (this.faceAnimationInterface && this.videoEditorInterface) {
      this.videoEditorInterface.classList.remove("active");
      this.faceAnimationInterface.classList.add("active");
      this.videoEditorInterface.style.display = "none";
      this.faceAnimationInterface.style.display = "block"; // fallback inline
    }
    document.body.classList.remove("video-editor-active");

    // Save mode preference
    localStorage.setItem("faceSequencerMode", "face-animation");

    this.dispatchEvent(
      new CustomEvent("modeChanged", {
        detail: { mode: "face-animation" },
      })
    );
  }

  restoreModeFromStorage() {
    const savedMode = localStorage.getItem("faceSequencerMode");
    if (savedMode === "video-editor") {
      this.switchToVideoMode();
      document.body.classList.add("video-editor-active");
    }
  }

  // Video Management
  handleVideoUpload(event) {
    const file = event.target.files[0];
    if (file && file.type.startsWith("video/")) {
      this.loadVideo(file);
    } else {
      this.app.showError("Please select a valid video file");
    }
  }

  loadVideo(file) {
    console.log("🎬 Loading video file:", file.name);

    this.videoFile = file;

    // Create object URL for video preview
    const videoURL = URL.createObjectURL(file);

    if (this.videoPreview) {
      this.videoPreview.src = videoURL;
      this.videoPreview.style.display = "block";
    }

    if (this.videoPlaceholder) {
      this.videoPlaceholder.style.display = "none";
    }

    // Show success message
    this.app.showStatus(`Video loaded: ${file.name}`);

    // Update UI state
    this.updateUIState();
  }

  onVideoLoaded() {
    console.log("📹 Video metadata loaded");
    this.isVideoLoaded = true;

    // Enable controls
    if (this.playPauseBtn) this.playPauseBtn.disabled = false;
    if (this.stopVideoBtn) this.stopVideoBtn.disabled = false;

    // Update generate button state
    this.updateGenerateButton();

    this.updateUIState();
  }

  togglePlayPause() {
    if (!this.videoPreview || !this.isVideoLoaded) return;

    if (this.videoPreview.paused) {
      this.videoPreview.play();
    } else {
      this.videoPreview.pause();
    }
  }

  stopVideo() {
    if (!this.videoPreview) return;

    this.videoPreview.pause();
    this.videoPreview.currentTime = 0;
  }

  updatePlayButton(isPlaying) {
    if (this.playPauseBtn) {
      const icon = this.playPauseBtn.querySelector("i");
      if (icon) {
        icon.className = isPlaying ? "fas fa-pause" : "fas fa-play";
      }
    }
  }

  updateVideoTime() {
    if (!this.videoPreview) return;

    const current = this.formatTime(this.videoPreview.currentTime);
    const duration = this.formatTime(this.videoPreview.duration || 0);

    const timeDisplay = document.querySelector(".video-time");
    if (timeDisplay) {
      timeDisplay.textContent = `${current} / ${duration}`;
    }
  }

  formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, "0")}:${secs
      .toString()
      .padStart(2, "0")}`;
  }

  // Subtitle Generation
  updateGenerateButton() {
    const hasVideo = this.isVideoLoaded;
    const hasText = this.videoTranscript?.value.trim().length > 0;

    if (this.generateSubtitlesBtn) {
      this.generateSubtitlesBtn.disabled = !(hasVideo && hasText);
    }
  }

  async generateSubtitles() {
    if (!this.videoFile || !this.videoTranscript?.value.trim()) {
      this.app.showError("Please upload a video and enter transcript text");
      return;
    }

    const text = this.videoTranscript.value.trim();

    try {
      this._cancelRequested = false;
      this._enterGeneratingState();
      console.log("🎬 Generating enhanced subtitles for video...");
      this.app.showStatus(
        "Generating intelligent subtitles from video audio..."
      );

      // Extract audio from video and use existing alignment system
      let audioBlob = null;
      if (this.externalAudioBlob) {
        this._updateProgressDetail("Using external audio track...");
        audioBlob = this.externalAudioBlob;
      } else {
        this._updateProgressDetail("Extracting audio...");
        audioBlob = await this.extractAudioFromVideo(this.videoFile);
      }
      if (this._cancelRequested) throw new Error("Generation cancelled");

      // Use the existing audio alignment system
      this._updateProgressDetail("Uploading & aligning audio...");
      const alignmentResult = await this.alignAudioWithText(
        audioBlob,
        text,
        (phase) => {
          if (!this._cancelRequested) this._updateProgressDetail(phase);
        }
      );
      if (this._cancelRequested) throw new Error("Generation cancelled");

      if (alignmentResult && alignmentResult.alignment) {
        // Try enhanced subtitle generation first
        this._updateProgressDetail("Enhancing segments...");
        const enhancedResult = await this.generateEnhancedSubtitles(
          alignmentResult.alignment,
          (phase) => {
            if (!this._cancelRequested) this._updateProgressDetail(phase);
          }
        );
        if (this._cancelRequested) throw new Error("Generation cancelled");

        if (enhancedResult && enhancedResult.enhanced) {
          this.subtitles = enhancedResult.segments;
          this.subtitleMetrics = enhancedResult.metrics;
          this.displaySubtitleMetrics(enhancedResult.metrics);
          console.log("✨ Enhanced subtitle generation successful");
        } else {
          // Fallback to standard generation
          this.subtitles = this.convertAlignmentToSubtitles(
            alignmentResult.alignment
          );
          console.log("📝 Using standard subtitle generation");
        }

        this.renderSubtitleTimeline();
        this.renderSubtitleSegments();
        this.updateUIState();

        this.app.showStatus(
          `Generated ${this.subtitles.length} subtitle segments`
        );
        this.previewWithSubtitles();
      } else {
        throw new Error("Failed to generate subtitle alignment");
      }
    } catch (error) {
      console.error("❌ Subtitle generation failed:", error);
      if (error.message === "Generation cancelled") {
        this.app.showStatus("Generation cancelled");
      } else if (/MediaRecorder/i.test(error.message)) {
        this.app.showError(
          "Audio extraction not supported in this browser. Provide an external audio track or try a different browser."
        );
      } else {
        this.app.showError(`Subtitle generation failed: ${error.message}`);
      }
    } finally {
      this._exitGeneratingState();
    }
  }

  _enterGeneratingState() {
    if (this._isGenerating) return;
    this._isGenerating = true;
    if (this.generateSubtitlesBtn) {
      this._originalGenerateText = this.generateSubtitlesBtn.innerHTML;
      this.generateSubtitlesBtn.disabled = true;
      this.generateSubtitlesBtn.classList.add("loading");
      this.generateSubtitlesBtn.innerHTML = `<span class="spinner" style="display:inline-block;width:14px;height:14px;border:2px solid currentColor;border-right-color:transparent;border-radius:50%;margin-right:6px;animation:spin .7s linear infinite;vertical-align:middle;"></span>Generating...`;
    }
    this._createProgressOverlay("Analyzing audio & aligning text...");
  }

  _exitGeneratingState() {
    this._isGenerating = false;
    if (this.generateSubtitlesBtn) {
      this.generateSubtitlesBtn.disabled = false;
      this.generateSubtitlesBtn.classList.remove("loading");
      if (this._originalGenerateText) {
        this.generateSubtitlesBtn.innerHTML = this._originalGenerateText;
      } else {
        this.generateSubtitlesBtn.textContent = "Generate";
      }
    }
    this._removeProgressOverlay();
  }

  _createProgressOverlay(message) {
    if (document.getElementById("videoGenProgressOverlay")) return;
    const container = this.videoPreview?.parentElement || document.body;
    const overlay = document.createElement("div");
    overlay.id = "videoGenProgressOverlay";
    overlay.style.cssText = `position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;background:rgba(0,0,0,0.55);backdrop-filter:blur(2px);color:#fff;font-family:system-ui,sans-serif;z-index:50;gap:12px;text-align:center;padding:16px;`;
    overlay.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;gap:10px;max-width:260px;">
        <div class="spinner-lg" style="width:42px;height:42px;border:4px solid rgba(255,255,255,0.85);border-right-color:transparent;border-radius:50%;animation:spin .9s linear infinite;"></div>
        <div style="font-size:14px;line-height:1.4;">${message}</div>
        <div id="genProgressDetail" style="font-size:11px;opacity:.85;">Starting...</div>
        <button id="cancelGenerationBtn" style="margin-top:4px;background:#dc2626;border:none;color:#fff;padding:6px 12px;border-radius:4px;font-size:12px;cursor:pointer;">Cancel</button>
      </div>`;
    container.style.position = "relative";
    container.appendChild(overlay);
    overlay
      .querySelector("#cancelGenerationBtn")
      .addEventListener("click", () => {
        this._cancelRequested = true;
        this._updateProgressDetail("Cancelling (may take a moment)...");
      });
  }

  _updateProgressDetail(text) {
    const el = document.getElementById("genProgressDetail");
    if (el) el.textContent = text;
  }

  _removeProgressOverlay() {
    const overlay = document.getElementById("videoGenProgressOverlay");
    if (overlay) overlay.remove();
    this._cancelRequested = false;
  }

  async generateEnhancedSubtitles(alignmentResult) {
    try {
      const selectedPreset = this.getSelectedPreset();

      const response = await fetch("/api/subtitles/generate-enhanced", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          alignment: alignmentResult,
          platform: selectedPreset,
          custom_options: this.getCustomOptions(),
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        return result.data;
      } else {
        throw new Error(
          result.message || "Enhanced subtitle generation failed"
        );
      }
    } catch (error) {
      console.warn(
        "Enhanced subtitle generation failed, falling back to standard:",
        error
      );
      return null;
    }
  }

  getSelectedPreset() {
    const activePresetBtn = document.querySelector(".preset-btn.active");
    return activePresetBtn?.dataset.preset || "custom";
  }

  getCustomOptions() {
    return {
      max_chars_per_line: 50,
      max_lines: 2,
      font_size_ratio: 0.05,
    };
  }

  displaySubtitleMetrics(metrics) {
    if (!metrics) return;

    const metricsPanel = document.querySelector(".subtitle-metrics");
    if (metricsPanel) {
      // Update individual metric values
      const readingSpeedEl = document.getElementById("readingSpeedMetric");
      const readabilityEl = document.getElementById("readabilityMetric");
      const segmentCountEl = document.getElementById("segmentCountMetric");
      const platformEl = document.getElementById("platformMetric");

      if (readingSpeedEl)
        readingSpeedEl.textContent = `${
          metrics.average_reading_speed_wps?.toFixed(1) || 0
        } words/sec`;
      if (readabilityEl)
        readabilityEl.textContent = `${Math.round(
          metrics.readability_score || 0
        )}%`;
      if (segmentCountEl)
        segmentCountEl.textContent = metrics.total_segments || 0;
      if (platformEl)
        platformEl.textContent = metrics.platform_preset || "custom";

      metricsPanel.style.display = "block";
    }
  }

  initializeEnhancedTimeline() {
    if (
      typeof EnhancedSubtitleTimeline !== "undefined" &&
      this.subtitleTimeline
    ) {
      if (!this.enhancedTimeline) {
        try {
          this.enhancedTimeline = new EnhancedSubtitleTimeline(
            this.subtitleTimeline,
            this
          );

          this.enhancedTimeline.addEventListener("segmentUpdated", (e) => {
            this.handleSegmentUpdate(e.detail);
          });

          this.enhancedTimeline.addEventListener("segmentDeleted", (e) => {
            this.handleSegmentDelete(e.detail);
          });

          this.enhancedTimeline.addEventListener("autoAlignRequested", () => {
            this.autoAlignSubtitles();
          });

          this.enhancedTimeline.addEventListener("optimizationRequested", () =>
            this.optimizeCurrentSubtitles()
          );

          console.log("✨ Enhanced subtitle timeline initialized");
        } catch (error) {
          console.warn("Enhanced timeline initialization failed:", error);
          this.enhancedTimeline = null;
        }
      }
      return !!this.enhancedTimeline;
    }
    return false;
  }

  handleSegmentUpdate(detail) {
    const { segment, index } = detail;
    if (this.subtitles && index >= 0 && index < this.subtitles.length) {
      this.subtitles[index] = segment;
      this.renderSubtitleSegments(); // Update other UI components
      console.log("📝 Subtitle segment updated:", segment.id);
    }
  }

  handleSegmentDelete(detail) {
    const { index } = detail;
    if (this.subtitles && index >= 0 && index < this.subtitles.length) {
      this.subtitles.splice(index, 1);
      this.renderSubtitleSegments(); // Update other UI components
      console.log("🗑️ Subtitle segment deleted");
    }
  }

  async autoAlignSubtitles() {
    try {
      console.log("🎯 Auto-aligning subtitle segments...");

      if (!this.subtitles || this.subtitles.length === 0) {
        this.app.showError("No subtitle segments to align");
        return;
      }

      // Validate current segments
      const validationResponse = await fetch("/api/subtitles/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segments: this.subtitles,
          platform: this.getSelectedPreset(),
        }),
      });

      if (validationResponse.ok) {
        const validation = await validationResponse.json();
        if (validation.success) {
          const issues = validation.data.total_issues;
          if (issues > 0) {
            this.app.showStatus(
              `Found ${issues} issues that need optimization`
            );

            // Optimize segments
            await this.optimizeCurrentSubtitles();
          } else {
            this.app.showStatus("Subtitles are already well-aligned");
          }
        }
      }
    } catch (error) {
      console.error("Auto-alignment failed:", error);
      this.app.showError("Auto-alignment failed");
    }
  }

  async optimizeCurrentSubtitles() {
    try {
      const response = await fetch("/api/subtitles/optimize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segments: this.subtitles,
          platform: this.getSelectedPreset(),
        }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          this.subtitles = result.data.optimized_segments;
          this.renderSubtitleTimeline();
          this.renderSubtitleSegments();
          this.app.showStatus("Subtitles optimized successfully");
        }
      }
    } catch (error) {
      console.error("Subtitle optimization failed:", error);
    }
  }

  async extractAudioFromVideo(videoFile) {
    // Extração de áudio com múltiplos fallbacks para evitar falha do MediaRecorder
    return new Promise((resolve, reject) => {
      try {
        // Primeiro: tentar criar um elemento <audio> diretamente se arquivo já contém áudio
        const directAudio = document.createElement("audio");
        directAudio.preload = "auto";
        directAudio.src = URL.createObjectURL(videoFile);

        directAudio.addEventListener(
          "error",
          () => {
            console.warn(
              "[VideoEditor] Direct audio element could not play file, trying video fallback"
            );
          },
          { once: true }
        );

        // Se conseguirmos metadata, podemos usar o blob diretamente
        directAudio.addEventListener(
          "loadedmetadata",
          () => {
            // Nem sempre conseguimos extrair diretamente, então partimos para fallback completo
          },
          { once: true }
        );

        // Fallback principal usando elemento <video>
        const video = document.createElement("video");
        video.preload = "auto";
        video.muted = true; // Evita autoplay restrictions
        video.src = URL.createObjectURL(videoFile);

        // Timeout de segurança
        const timeoutId = setTimeout(() => {
          console.warn(
            "[VideoEditor] Timeout loading video for audio extraction"
          );
        }, 15000);

        video.addEventListener(
          "loadedmetadata",
          async () => {
            clearTimeout(timeoutId);
            try {
              // Verificar se o navegador suporta MediaRecorder e se há trilha de áudio
              const hasAudioTrack =
                video.mozHasAudio ||
                video.webkitAudioDecodedByteCount > 0 ||
                (video.audioTracks && video.audioTracks.length);

              // Melhor abordagem: criar um MediaElementAudioSourceNode para ler a trilha
              if (window.AudioContext || window.webkitAudioContext) {
                try {
                  const AudioCtx =
                    window.AudioContext || window.webkitAudioContext;
                  const ctx = new AudioCtx();
                  const source = ctx.createMediaElementSource(video);
                  const dest = ctx.createMediaStreamDestination();
                  source.connect(dest);
                  source.connect(ctx.destination); // opcional para ouvir

                  if (
                    window.MediaRecorder &&
                    dest.stream.getAudioTracks().length
                  ) {
                    const options = this._chooseAudioMimeType();
                    const mr = new MediaRecorder(dest.stream, options);
                    const chunks = [];
                    mr.ondataavailable = (e) => {
                      if (e.data.size) chunks.push(e.data);
                    };
                    mr.onstop = () => {
                      if (chunks.length) {
                        const blob = new Blob(chunks, {
                          type: options.mimeType || "audio/webm",
                        });
                        resolve(blob);
                      } else {
                        reject(new Error("No audio data captured"));
                      }
                    };
                    mr.start();
                    video.play().catch(() => {});
                    video.addEventListener(
                      "ended",
                      () => mr.state !== "inactive" && mr.stop(),
                      { once: true }
                    );
                    return; // Sucesso – aguardando stop
                  }
                } catch (ctxErr) {
                  console.warn(
                    "[VideoEditor] Web Audio extraction failed:",
                    ctxErr
                  );
                }
              }

              // Fallback secundário: tentar MediaRecorder diretamente no elemento (Chrome não permite, mas mantemos por completude)
              if (window.MediaRecorder && video.captureStream) {
                try {
                  const stream = video.captureStream();
                  if (stream.getAudioTracks().length) {
                    const options = this._chooseAudioMimeType();
                    const mr2 = new MediaRecorder(stream, options);
                    const chunks2 = [];
                    mr2.ondataavailable = (e) => {
                      if (e.data.size) chunks2.push(e.data);
                    };
                    mr2.onstop = () => {
                      const blob = new Blob(chunks2, {
                        type: options.mimeType || "audio/webm",
                      });
                      resolve(blob);
                    };
                    mr2.start();
                    video.play().catch(() => {});
                    video.addEventListener(
                      "ended",
                      () => mr2.state !== "inactive" && mr2.stop(),
                      { once: true }
                    );
                    return;
                  }
                } catch (mrErr) {
                  console.warn(
                    "[VideoEditor] Direct captureStream() MediaRecorder failed:",
                    mrErr
                  );
                }
              }

              // Fallback final: retornar erro mais claro
              reject(
                new Error(
                  "Audio extraction not supported in this browser/environment."
                )
              );
            } catch (err) {
              reject(err);
            }
          },
          { once: true }
        );

        video.addEventListener(
          "error",
          (e) => {
            clearTimeout(timeoutId);
            reject(new Error("Failed to load video for audio extraction"));
          },
          { once: true }
        );
      } catch (outerErr) {
        reject(outerErr);
      }
    });
  }

  // Escolhe o melhor mime type suportado pelo navegador para áudio
  _chooseAudioMimeType() {
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/ogg",
    ];
    for (const c of candidates) {
      if (
        MediaRecorder &&
        MediaRecorder.isTypeSupported &&
        MediaRecorder.isTypeSupported(c)
      ) {
        return { mimeType: c };
      }
    }
    return {}; // Deixa o navegador decidir
  }

  async alignAudioWithText(audioBlob, text, progressCallback) {
    // Convert blob to file for upload
    const formData = new FormData();
    formData.append("audio", audioBlob, "extracted_audio.webm");
    formData.append("text", text);
    formData.append("language", "pt-BR"); // Could be configurable

    try {
      // Upload audio file first (with progress)
      if (progressCallback) progressCallback("Uploading audio (0%)...");
      const uploadResult = await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/audio/upload");
        xhr.responseType = "json";
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable && progressCallback) {
            const pct = Math.min(99, Math.round((e.loaded / e.total) * 100));
            progressCallback(`Uploading audio (${pct}%)...`);
            window.UploadProgress?.updateProgress(pct, this.videoPreview?.parentElement);
          }
        };
        xhr.onload = () => {
          window.UploadProgress?.updateProgress(100, this.videoPreview?.parentElement);
          if (xhr.status >= 200 && xhr.status < 300) {
            const json = xhr.response || {};
            if (!json.success) {
              reject(new Error(json.error || json.message || `Upload failed (${xhr.status})`));
            } else {
              resolve(json);
            }
          } else {
            let msg = `Upload failed (${xhr.status})`;
            try {
              const bodyText = xhr.responseText || '';
              const maybe = bodyText ? JSON.parse(bodyText) : null;
              if (maybe && maybe.error_type) {
                msg = `${maybe.error || maybe.message || msg} (${maybe.error_type})`;
                if (maybe.error_type === 'format_error' && this.app?.errorToasts) {
                  this.app.errorToasts.show(`Formato não suportado. Aceitos: wav, mp3, ogg, flac, m4a, aac, webm`, { level: 'warning', autoDismiss: true });
                }
              }
            } catch (_) {}
            reject(new Error(msg));
          }
        };
        xhr.onerror = () => reject(new Error("Network error during upload"));
        xhr.send(formData);
      });

      if (!uploadResult || !uploadResult.filename) {
        throw new Error("Audio upload failed (no filename returned)");
      }

      // Use existing alignment endpoint
      // Attempt SSE streaming version first for richer progress
      const sseSupported = !!window.EventSource;
      const useStreaming = sseSupported;
      if (useStreaming) {
        if (progressCallback) progressCallback('Starting streaming alignment...');
        return await this._streamingEnhancedAlignment(uploadResult.filename, text, progressCallback);
      } else {
        if (progressCallback) progressCallback("Requesting alignment...");
        const alignController = new AbortController();
        this._activeAbortControllers.push(alignController);
        const alignResponse = await fetch("/api/audio/align-enhanced", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            filename: uploadResult.filename,
            text: text,
            fps: 30,
            method: "auto",
            language: "pt-BR",
          }),
          signal: alignController.signal,
        });
        if (!alignResponse.ok) {
          let detail = alignResponse.statusText;
          try {
            const errJson = await alignResponse.json();
            if (errJson && errJson.error_type) {
              detail = `${errJson.error || errJson.message || detail} (${errJson.error_type})`;
            }
          } catch (_) {}
          throw new Error(`Alignment failed: ${detail}`);
        }
        const result = await alignResponse.json();
        if (progressCallback) progressCallback("Alignment complete");
        return result;
      }
    } catch (error) {
      console.error("❌ Audio alignment failed:", error);
      throw error;
    }
  }

  _streamingEnhancedAlignment(filename, text, progressCallback){
    return new Promise((resolve, reject) => {
      try {
        const es = new EventSource('/api/audio/align-enhanced/stream');
        // We need to POST initial data; SSE GET can't carry body. Fallback quickly.
        // Strategy: if server returns 200 but no data for 1s, fallback via fetch POST.
        // Simpler: close and fallback immediately because we can't send POST body via EventSource.
        es.close();
        // Fallback approach: use fetch with POST to a streaming endpoint by query param.
        fetch('/api/audio/align-enhanced/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename, text, fps:30, method:'auto', language:'pt-BR' })
        }).then(resp => {
          if(!resp.ok){
            throw new Error('Streaming request failed '+resp.status);
          }
          const reader = resp.body.getReader();
          const decoder = new TextDecoder();
          let buffer='';
          const parseChunk = () => reader.read().then(({done, value})=>{
            if(done){ return; }
            buffer += decoder.decode(value, {stream:true});
            const parts = buffer.split('\n\n');
            buffer = parts.pop();
            for(const part of parts){
              if(!part.startsWith('data:')) continue;
              try {
                const json = JSON.parse(part.slice(5).trim());
                const ev = json.event; const data = json.data;
                if(progressCallback){
                  const phaseMap = { start:'Iniciando', precheck:'Verificando', load_audio:'Carregando áudio', decode:'Decodificando', transcribe:'Transcrevendo', align:'Alinhando', enhance:'Aprimorando', build_sequence:'Finalizando', complete:'Concluído' };
                  progressCallback(phaseMap[ev] || ev);
                }
                if(ev==='complete'){
                  resolve({ alignment: data.alignment || data.result?.data?.alignment || data });
                } else if(ev==='error'){
                  reject(new Error(data?.error || 'Streaming alignment error'));
                }
              } catch(e){ console.warn('SSE chunk parse error', e); }
            }
            return parseChunk();
          });
          return parseChunk();
        }).catch(err=>reject(err));
      } catch (e){ reject(e); }
    });
  }

  convertAlignmentToSubtitles(alignment) {
    if (!alignment || !alignment.tokens) return [];

    const subtitles = [];
    let currentSubtitle = null;
    const maxDuration = 3000; // 3 seconds max per subtitle
    const maxChars = 40; // Max characters per subtitle chunk (single line heuristic)
    const gapBreakMs = 400; // Pause threshold to force new subtitle
    const minSegmentChars = 12; // Only break on punctuation if we have at least this many chars
    let prevEnd = null;

    for (const token of alignment.tokens) {
      const text = (token.text || "").trim();
      if (!text) continue;
      if (token.start_ms == null || token.end_ms == null) continue;

      // Determine if this token should trigger a new subtitle
      const longGap = prevEnd !== null && token.start_ms - prevEnd > gapBreakMs;
      const needsNew =
        !currentSubtitle ||
        token.start_ms - currentSubtitle.start_ms > maxDuration ||
        currentSubtitle.text.length + text.length + 1 > maxChars ||
        longGap;

      if (needsNew) {
        if (currentSubtitle) subtitles.push(currentSubtitle);
        currentSubtitle = {
          id: subtitles.length,
          text: text,
          start_ms: token.start_ms,
          end_ms: token.end_ms,
          confidence: token.confidence || 1.0,
        };
      } else {
        currentSubtitle.text += " " + text;
        currentSubtitle.end_ms = token.end_ms;
        currentSubtitle.confidence = Math.min(
          currentSubtitle.confidence,
          token.confidence || 1.0
        );
      }

      // If token ends with strong punctuation and segment is sufficiently long, close subtitle early
      if (
        /[,.;!?…]$/.test(text) &&
        currentSubtitle &&
        currentSubtitle.text.length >= minSegmentChars
      ) {
        subtitles.push(currentSubtitle);
        currentSubtitle = null;
      }

      prevEnd = token.end_ms;
    }

    // Add final subtitle
    if (currentSubtitle) {
      subtitles.push(currentSubtitle);
    }

    return subtitles;
  }

  renderSubtitleTimeline() {
    if (!this.subtitleTimeline) return;

    // Use enhanced timeline if available
    if (this.enhancedTimeline) {
      // Convert subtitles to enhanced timeline format
      const segments = this.subtitles.map((subtitle) => ({
        id: subtitle.id || `seg_${Date.now()}_${Math.random()}`,
        text: subtitle.text || "",
        start_time: (subtitle.start_ms || 0) / 1000,
        end_time: (subtitle.end_ms || 0) / 1000,
        confidence: subtitle.confidence || 1.0,
        word_count: subtitle.text ? subtitle.text.split(" ").length : 0,
        reading_speed: 0,
        platform_optimized: {},
        style_overrides: {},
      }));

      this.enhancedTimeline.loadSegments(segments);
      console.log(
        `🎬 Loaded ${segments.length} segments into enhanced timeline`
      );
      return;
    }

    // Fallback to basic timeline
    this.subtitleTimeline.innerHTML = "";

    if (this.subtitles.length === 0) {
      this.subtitleTimeline.innerHTML = `
        <div class="timeline-placeholder">
          <i class="fas fa-waveform-lines"></i>
          <p>Generate subtitles to see enhanced timeline</p>
        </div>
      `;
      return;
    }

    // Create basic timeline visualization
    const timeline = document.createElement("div");
    timeline.className = "subtitle-timeline-track";

    const totalDuration = Math.max(...this.subtitles.map((s) => s.end_ms || 0));

    this.subtitles.forEach((subtitle, index) => {
      const segment = document.createElement("div");
      segment.className = "subtitle-segment";
      segment.dataset.id = subtitle.id;

      const startPercent = ((subtitle.start_ms || 0) / totalDuration) * 100;
      const widthPercent =
        (((subtitle.end_ms || 0) - (subtitle.start_ms || 0)) / totalDuration) *
        100;

      segment.style.left = `${startPercent}%`;
      segment.style.width = `${Math.max(widthPercent, 2)}%`; // Minimum 2% width

      segment.innerHTML = `
        <div class="segment-content">
          <span class="segment-text">${subtitle.text || ""}</span>
          <span class="segment-time">${this.formatTime(
            (subtitle.start_ms || 0) / 1000
          )}</span>
        </div>
        <div class="segment-handle handle-start" data-handle="start"></div>
        <div class="segment-handle handle-end" data-handle="end"></div>
      `;

      // Add click handler for editing
      segment.addEventListener("click", () => this.editSubtitle(subtitle.id));
      // Duplo clique abre edição imediata (seleciona input correspondente)
      segment.addEventListener("dblclick", (e) => {
        e.stopPropagation();
        this.editSubtitle(subtitle.id);
      });

      timeline.appendChild(segment);
    });

    // Scrubbing click on timeline background
    timeline.addEventListener("click", (e) => {
      if (
        e.target.classList.contains("subtitle-segment") ||
        e.target.closest(".subtitle-segment")
      )
        return; // ignore clicks on segments themselves
      const rect = timeline.getBoundingClientRect();
      const pct = (e.clientX - rect.left) / rect.width;
      const totalDuration = Math.max(
        ...this.subtitles.map((s) => s.end_ms || 0)
      );
      const targetMs = pct * totalDuration;
      if (this.videoPreview) {
        this.videoPreview.currentTime = targetMs / 1000;
      }
    });

    // Drag handles for timing adjustment
    let dragData = null;
    const startDrag = (e, segmentEl, handle) => {
      e.stopPropagation();
      const id = parseInt(segmentEl.dataset.id, 10);
      const sub = this.subtitles.find((s) => s.id === id);
      if (!sub) return;
      const rect = timeline.getBoundingClientRect();
      const totalDuration = Math.max(
        ...this.subtitles.map((s) => s.end_ms || 0)
      );
      dragData = {
        id,
        sub,
        rect,
        totalDuration,
        handle,
        origStart: sub.start_ms,
        origEnd: sub.end_ms,
      };
      document.body.style.userSelect = "none";
      this._pushHistory();
      this._ensureSnapMarkersLayer();
    };
    const onMove = (e) => {
      if (!dragData) return;
      const { rect, totalDuration, handle, sub, origStart, origEnd } = dragData;
      const pct = Math.min(
        1,
        Math.max(0, (e.clientX - rect.left) / rect.width)
      );
      const ms = pct * totalDuration;
      if (handle === "start") {
        sub.start_ms = Math.min(ms, sub.end_ms - 100); // keep minimum length 100ms
      } else {
        sub.end_ms = Math.max(ms, sub.start_ms + 100);
      }
      // Prevent overlap with neighbors
      const idx = this.subtitles.indexOf(sub);
      const prev = this.subtitles[idx - 1];
      const next = this.subtitles[idx + 1];
      if (prev && sub.start_ms < prev.end_ms) sub.start_ms = prev.end_ms + 10;
      if (next && sub.end_ms > next.start_ms) sub.end_ms = next.start_ms - 10;
      this._updateSnapMarkers(sub);
      // Live update
      this.renderSubtitleTimeline();
      const overlay = document.getElementById("subtitleOverlay");
      if (overlay) this.updateSubtitleOverlay(overlay);
    };
    const endDrag = () => {
      if (dragData) {
        dragData = null;
        document.body.style.userSelect = "";
        this._clearSnapMarkers();
      }
    };
    timeline.addEventListener("mousedown", (e) => {
      const handle = e.target.closest(".segment-handle");
      if (handle) {
        const segmentEl = handle.closest(".subtitle-segment");
        startDrag(e, segmentEl, handle.dataset.handle);
      }
    });
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", endDrag);

    this.subtitleTimeline.appendChild(timeline);
  }

  renderSubtitleSegments() {
    if (!this.segmentsList) return;

    // Update count
    const countElement = document.querySelector(".segment-count");
    if (countElement) {
      countElement.textContent = `${this.subtitles.length} segments`;
    }

    // Clear existing segments
    this.segmentsList.innerHTML = "";

    this.subtitles.forEach((subtitle, index) => {
      const segmentDiv = document.createElement("div");
      segmentDiv.className = "subtitle-segment-item";
      segmentDiv.dataset.id = subtitle.id;

      segmentDiv.innerHTML = `
        <div class="segment-header">
          <span class="segment-number">#${index + 1}</span>
          <span class="segment-timing">${this.formatTime(
            subtitle.start_ms / 1000
          )} - ${this.formatTime(subtitle.end_ms / 1000)}</span>
        </div>
        <div class="segment-text-content">
          <input type="text" class="segment-text-input" value="${
            subtitle.text
          }" />
        </div>
        <div class="segment-actions">
          <button class="btn btn-sm" onclick="videoEditor.deleteSubtitle(${
            subtitle.id
          })">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      `;

      // Add text editing handler
      const textInput = segmentDiv.querySelector(".segment-text-input");
      textInput.addEventListener("change", () => {
        this.updateSubtitleText(subtitle.id, textInput.value);
      });
      // Atualização ao vivo enquanto digita
      textInput.addEventListener("input", () => {
        this.updateSubtitleTextLive(subtitle.id, textInput.value);
      });

      this.segmentsList.appendChild(segmentDiv);
    });
  }

  editSubtitle(id) {
    const subtitle = this.subtitles.find((s) => s.id === id);
    if (!subtitle) return;

    // Scroll to segment in list and focus input
    const segmentItem = this.segmentsList?.querySelector(`[data-id="${id}"]`);
    if (segmentItem) {
      segmentItem.scrollIntoView({ behavior: "smooth", block: "center" });
      const input = segmentItem.querySelector(".segment-text-input");
      if (input) {
        input.focus();
        input.select();
      }
    }
  }

  _maybeSnap(valueMs, frameMs, id, edge) {
    if (!this._snappingEnabled) return valueMs;
    const original = valueMs;
    this._lastSnapMeta = null;
    const threshold = this._snapThresholdMs;
    const strict = this._strictSnapMode;
    const considerSnap = (candidate, type) => {
      const delta = candidate - original;
      if (Math.abs(delta) < threshold) {
        if (!strict || Math.abs(delta) < threshold) {
          this._lastSnapMeta = {
            type,
            edge,
            target: candidate,
            deltaMs: delta,
            deltaFrames: Math.round(delta / frameMs),
          };
          return candidate;
        }
      }
      return null;
    };
    // frame snap
    const frameSnap = Math.round(valueMs / frameMs) * frameMs;
    const snappedFrame = considerSnap(frameSnap, "frame");
    if (snappedFrame != null) valueMs = snappedFrame;
    // neighbor edges
    for (const s of this.subtitles) {
      if (s.id === id) continue;
      const startCandidate = considerSnap(s.start_ms, "neighbor");
      if (startCandidate != null) valueMs = startCandidate;
      const endCandidate = considerSnap(s.end_ms, "neighbor");
      if (endCandidate != null) valueMs = endCandidate;
    }
    return valueMs;
  }

  _ensureSnapMarkersLayer() {
    if (!this.subtitleTimeline) return;
    let layer = this.subtitleTimeline.querySelector(".snap-markers-layer");
    if (!layer) {
      layer = document.createElement("div");
      layer.className = "snap-markers-layer";
      Object.assign(layer.style, {
        position: "absolute",
        inset: "0",
        pointerEvents: "none",
      });
      this.subtitleTimeline.appendChild(layer);
    }
    this._snapLayer = layer;
  }

  _clearSnapMarkers() {
    if (this._snapLayer) this._snapLayer.innerHTML = "";
  }

  _updateSnapMarkers(activeSub) {
    if (!this._snapLayer || !this.subtitles.length) return;
    const totalDuration = Math.max(...this.subtitles.map((s) => s.end_ms || 0));
    const points = new Set();
    // Frame grid (sparser: every 10 frames)
    const frameMs = 1000 / this._frameRate;
    const frameStep = frameMs * this._frameSnapStep;
    if (this._showFrameGrid) {
      for (let t = 0; t <= totalDuration; t += frameStep) {
        if (
          Math.abs(t - activeSub.start_ms) < this._snapThresholdMs ||
          Math.abs(t - activeSub.end_ms) < this._snapThresholdMs
        ) {
          points.add(t);
        }
      }
    }
    // Neighbor edges
    for (const s of this.subtitles) {
      if (s === activeSub) continue;
      if (
        Math.abs(s.start_ms - activeSub.start_ms) < this._snapThresholdMs ||
        Math.abs(s.start_ms - activeSub.end_ms) < this._snapThresholdMs
      )
        points.add(s.start_ms);
      if (
        Math.abs(s.end_ms - activeSub.start_ms) < this._snapThresholdMs ||
        Math.abs(s.end_ms - activeSub.end_ms) < this._snapThresholdMs
      )
        points.add(s.end_ms);
    }
    this._snapLayer.innerHTML = "";
    points.forEach((ms) => {
      const line = document.createElement("div");
      const leftPct = (ms / totalDuration) * 100;
      Object.assign(line.style, {
        position: "absolute",
        top: 0,
        bottom: 0,
        width: "2px",
        background: "rgba(255,215,0,0.7)",
        left: leftPct + "%",
        transform: "translateX(-1px)",
      });
      this._snapLayer.appendChild(line);
    });
  }

  _pushHistory() {
    const snapshot = JSON.stringify(this.subtitles.map((s) => ({ ...s })));
    this._undoStack.push(snapshot);
    if (this._undoStack.length > this._maxHistory) this._undoStack.shift();
    this._redoStack = [];
  }

  _applyEdgeSnapHighlight(segmentEl, sub, totalDuration) {
    // Remove existing edge guides
    if (!this.subtitleTimeline) return;
    let guideLayer = this.subtitleTimeline.querySelector(".snap-edge-guides");
    if (!guideLayer) {
      guideLayer = document.createElement("div");
      guideLayer.className = "snap-edge-guides";
      Object.assign(guideLayer.style, {
        position: "absolute",
        inset: "0",
        pointerEvents: "none",
      });
      this.subtitleTimeline.appendChild(guideLayer);
    }
    guideLayer.innerHTML = "";
    if (!this._lastSnapMeta || !sub) return;
    const { edge, target } = this._lastSnapMeta;
    if (target == null) return;
    const leftPct = (target / totalDuration) * 100;
    const line = document.createElement("div");
    line.className = "snap-edge-line";
    line.style.left = leftPct + "%";
    line.style.transform = "translateX(-1.5px)";
    guideLayer.appendChild(line);
    // fade out after short time (on mouseup this stays then fades)
    requestAnimationFrame(() => {
      setTimeout(() => {
        line.style.opacity = "0";
      }, 120);
    });
    // add subtle highlight to which edge snapped
    if (segmentEl) {
      segmentEl.dataset.snapEdge = edge;
    }
    // Show tooltip
    this._showSnapTooltip(target, edge, totalDuration);
  }

  _showSnapTooltip(targetMs, edge, totalDuration) {
    if (!this.subtitleTimeline) return;
    if (!this._snapTooltip) {
      this._snapTooltip = document.createElement("div");
      this._snapTooltip.className = "snap-tooltip";
      this.subtitleTimeline.appendChild(this._snapTooltip);
    }
    const frameMs = 1000 / this._frameRate;
    const frameIndex = Math.round(targetMs / frameMs);
    const leftPct = (targetMs / totalDuration) * 100;
    this._snapTooltip.style.left = leftPct + "%";
    this._snapTooltip.style.top = "6px";
    const abs = this._formatAbsoluteTime(targetMs / 1000);
    let deltaHtml = "";
    if (this._lastSnapMeta && typeof this._lastSnapMeta.deltaMs === "number") {
      const d = this._lastSnapMeta.deltaMs;
      const df = this._lastSnapMeta.deltaFrames;
      deltaHtml = ` <span class="snap-delta">${
        d >= 0 ? "+" : ""
      }${d}ms (${df}f)</span>`;
    }
    this._snapTooltip.innerHTML = `${Math.round(
      targetMs
    )}ms (${abs}) <span class="snap-frame">f${frameIndex}</span> <span class="snap-edge">${edge}</span>${deltaHtml}`;
    requestAnimationFrame(() => {
      this._snapTooltip.style.opacity = "1";
    });
    clearTimeout(this._snapTooltip._hideTimer);
    this._snapTooltip._hideTimer = setTimeout(() => {
      this._snapTooltip.style.opacity = "0";
    }, 900);
  }

  _formatAbsoluteTime(seconds) {
    if (!isFinite(seconds)) return "00:00.000";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.round((seconds - Math.floor(seconds)) * 1000);
    return `${String(m).padStart(2, "0")}:${String(s).padStart(
      2,
      "0"
    )}.${String(ms).padStart(3, "0")}`;
  }

  _updateEdgeDelta(segmentEl, edge, deltaMs) {
    if (!segmentEl) return;
    let badge = segmentEl.querySelector(".edge-delta");
    if (!badge) {
      badge = document.createElement("div");
      badge.className = "edge-delta";
      segmentEl.appendChild(badge);
    }
    badge.textContent = (deltaMs >= 0 ? "+" : "") + deltaMs + "ms";
    badge.style.left = edge === "start" ? "-2px" : "calc(100% - 28px)";
  }

  _clearEdgeDelta(segmentEl) {
    if (!segmentEl) return;
    const badge = segmentEl.querySelector(".edge-delta");
    if (badge) badge.remove();
  }

  _debouncedOverlayUpdate() {
    if (this._overlayUpdateRaf) cancelAnimationFrame(this._overlayUpdateRaf);
    this._overlayUpdateRaf = requestAnimationFrame(() => {
      const overlay = document.getElementById("subtitleOverlay");
      if (overlay) this.updateSubtitleOverlay(overlay);
    });
  }

  undo() {
    if (!this._undoStack.length) return;
    const current = JSON.stringify(this.subtitles.map((s) => ({ ...s })));
    this._redoStack.push(current);
    const prev = this._undoStack.pop();
    this.subtitles = JSON.parse(prev);
    this.renderSubtitleTimeline();
    this.renderSubtitleSegments();
  }

  redo() {
    if (!this._redoStack.length) return;
    const current = JSON.stringify(this.subtitles.map((s) => ({ ...s })));
    this._undoStack.push(current);
    const next = this._redoStack.pop();
    this.subtitles = JSON.parse(next);
    this.renderSubtitleTimeline();
    this.renderSubtitleSegments();
  }

  attachUndoRedoShortcuts() {
    if (this._undoBound) return;
    this._undoBound = true;
    window.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) this.redo();
        else this.undo();
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {
        e.preventDefault();
        this.redo();
      } else if (e.key === "Alt") {
        // Holding Alt temporarily disables snapping
        this._snappingEnabled = false;
      } else if (!e.ctrlKey && !e.metaKey && e.key.toLowerCase() === "f") {
        this._showFrameGrid = !this._showFrameGrid;
        try {
          localStorage.setItem(
            "showFrameGrid",
            this._showFrameGrid ? "1" : "0"
          );
        } catch (err) {}
        this.app?.showStatus?.(
          this._showFrameGrid ? "Frame grid ON" : "Frame grid OFF"
        );
        if (this._snapLayer) this._clearSnapMarkers();
      } else if (e.shiftKey && (e.key === "." || e.key === ">")) {
        this._frameSnapStep = Math.min(this._frameSnapStep + 1, 30);
        if (this.frameSnapStepSelect)
          this.frameSnapStepSelect.value = String(this._frameSnapStep);
        try {
          localStorage.setItem("frameSnapStep", String(this._frameSnapStep));
        } catch (err) {}
        this.app?.showStatus?.(
          `Snap step: every ${this._frameSnapStep} frame(s)`
        );
      } else if (e.key.toLowerCase() === "s" && !e.ctrlKey && !e.metaKey) {
        this._strictSnapMode = !this._strictSnapMode;
        try {
          localStorage.setItem(
            "strictSnapMode",
            this._strictSnapMode ? "1" : "0"
          );
        } catch (e) {}
        this.app?.showStatus?.(
          this._strictSnapMode ? "Strict snap ON" : "Strict snap OFF"
        );
      } else if (e.shiftKey && (e.key === "/" || e.key === "?")) {
        this._frameSnapStep = Math.max(this._frameSnapStep - 1, 1);
        if (this.frameSnapStepSelect)
          this.frameSnapStepSelect.value = String(this._frameSnapStep);
        try {
          localStorage.setItem("frameSnapStep", String(this._frameSnapStep));
        } catch (err) {}
        this.app?.showStatus?.(
          `Snap step: every ${this._frameSnapStep} frame(s)`
        );
      }
    });
    window.addEventListener("keyup", (e) => {
      if (e.key === "Alt") this._snappingEnabled = true;
    });
  }

  updateSubtitleText(id, newText) {
    const subtitle = this.subtitles.find((s) => s.id === id);
    if (subtitle) {
      this._pushHistory();
      subtitle.text = newText;
      this.renderSubtitleTimeline(); // Update timeline display
    }
  }

  updateSubtitleTextLive(id, newText) {
    const subtitle = this.subtitles.find((s) => s.id === id);
    if (subtitle) {
      subtitle.text = newText;
      // Atualiza apenas overlay atual sem redesenhar toda timeline para performance
      const overlay = document.getElementById("subtitleOverlay");
      if (overlay && overlay.style.display !== "none") {
        this.updateSubtitleOverlay(overlay);
      }
    }
  }

  deleteSubtitle(id) {
    this._pushHistory();
    this.subtitles = this.subtitles.filter((s) => s.id !== id);
    this.renderSubtitleTimeline();
    this.renderSubtitleSegments();
    this.updateUIState();
  }

  clearSubtitles() {
    if (this.subtitles.length === 0) return;

    if (confirm("Clear all subtitles? This cannot be undone.")) {
      this.subtitles = [];
      this.renderSubtitleTimeline();
      this.renderSubtitleSegments();
      this.updateUIState();
      this.app.showStatus("Subtitles cleared");
    }
  }

  // Platform Presets
  applyPreset(presetName) {
    console.log("🎨 Applying preset:", presetName);

    // Remove active class from all preset buttons
    this.presetButtons?.forEach((btn) => btn.classList.remove("active"));

    // Add active class to selected preset
    const selectedBtn = document.querySelector(`[data-preset="${presetName}"]`);
    if (selectedBtn) {
      selectedBtn.classList.add("active");
    }

    this.currentPreset = presetName;

    // Apply preset-specific settings
    const presets = {
      "instagram-story": {
        fontSize: 32,
        fontWeight: "bold",
        textColor: "#ffffff",
        backgroundColor: "#000000",
        backgroundOpacity: 60,
        outlineWidth: 2,
        verticalPosition: "bottom",
        horizontalAlign: "center",
        maxWidth: 85,
      },
      "instagram-reel": {
        fontSize: 28,
        fontWeight: "600",
        textColor: "#ffffff",
        backgroundColor: "#000000",
        backgroundOpacity: 70,
        outlineWidth: 2,
        verticalPosition: "bottom",
        horizontalAlign: "center",
        maxWidth: 90,
      },
      tiktok: {
        fontSize: 36,
        fontWeight: "bold",
        textColor: "#ffffff",
        backgroundColor: "#000000",
        backgroundOpacity: 50,
        outlineWidth: 3,
        verticalPosition: "bottom",
        horizontalAlign: "center",
        maxWidth: 80,
      },
      "youtube-shorts": {
        fontSize: 30,
        fontWeight: "bold",
        textColor: "#ffffff",
        backgroundColor: "#000000",
        backgroundOpacity: 65,
        outlineWidth: 2,
        verticalPosition: "bottom",
        horizontalAlign: "center",
        maxWidth: 85,
      },
    };

    const preset = presets[presetName];
    if (preset) {
      // Apply settings to controls
      if (this.fontSize) {
        this.fontSize.value = preset.fontSize;
        this.fontSize.dispatchEvent(new Event("input"));
      }
      if (this.fontWeight) this.fontWeight.value = preset.fontWeight;
      if (this.textColor) this.textColor.value = preset.textColor;
      if (this.backgroundColor)
        this.backgroundColor.value = preset.backgroundColor;
      if (this.backgroundOpacity) {
        this.backgroundOpacity.value = preset.backgroundOpacity;
        this.backgroundOpacity.dispatchEvent(new Event("input"));
      }
      if (this.outlineWidth) {
        this.outlineWidth.value = preset.outlineWidth;
        this.outlineWidth.dispatchEvent(new Event("input"));
      }
      if (this.verticalPosition)
        this.verticalPosition.value = preset.verticalPosition;
      if (this.horizontalAlign)
        this.horizontalAlign.value = preset.horizontalAlign;
      if (this.maxWidth) {
        this.maxWidth.value = preset.maxWidth;
        this.maxWidth.dispatchEvent(new Event("input"));
      }

      this.updateSubtitleStyle();
      this.app.showStatus(`Applied ${presetName.replace("-", " ")} preset`);
    }
  }

  updateSubtitleStyle() {
    // This will be used for real-time preview
    console.log("🎨 Updating subtitle style");

    const style = this.getCurrentStyle();

    // Apply to video preview if subtitles are being previewed
    this.applyStyleToPreview(style);
  }

  getCurrentStyle() {
    return {
      fontFamily: this.fontFamily?.value || "Arial, sans-serif",
      fontSize: this.fontSize?.value || 24,
      fontWeight: this.fontWeight?.value || "normal",
      textColor: this.textColor?.value || "#ffffff",
      backgroundColor: this.backgroundColor?.value || "#000000",
      backgroundOpacity: this.backgroundOpacity?.value || 70,
      outlineColor: this.outlineColor?.value || "#000000",
      outlineWidth: this.outlineWidth?.value || 2,
      verticalPosition: this.verticalPosition?.value || "bottom",
      horizontalAlign: this.horizontalAlign?.value || "center",
      maxWidth: this.maxWidth?.value || 80,
    };
  }

  applyStyleToPreview(style) {
    // This would apply the style to any subtitle preview overlay
    // Implementation depends on the preview system
  }

  // Preview and Export
  previewWithSubtitles() {
    if (!this.isVideoLoaded || this.subtitles.length === 0) {
      this.app.showError("Please load a video and generate subtitles first");
      return;
    }

    console.log("👁️ Previewing video with subtitles");

    // This would create a subtitle overlay on the video
    this.createSubtitleOverlay();

    this.app.showStatus("Subtitle preview enabled");
  }

  createSubtitleOverlay() {
    // Create overlay container if it doesn't exist
    let overlay = document.getElementById("subtitleOverlay");
    if (!overlay) {
      overlay.id = "subtitleOverlay";
      overlay.className = "subtitle-overlay";

      const videoContainer = this.videoPreview?.parentElement;
      if (videoContainer) {
        videoContainer.style.position = "relative";
        videoContainer.appendChild(overlay);
      }
    }

    // Update overlay based on current video time
    this.updateSubtitleOverlay(overlay);

    // Set up time update listener
    if (this.videoPreview && !this.subtitleUpdateListener) {
      this.subtitleUpdateListener = () => this.updateSubtitleOverlay(overlay);
      this.videoPreview.addEventListener(
        "timeupdate",
        this.subtitleUpdateListener
      );
    }
  }

  updateSubtitleOverlay(overlay) {
    if (!this.videoPreview || !overlay) return;

    const currentTime = this.videoPreview.currentTime * 1000; // ms
    const currentSubtitle = this.subtitles.find(
      (s) => currentTime >= s.start_ms && currentTime <= s.end_ms
    );

    if (currentSubtitle) {
      const style = this.getCurrentStyle();
      overlay.style.display = "block";
      overlay.innerHTML = `<div class="subtitle-text" style="
        font-family: ${style.fontFamily};
        font-size: ${style.fontSize}px;
        font-weight: ${style.fontWeight};
        color: ${style.textColor};
        background: ${this.hexToRgba(
          style.backgroundColor,
          style.backgroundOpacity / 100
        )};
        text-stroke: ${style.outlineWidth}px ${style.outlineColor};
        -webkit-text-stroke: ${style.outlineWidth}px ${style.outlineColor};
        text-align: ${style.horizontalAlign};
        max-width: ${style.maxWidth}%;
        position: absolute;
        ${this._computeDynamicVerticalPosition(style)}: 20px;
        left: 50%;
        transform: translateX(-50%);
        padding: 8px 16px;
        border-radius: 4px;
        word-wrap: break-word;
        z-index: 10;
      ">${this._formatSubtitleLines(currentSubtitle.text, style)}</div>`;
    } else {
      overlay.style.display = "none";
    }
  }

  _computeDynamicVerticalPosition(style) {
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
  }

  _formatSubtitleLines(text, style) {
    if (!text) return "";
    const words = text.split(/\s+/);
    if (words.length <= 6) return this._escapeHtml(text);
    const targetChars = Math.ceil(text.length / 2);
    let line1 = "";
    let line2 = "";
    let acc = 0;
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
  }

  _escapeHtml(str) {
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
  }

  hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  async exportVideo() {
    if (!this.isVideoLoaded || this.subtitles.length === 0) {
      this.app.showError("Please load a video and generate subtitles first");
      return;
    }

    try {
      console.log("📤 Exporting video with subtitles...");
      this.app.showStatus("Preparing video export with subtitles...");

      // Prepare export data
      const exportData = {
        videoFile: this.videoFile,
        subtitles: this.subtitles,
        style: this.getCurrentStyle(),
        preset: this.currentPreset,
      };

      // Use existing export system
      const result = await this.processVideoExport(exportData);

      if (result.success) {
        this.app.showStatus("Video exported successfully with subtitles!");

        // Trigger download if URL provided
        if (result.downloadUrl) {
          const a = document.createElement("a");
          a.href = result.downloadUrl;
          a.download = result.filename || "video_with_subtitles.mp4";
          a.click();
        }
      } else {
        throw new Error(result.error || "Export failed");
      }
    } catch (error) {
      console.error("❌ Video export failed:", error);
      this.app.showError(`Export failed: ${error.message}`);
    }
  }

  async processVideoExport(exportData) {
    // This would integrate with the existing export system
    // For now, return a mock response
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          success: true,
          filename: "video_with_subtitles.mp4",
          downloadUrl: "#",
        });
      }, 2000);
    });
  }

  // UI State Management
  updateUIState() {
    const hasVideo = this.isVideoLoaded;
    const hasSubtitles = this.subtitles.length > 0;
    const hasText = this.videoTranscript?.value.trim().length > 0;

    // Update button states
    if (this.generateSubtitlesBtn) {
      this.generateSubtitlesBtn.disabled = !(hasVideo && hasText);
    }

    if (this.clearSubtitlesBtn) {
      this.clearSubtitlesBtn.disabled = !hasSubtitles;
    }

    if (this.previewSubtitles) {
      this.previewSubtitles.disabled = !(hasVideo && hasSubtitles);
    }

    if (this.exportVideoWithSubtitles) {
      this.exportVideoWithSubtitles.disabled = !(hasVideo && hasSubtitles);
    }
  }
}

// Disponibilizar a classe globalmente
window.VideoEditorModule = VideoEditorModule;
console.log(
  "✅ VideoEditorModule class defined and added to window successfully"
);
