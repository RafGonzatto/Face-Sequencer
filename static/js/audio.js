// audio.js - Audio functionality for Face Sequencer Pro

class AudioManager {
  constructor(app) {
    console.log("AudioManager being initialized...");
    this.app = app;
    this.audioFile = null;
    this.audioBlob = null;
    this.audioElement = null;
    this.wavesurfer = null;
    this.isAudioMode = false;
    this.markers = [];
    this.alignmentTokens = null; // Para armazenar tokens de alinhamento

    this.initElements();
    this.initWaveSurfer();
    this.bindEvents();
    console.log("AudioManager initialized successfully");
  }

  initElements() {
    // Audio file upload elements
    this.audioFileInput = document.getElementById("audioFileInput");
    this.selectedAudioFile = document.getElementById("selectedAudioFile");
    this.uploadAudioBtn = document.getElementById("uploadAudioBtn");

    console.log("Audio elements found:", {
      audioFileInput: !!this.audioFileInput,
      selectedAudioFile: !!this.selectedAudioFile,
      uploadAudioBtn: !!this.uploadAudioBtn,
    });

    // Audio toggle elements
    this.timingModeToggle = document.getElementById("timingModeToggle");

    // Audio visualization and control elements
    this.audioVisualizationContainer = document.getElementById(
      "audioVisualizationContainer"
    );
    this.waveformContainer = document.getElementById("waveformContainer");
    this.audioPlayBtn = document.getElementById("audioPlayBtn");
    this.audioProgress = document.getElementById("audioProgress");
    this.audioProgressBar = document.getElementById("audioProgressBar");
    this.currentTimeDisplay = document.getElementById("currentTime");
    this.durationDisplay = document.getElementById("duration");
  }

  initWaveSurfer() {
    if (!this.waveformContainer) {
      console.error("WaveformContainer not found!");
      return;
    }

    this.wavesurfer = WaveSurfer.create({
      container: this.waveformContainer,
      waveColor: "#64748b",
      progressColor: "#2563eb",
      cursorColor: "#ef4444",
      barWidth: 2,
      barRadius: 3,
      cursorWidth: 1,
      height: 80,
      barGap: 2,
      responsive: true,
    });

    // Add wavesurfer events
    this.wavesurfer.on("ready", () => {
      this.updateAudioDuration();
      console.log("Audio ready");
    });

    this.wavesurfer.on("audioprocess", () => {
      this.updateCurrentTime();
      // Dynamic playback line sync when audio-driven
      if (
        this.isAudioMode &&
        this.app?.timelineEnhancer &&
        this.app?.frameStartTimes
      ) {
        const ms = this.wavesurfer.getCurrentTime() * 1000;
        this.app.timelineEnhancer.updatePlaybackLine(ms);
      }
    });

    this.wavesurfer.on("seek", () => {
      this.updateCurrentTime();
    });

    this.wavesurfer.on("finish", () => {
      this.audioPlayBtn.innerHTML = '<i class="fas fa-play"></i>';
    });
  }

  bindEvents() {
    // File selection event
    if (this.audioFileInput) {
      this.audioFileInput.addEventListener("change", (e) => {
        console.log("Audio file selected");
        this.handleFileSelection(e);
      });
    } else {
      console.error("AudioFileInput element not found");
    }

    // Upload button event
    if (this.uploadAudioBtn) {
      this.uploadAudioBtn.addEventListener("click", () => {
        console.log("Upload button clicked");
        this.uploadAudio();
      });
    } else {
      console.error("UploadAudioBtn element not found");
    }

    // Toggle switch between manual and audio-driven timing
    if (this.timingModeToggle) {
      this.timingModeToggle.addEventListener("change", (e) => {
        this.toggleTimingMode(e.target.checked);
      });
    } else {
      console.warn('AudioManager: timingModeToggle not found (timing toggle disabled)');
    }

    // Audio playback controls
    if (this.audioPlayBtn) {
      this.audioPlayBtn.addEventListener("click", () => {
        this.toggleAudioPlayback();
      });
    }

    if (this.audioProgress) {
      this.audioProgress.addEventListener("click", (e) => {
        this.seekAudio(e);
      });
    }
  }

  handleFileSelection(e) {
    if (e.target.files && e.target.files.length > 0) {
      this.audioFile = e.target.files[0];
      if (this.selectedAudioFile) {
        this.selectedAudioFile.textContent = this.audioFile.name;
      }

      // Create audio URL for wavesurfer
      this.audioBlob = URL.createObjectURL(this.audioFile);
      this.wavesurfer.load(this.audioBlob);

      // Show audio visualization container
      if (this.audioVisualizationContainer) {
        this.audioVisualizationContainer.style.display = "block";
      }
    }
  }

  toggleTimingMode(isAudioMode) {
    this.isAudioMode = isAudioMode;

    // Toggle visibility of audio visualization container
    if (this.audioVisualizationContainer) {
      this.audioVisualizationContainer.style.display = isAudioMode
        ? "block"
        : "none";
    }

    // Update app state or other UI elements as needed
    console.log("Timing mode set to:", isAudioMode ? "audio-driven" : "manual");

    // Notify the main app about the mode change
    if (this.app && typeof this.app.onTimingModeChange === "function") {
      this.app.onTimingModeChange(isAudioMode);
    }
  }

  uploadAudio() {
    console.log("uploadAudio method called");
    if (!this.audioFile) {
      this.app?.reportError("Please select an audio file first.", {
        level: "warning",
        autoDismiss: true,
      });
      return;
    }

    const formData = new FormData();
    formData.append("audio", this.audioFile);

    // Show loading state
    if (this.uploadAudioBtn) {
      this.uploadAudioBtn.disabled = true;
      this.uploadAudioBtn.innerHTML =
        '<i class="fas fa-spinner fa-spin"></i> Uploading...';
    }

    console.log("Sending fetch request to /api/audio/upload");
    const correlationId = `upl-${Date.now().toString(36)}-${Math.random()
      .toString(36)
      .slice(2, 7)}`;
    window.ErrorInstrumentation?.record("audio.upload.start", {
      correlationId,
      filename: this.audioFile.name,
    });
    fetch("/api/audio/upload", {
      method: "POST",
      body: formData,
      _retryAttempts: 2,
    })
      .then((resp) => resp.json())
      .then((data) => {
        if (data.success) {
          window.ErrorInstrumentation?.record("audio.upload.success", {
            correlationId,
          });
          if (data.alignment && data.alignment.tokens) {
            this.createTimingMarkers(data.alignment.tokens);
            // Expose tokens to app for future timeline phoneme markers
            if (this.app) this.app.alignmentTokens = data.alignment.tokens;
          }
          if (data.audio?.filename && this.app?.state) {
            this.app.state.audioFileId = data.audio.filename;
          }
          if (this.timingModeToggle) {
            this.timingModeToggle.checked = true;
            this.toggleTimingMode(true);
          }
          this.app?.errorToasts?.show("Audio uploaded successfully", {
            level: "success",
            autoDismiss: true,
            timeout: 3000,
          });
        } else {
          window.ErrorInstrumentation?.record("audio.upload.failure", {
            correlationId,
            error: data.error,
          });
          this.app?.reportError(
            `Audio upload failed: ${data.error || "Unknown error"}`,
            { action: () => this.uploadAudio(), actionLabel: "Retry Upload" }
          );
        }
      })
      .catch((err) => {
        window.ErrorInstrumentation?.record("audio.upload.exception", {
          correlationId,
          message: err?.message,
        });
        this.app?.reportError(`Audio upload error: ${err.message}`, {
          action: () => this.uploadAudio(),
          actionLabel: "Retry Upload",
        });
      })
      .finally(() => {
        if (this.uploadAudioBtn) {
          this.uploadAudioBtn.disabled = false;
          this.uploadAudioBtn.innerHTML =
            '<i class="fas fa-upload"></i> Upload Audio';
        }
      });
  }

  toggleAudioPlayback() {
    if (!this.wavesurfer) return;

    if (this.wavesurfer.isPlaying()) {
      this.wavesurfer.pause();
      this.audioPlayBtn.innerHTML = '<i class="fas fa-play"></i>';

      // Add visual feedback
      this.audioPlayBtn.classList.remove("playing");
      document.body.classList.remove("playback-active");

      // Stop animation sync if it was running
      if (this.app && this.app.state && this.app.state.syncPlaybackActive) {
        this.app.stopSyncPlayback();
      }

      // Update UI state
      this.app.state.isPlaying = false;

      // Add visual notification
      this.showTemporaryNotification("Paused");
    } else {
      this.wavesurfer.play();
      this.audioPlayBtn.innerHTML = '<i class="fas fa-pause"></i>';

      // Add visual feedback
      this.audioPlayBtn.classList.add("playing");
      document.body.classList.add("playback-active");

      // Start animation sync
      if (this.app && this.isAudioMode) {
        this.app.state.isPlaying = true;
        this.app.state.syncPlaybackActive = true;

        // Initial sync on start
        const currentTime = this.wavesurfer.getCurrentTime() * 1000; // Convert to ms
        this.app.updateAnimationForAudioTime(currentTime);
      }

      // Add visual notification
      this.showTemporaryNotification("Playing");
    }
  }

  seekAudio(e) {
    if (!this.wavesurfer) return;

    // Prevent seeking if there's no loaded audio
    if (!this.wavesurfer.getDuration()) return;

    // Calculate percentage based on click position
    const rect = this.audioProgress.getBoundingClientRect();
    const clickPos = e.clientX - rect.left;
    const percent = clickPos / this.audioProgress.clientWidth;

    // Ensure percent is between 0 and 1
    const clampedPercent = Math.max(0, Math.min(1, percent));

    // Seek to position
    this.wavesurfer.seekTo(clampedPercent);

    // Update animation frame if in sync mode
    if (this.isAudioMode) {
      const currentTime = this.wavesurfer.getCurrentTime() * 1000; // Convert to ms
      this.app.updateAnimationForAudioTime(currentTime);

      // Show visual indicator for frame change
      const formattedTime = this.formatTime(this.wavesurfer.getCurrentTime());
      this.showTemporaryNotification(`Seek to ${formattedTime}`);
    }
  }

  showTemporaryNotification(message) {
    // Create notification element if it doesn't exist
    let notification = document.getElementById("audio-notification");
    if (!notification) {
      notification = document.createElement("div");
      notification.id = "audio-notification";
      notification.style.cssText = `
        position: absolute;
        top: -40px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.7);
        color: white;
        padding: 5px 10px;
        border-radius: 4px;
        font-size: 12px;
        opacity: 0;
        transition: opacity 0.3s, top 0.3s;
        z-index: 1000;
      `;
      this.audioVisualizationContainer.style.position = "relative";
      this.audioVisualizationContainer.appendChild(notification);
    }

    // Show notification with message
    notification.textContent = message;
    notification.style.opacity = "1";
    notification.style.top = "10px";

    // Hide after 1.5 seconds
    clearTimeout(this.notificationTimeout);
    this.notificationTimeout = setTimeout(() => {
      notification.style.opacity = "0";
      notification.style.top = "-40px";
    }, 1500);
  }

  updateCurrentTime() {
    if (!this.wavesurfer) return;

    const currentTime = this.wavesurfer.getCurrentTime();
    if (this.currentTimeDisplay) {
      this.currentTimeDisplay.textContent = this.formatTime(currentTime);
    }

    // Update progress bar
    const duration = this.wavesurfer.getDuration();
    if (duration && this.audioProgressBar) {
      const percent = (currentTime / duration) * 100;
      this.audioProgressBar.style.width = `${percent}%`;
    }

    // Synchronize with animation if in audio-driven mode
    if (this.isAudioMode && this.app) {
      this.syncAnimationWithAudio(currentTime);
    }
  }

  updateAudioDuration() {
    if (!this.wavesurfer) return;

    const duration = this.wavesurfer.getDuration();
    this.durationDisplay.textContent = this.formatTime(duration);
  }

  formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, "0")}`;
  }

  createTimingMarkers(tokens) {
    // Clear existing markers
    this.markers.forEach((marker) => {
      marker.element.remove();
    });
    this.markers = [];

    // Store tokens for later use in sequence building
    this.alignmentTokens = tokens;
    console.log("Alignment tokens stored:", this.alignmentTokens);

    if (!tokens || !this.wavesurfer) return;

    const duration = this.wavesurfer.getDuration() * 1000; // Convert to ms

    tokens.forEach((token) => {
      if (token.type === "word") {
        const percent = (token.start_ms / duration) * 100;

        // Create marker element
        const marker = document.createElement("div");
        marker.className = "timing-marker";
        marker.style.left = `${percent}%`;

        // Create label
        const label = document.createElement("span");
        label.className = "timing-label";
        label.textContent = token.text;
        label.style.left = `${percent}%`;

        // Add to container
        this.waveformContainer.appendChild(marker);
        this.waveformContainer.appendChild(label);

        // Store reference
        this.markers.push({
          element: marker,
          labelElement: label,
          time: token.start_ms,
          text: token.text,
        });
      }
    });
  }

  syncAnimationWithAudio(currentTime) {
    if (!this.wavesurfer || !this.isAudioMode) return;

    // Find the closest marker to the current time
    const currentTimeMs = currentTime * 1000;

    // Reset all markers to default state first
    this.markers.forEach((marker) => {
      marker.element.classList.remove("active-marker");
      if (marker.labelElement) {
        marker.labelElement.classList.remove("active-label");
      }
    });

    // Find the closest marker that is earlier than or equal to the current time
    // Use a small lookahead window to improve responsiveness (50ms)
    const lookaheadWindow = 50; // ms
    const activeMarker = this.markers.reduce((closest, marker) => {
      // Include markers slightly ahead of current time for better responsiveness
      if (
        marker.time <= currentTimeMs + lookaheadWindow &&
        (!closest ||
          Math.abs(marker.time - currentTimeMs) <
            Math.abs(closest.time - currentTimeMs))
      ) {
        return marker;
      }
      return closest;
    }, null);

    // Highlight the active marker
    if (activeMarker) {
      activeMarker.element.classList.add("active-marker");
      if (activeMarker.labelElement) {
        activeMarker.labelElement.classList.add("active-label");
      }

      // Only update animation if there's a significant change or we haven't updated recently
      // This prevents too frequent updates that might cause jitter
      if (
        !this.lastMarkerTime ||
        Math.abs(activeMarker.time - this.lastMarkerTime) > 20 ||
        Date.now() - (this.lastUpdateTime || 0) > 100
      ) {
        // Sync with the animation frame in the main app
        if (
          this.app &&
          typeof this.app.updateAnimationForAudioTime === "function"
        ) {
          this.app.updateAnimationForAudioTime(currentTimeMs);

          // Store last update time to throttle updates
          this.lastUpdateTime = Date.now();
          this.lastMarkerTime = activeMarker.time;
        }
      }

      // Display the current word in the sync preview area with transition effect
      this.updateSyncPreview(activeMarker.text);

      // Show visual waveform highlight around active marker
      this.highlightActiveRegion(activeMarker.time);
    }
  }

  highlightActiveRegion(timeMs) {
    // Remove any existing highlight
    const existingHighlight =
      this.waveformContainer.querySelector(".active-region");
    if (existingHighlight) {
      existingHighlight.remove();
    }

    if (!this.wavesurfer) return;

    // Create a new highlight region
    const duration = this.wavesurfer.getDuration() * 1000; // Convert to ms
    const percent = (timeMs / duration) * 100;
    const width = 3; // Width of highlight in percent

    const highlight = document.createElement("div");
    highlight.className = "active-region";
    highlight.style.cssText = `
      position: absolute;
      top: 0;
      height: 100%;
      left: ${Math.max(0, percent - width / 2)}%;
      width: ${width}%;
      background: rgba(59, 130, 246, 0.3);
      border-radius: 2px;
      pointer-events: none;
      z-index: 5;
      transition: left 0.1s ease;
    `;

    this.waveformContainer.appendChild(highlight);
  }

  updateSyncPreview(text) {
    // Create sync preview area if it doesn't exist
    if (!this.syncPreviewArea) {
      this.syncPreviewArea = document.createElement("div");
      this.syncPreviewArea.className = "sync-preview";
      this.syncPreviewArea.innerHTML =
        '<div class="sync-preview-title">Current Word</div><div class="sync-preview-text"></div>';
      this.audioVisualizationContainer.appendChild(this.syncPreviewArea);

      // Create the text element
      this.syncPreviewText =
        this.syncPreviewArea.querySelector(".sync-preview-text");
    }

    // Update the text
    if (this.syncPreviewText) {
      this.syncPreviewText.textContent = text || "—";

      // Add a highlight animation
      this.syncPreviewText.classList.remove("text-highlight");
      void this.syncPreviewText.offsetWidth; // Trigger reflow to restart animation
      this.syncPreviewText.classList.add("text-highlight");
    }
  }
}

// Initialize after DOM is fully loaded
document.addEventListener("DOMContentLoaded", function () {
  console.log("DOM loaded, checking for app instance");
  // Wait for app to be initialized
  const initAudioManager = function () {
    if (
      window.faceSequencerApp &&
      window.faceSequencerApp.init &&
      typeof window.faceSequencerApp.updateTimeline === "function"
    ) {
      console.log("App found and fully initialized, initializing AudioManager");
      try {
        window.faceSequencerApp.audioManager = new AudioManager(
          window.faceSequencerApp
        );
      } catch (error) {
        console.error("Error initializing AudioManager:", error);
        setTimeout(initAudioManager, 1000); // Retry after 1 second
      }
    } else {
      console.log("App not found or not fully initialized yet, waiting...");
      setTimeout(initAudioManager, 500);
    }
  };

  // Start initialization with a slight delay to ensure app is ready
  setTimeout(initAudioManager, 500);
});
