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
    this.videoTranscript = document.getElementById("videoTranscript");
    this.subtitleTimeline = document.getElementById("subtitleTimeline");
    this.segmentsList = document.getElementById("segmentsList");
    this.previewSubtitles = document.getElementById("previewSubtitles");
    this.exportVideoWithSubtitles = document.getElementById(
      "exportVideoWithSubtitles"
    );

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

    // Subtitle controls
    this.generateSubtitlesBtn?.addEventListener("click", () =>
      this.generateSubtitles()
    );
    this.clearSubtitlesBtn?.addEventListener("click", () =>
      this.clearSubtitles()
    );
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
      console.log("🎬 Generating enhanced subtitles for video...");
      this.app.showStatus(
        "Generating intelligent subtitles from video audio..."
      );

      // Extract audio from video and use existing alignment system
      const audioBlob = await this.extractAudioFromVideo(this.videoFile);

      // Use the existing audio alignment system
      const alignmentResult = await this.alignAudioWithText(audioBlob, text);

      if (alignmentResult && alignmentResult.alignment) {
        // Try enhanced subtitle generation first
        const enhancedResult = await this.generateEnhancedSubtitles(
          alignmentResult.alignment
        );

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
      } else {
        throw new Error("Failed to generate subtitle alignment");
      }
    } catch (error) {
      console.error("❌ Subtitle generation failed:", error);
      this.app.showError(`Subtitle generation failed: ${error.message}`);
    }
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
      try {
        this.enhancedTimeline = new EnhancedSubtitleTimeline(
          this.subtitleTimeline,
          this
        );

        // Listen for timeline events
        this.enhancedTimeline.addEventListener("segmentUpdated", (e) => {
          this.handleSegmentUpdate(e.detail);
        });

        this.enhancedTimeline.addEventListener("segmentDeleted", (e) => {
          this.handleSegmentDelete(e.detail);
        });

        this.enhancedTimeline.addEventListener("autoAlignRequested", () => {
          this.autoAlignSubtitles();
        });

        console.log("✨ Enhanced subtitle timeline initialized");
      } catch (error) {
        console.warn("Enhanced timeline initialization failed:", error);
        this.enhancedTimeline = null;
      }
    }
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
    // Create a temporary audio element to extract audio
    return new Promise((resolve, reject) => {
      const video = document.createElement("video");
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");

      video.addEventListener("loadedmetadata", async () => {
        try {
          // Use MediaRecorder to extract audio
          const stream = canvas.captureStream();
          const mediaRecorder = new MediaRecorder(stream, {
            mimeType: "audio/webm",
          });
          const chunks = [];

          mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
          mediaRecorder.onstop = () => {
            const audioBlob = new Blob(chunks, { type: "audio/webm" });
            resolve(audioBlob);
          };

          mediaRecorder.start();
          video.play();

          // Stop after video ends
          video.addEventListener("ended", () => {
            mediaRecorder.stop();
          });
        } catch (error) {
          reject(error);
        }
      });

      video.src = URL.createObjectURL(videoFile);
    });
  }

  async alignAudioWithText(audioBlob, text) {
    // Convert blob to file for upload
    const formData = new FormData();
    formData.append("audio", audioBlob, "extracted_audio.webm");
    formData.append("text", text);
    formData.append("language", "pt-BR"); // Could be configurable

    try {
      // Upload audio file first
      const uploadResponse = await fetch("/api/audio/upload", {
        method: "POST",
        body: formData,
      });

      if (!uploadResponse.ok) {
        throw new Error(`Upload failed: ${uploadResponse.statusText}`);
      }

      const uploadResult = await uploadResponse.json();

      if (!uploadResult.success || !uploadResult.filename) {
        throw new Error("Audio upload failed");
      }

      // Use existing alignment endpoint
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
      });

      if (!alignResponse.ok) {
        throw new Error(`Alignment failed: ${alignResponse.statusText}`);
      }

      return await alignResponse.json();
    } catch (error) {
      console.error("❌ Audio alignment failed:", error);
      throw error;
    }
  }

  convertAlignmentToSubtitles(alignment) {
    if (!alignment || !alignment.tokens) return [];

    const subtitles = [];
    let currentSubtitle = null;
    const maxDuration = 3000; // 3 seconds max per subtitle
    const maxChars = 40; // Max characters per line

    for (const token of alignment.tokens) {
      if (token.type === "word" && token.text.trim()) {
        if (
          !currentSubtitle ||
          token.start_ms - currentSubtitle.start_ms > maxDuration ||
          currentSubtitle.text.length + token.text.length > maxChars
        ) {
          // Start new subtitle
          if (currentSubtitle) {
            subtitles.push(currentSubtitle);
          }

          currentSubtitle = {
            id: subtitles.length,
            text: token.text,
            start_ms: token.start_ms,
            end_ms: token.end_ms,
            confidence: token.confidence || 1.0,
          };
        } else {
          // Extend current subtitle
          currentSubtitle.text += " " + token.text;
          currentSubtitle.end_ms = token.end_ms;
          currentSubtitle.confidence = Math.min(
            currentSubtitle.confidence,
            token.confidence || 1.0
          );
        }
      }
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
      `;

      // Add click handler for editing
      segment.addEventListener("click", () => this.editSubtitle(subtitle.id));

      timeline.appendChild(segment);
    });

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

  updateSubtitleText(id, newText) {
    const subtitle = this.subtitles.find((s) => s.id === id);
    if (subtitle) {
      subtitle.text = newText;
      this.renderSubtitleTimeline(); // Update timeline display
    }
  }

  deleteSubtitle(id) {
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
      overlay = document.createElement("div");
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

    const currentTime = this.videoPreview.currentTime * 1000; // Convert to ms

    // Find current subtitle
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
        ${style.verticalPosition}: 20px;
        left: 50%;
        transform: translateX(-50%);
        padding: 8px 16px;
        border-radius: 4px;
        word-wrap: break-word;
        z-index: 10;
      ">${currentSubtitle.text}</div>`;
    } else {
      overlay.style.display = "none";
    }
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
