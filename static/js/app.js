// app.js - Face Sequencer Pro Frontend Application
class FaceSequencerApp {
  constructor() {
    this.state = {
      project: {
        name: "Untitled Project",
        folder_path: "",
        fallback_image: "",
        space_image: null,
        text: "",
        letter_map: {},
        sequence: [],
        settings: {
          frame_duration: 80,
          pause_duration: 120,
          fps: 30,
          quality: 14,
          preset: "medium",
        },
      },
      sequence: [], // Ensure sequence is initialized at both levels
      mappings: {},
      currentFrame: 0,
      playing: false,
      exportTask: null,
      syncPlaybackActive: false,
      syncAnimationFrameTimer: null,
    };

    this.previewInterval = null;
    // Internal drag & drop visuals
    this._dragFileActive = false;
    this._dragCounter = 0; // helps manage nested dragenter/dragleave
    this.dragGhostEl = null;
    this.ariaStatusRegion = null;
    this.ariaAlertRegion = null;
    this.init();
  }

  init() {
    this.initializeElements();
    this.bindEvents();
    this.loadProject();
    this.generateMappingGrid();
    this.updateUI();
    this.initDragVisualFeedback();
    this.initAriaRegions();
    this.initLocalization();

    // Make sure sequences are in sync
    this.syncSequenceState();

    // Audio manager will be initialized by audio.js
    this.audioManager = null;

    // Initialize synchronized playback
    this.initSyncPlayback();

    // Initialize enhanced alignment features
    this.initEnhancedAlignment();
    // Timeline enhancer (after DOM present)
    if (window.TimelineEnhancer) {
      this.timelineEnhancer = new TimelineEnhancer(this);
    }
  }

  initializeElements() {
    // Text input elements
    this.textInput = document.getElementById("textInput");
    this.charCount = document.getElementById("charCount");
    this.mappingStatus = document.getElementById("mappingStatus");

    // Folder elements
    this.folderPath = document.getElementById("folderPath");
    this.browseFolderBtn = document.getElementById("browseFolderBtn");
    this.scanFolderBtn = document.getElementById("scanFolderBtn");
    this.folderInput = document.getElementById("folderInput");

    // Settings elements
    this.frameDuration = document.getElementById("frameDuration");
    this.pauseDuration = document.getElementById("pauseDuration");
    this.fps = document.getElementById("fps");
    this.quality = document.getElementById("quality");

    // Enhanced alignment elements
    this.useEnhancedAlignment = document.getElementById("useEnhancedAlignment");
    this.alignmentMethod = document.getElementById("alignmentMethod");
    this.targetFps = document.getElementById("targetFps");
    this.enhancementStatus = document.getElementById("enhancementStatus");
    this.alignmentMethodContainer = document.getElementById(
      "alignmentMethodContainer"
    );
    this.targetFpsContainer = document.getElementById("targetFpsContainer");

    // Audio text-driven toggle
    this.audioTextDrivenToggle = document.getElementById(
      "audioTextDrivenToggle"
    );

    // Fallback elements
    this.fallbackPreview = document.getElementById("fallbackPreview");
    this.chooseFallbackBtn = document.getElementById("chooseFallbackBtn");
    this.imageInput = document.getElementById("imageInput");

    // Space image elements
    this.spacePreview = document.getElementById("spacePreview");
    this.chooseSpaceBtn = document.getElementById("chooseSpaceBtn");
    this.clearSpaceBtn = document.getElementById("clearSpaceBtn");
    this.spaceImageInput = document.createElement("input");
    this.spaceImageInput.type = "file";
    this.spaceImageInput.accept = "image/*";
    this.spaceImageInput.style.display = "none";
    document.body.appendChild(this.spaceImageInput);

    // Action buttons
    this.buildSequenceBtn = document.getElementById("buildSequenceBtn");
    this.previewBtn = document.getElementById("previewBtn");
    this.testModeBtn = document.getElementById("testModeBtn");

    // Mapping elements
    this.mappingGrid = document.getElementById("mappingGrid");
    this.autoMapBtn = document.getElementById("autoMapBtn");
    this.clearMappingBtn = document.getElementById("clearMappingBtn");

    // Timeline elements
    this.previewFrame = document.getElementById("previewFrame");
    this.timelineFrames = document.getElementById("timelineFrames");
    this.timelineInfo = document.getElementById("timelineInfo");
    this.playBtn = document.getElementById("playBtn");
    this.stopBtn = document.getElementById("stopBtn");
    this.scrubberHandle = document.getElementById("scrubberHandle");

    // Frame editor elements
    this.frameEditor = document.getElementById("frameEditor");
    this.selectedFrameDuration = document.getElementById(
      "selectedFrameDuration"
    );
    this.duplicateFrameBtn = document.getElementById("duplicateFrameBtn");
    this.deleteFrameBtn = document.getElementById("deleteFrameBtn");

    // Export elements
    this.exportModal = document.getElementById("exportModal");
    this.exportVideoBtn = document.getElementById("exportVideo");
    this.closeExportModal = document.getElementById("closeExportModal");
    this.confirmExportBtn = document.getElementById("confirmExportBtn");
    this.cancelExportBtn = document.getElementById("cancelExportBtn");

    // Project elements
    this.saveProjectBtn = document.getElementById("saveProject");
    this.loadProjectBtn = document.getElementById("loadProject");
    this.projectInput = document.getElementById("projectInput");

    // Status elements
    this.statusMessage = document.getElementById("statusMessage");
    this.progressContainer = document.getElementById("progressContainer");
    this.progressFill = document.getElementById("progressFill");
    this.progressText = document.getElementById("progressText");
  }

  bindEvents() {
    // Text input events
    this.textInput.addEventListener("input", () => {
      this.state.project.text = this.textInput.value;
      this.updateCharCount();
      this.validateMappings();
    });

    // Folder events
    this.browseFolderBtn.addEventListener("click", () => {
      this.folderInput.click();
    });

    this.folderInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        // Get the folder path from the first file
        const fullRelPath = e.target.files[0].webkitRelativePath; // e.g. ImagesSet/A.png
        const topFolder = fullRelPath.split("/")[0];
        console.log("Selected folder (top-level):", topFolder);
        console.log("First file relative path:", fullRelPath);
        this.folderPath.value = topFolder;
        this.state.project.folder_path = topFolder; // store logical folder token

        // Show success message
        this.showStatus(`Folder selected: ${topFolder}`);
      }
    });

    // Manual folder path input
    this.folderPath.addEventListener("input", () => {
      this.state.project.folder_path = this.folderPath.value;
    });

    this.scanFolderBtn.addEventListener("click", () => {
      this.scanFolder();
    });

    if (this.audioTextDrivenToggle) {
      this.audioTextDrivenToggle.addEventListener("change", () => {
        this.state.project.audio_text_driven =
          this.audioTextDrivenToggle.checked;
      });
      // default ON
      this.audioTextDrivenToggle.checked = true;
      this.state.project.audio_text_driven = true;
    }

    // Settings events
    this.frameDuration.addEventListener("change", () => {
      this.state.project.settings.frame_duration = parseInt(
        this.frameDuration.value
      );
    });

    this.pauseDuration.addEventListener("change", () => {
      this.state.project.settings.pause_duration = parseInt(
        this.pauseDuration.value
      );
    });

    this.fps.addEventListener("change", () => {
      this.state.project.settings.fps = parseInt(this.fps.value);
    });

    this.quality.addEventListener("change", () => {
      this.state.project.settings.quality = parseInt(this.quality.value);
    });

    // Enhanced alignment events
    this.useEnhancedAlignment?.addEventListener("change", () => {
      this.toggleEnhancedAlignmentSettings();
    });

    this.alignmentMethod?.addEventListener("change", () => {
      this.state.project.settings.alignmentMethod = this.alignmentMethod.value;
    });

    this.targetFps?.addEventListener("change", () => {
      this.state.project.settings.targetFps = parseInt(this.targetFps.value);
      // Sync with main FPS if enhanced is enabled
      if (this.useEnhancedAlignment?.checked) {
        this.fps.value = this.targetFps.value;
        this.state.project.settings.fps = parseInt(this.targetFps.value);
      }
    });

    // Fallback events
    this.chooseFallbackBtn.addEventListener("click", () => {
      this.imageInput.click();
    });

    this.imageInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        this.handleFallbackImage(e.target.files[0]);
      }
    });

    // Space image events
    this.chooseSpaceBtn.addEventListener("click", () => {
      this.spaceImageInput.click();
    });

    this.spaceImageInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        this.handleSpaceImage(e.target.files[0]);
      }
    });

    this.clearSpaceBtn.addEventListener("click", () => {
      this.clearSpaceImage();
    });

    // Action events
    this.buildSequenceBtn.addEventListener("click", () => {
      this.buildSequence();
    });

    this.previewBtn.addEventListener("click", () => {
      this.togglePreview();
    });

    this.testModeBtn.addEventListener("click", () => {
      this.enableTestMode();
    });

    // Mapping events
    this.autoMapBtn.addEventListener("click", () => {
      this.autoMapCharacters();
    });

    this.clearMappingBtn.addEventListener("click", () => {
      this.clearMappings();
    });

    // Bulk import & drag help
    this.bulkImportBtn = document.getElementById("bulkImportBtn");
    this.bulkImportInput = document.getElementById("bulkImportInput");
    this.showDragHelpBtn = document.getElementById("showDragHelpBtn");
    if (this.bulkImportBtn && this.bulkImportInput) {
      this.bulkImportBtn.addEventListener("click", () =>
        this.bulkImportInput.click()
      );
      this.bulkImportInput.addEventListener("change", (e) => {
        if (e.target.files?.length) {
          const files = Array.from(e.target.files).filter((f) =>
            this.isImageFile(f)
          );
          if (files.length) {
            this.processBatchMapping(files).then(() => {
              this.showSuccess(`${files.length} images imported.`);
              this.announceStatus(
                `${files.length} images imported successfully.`
              );
            });
          } else {
            this.showError("No supported image files selected");
            this.announceAlert("No supported image files selected");
          }
          this.bulkImportInput.value = "";
        }
      });
    }
    if (this.showDragHelpBtn) {
      this.showDragHelpBtn.addEventListener("click", () => {
        localStorage.removeItem("dragOnboardingShown");
        const banner = document.getElementById("dragOnboardingBanner");
        if (banner) {
          banner.style.display = "flex";
          banner.setAttribute("aria-hidden", "false");
        }
        this.showDragHelpBtn.style.display = "none";
      });
    }

    // Timeline events
    this.playBtn.addEventListener("click", () => {
      this.playSequence();
    });

    this.stopBtn.addEventListener("click", () => {
      this.stopSequence();
    });

    // Timeline scrubber events
    this.setupTimelineScrubber();

    // Frame editor events
    this.selectedFrameDuration.addEventListener("change", () => {
      this.updateFrameDuration();
    });

    this.duplicateFrameBtn.addEventListener("click", () => {
      this.duplicateFrame();
    });

    this.deleteFrameBtn.addEventListener("click", () => {
      this.deleteFrame();
    });

    // Export events
    this.exportVideoBtn.addEventListener("click", () => {
      this.showExportModal();
    });

    this.closeExportModal.addEventListener("click", () => {
      this.hideExportModal();
    });

    this.confirmExportBtn.addEventListener("click", () => {
      this.exportVideo();
    });

    this.cancelExportBtn.addEventListener("click", () => {
      this.hideExportModal();
    });

    // Project events
    this.saveProjectBtn.addEventListener("click", () => {
      this.saveProject();
    });

    this.loadProjectBtn.addEventListener("click", () => {
      this.projectInput.click();
    });

    this.projectInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        this.loadProject(e.target.files[0]);
      }
    });

    // Modal close on backdrop click
    this.exportModal.addEventListener("click", (e) => {
      if (e.target === this.exportModal) {
        this.hideExportModal();
      }
    });
  }

  // API Communication Methods
  async apiCall(endpoint, method = "GET", data = null) {
    const config = {
      method,
      headers: {
        "Content-Type": "application/json",
      },
      _retryAttempts: 2,
    };

    if (data && method !== "GET") {
      config.body = JSON.stringify(data);
    }

    try {
      const url = endpoint.startsWith("/api") ? endpoint : `/api${endpoint}`;
      const response = await fetch(url, config);
      const result = await response.json();
      if (!result.success) throw new Error(result.error || "API call failed");
      return result;
    } catch (error) {
      this.reportError(`API Error: ${error.message}`, {
        level: "error",
        action: () => this.apiCall(endpoint, method, data),
        actionLabel: "Retry",
      });
      throw error;
    }
  }

  // Project Management
  async loadProject(file = null) {
    try {
      if (file) {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch("/api/project/load", {
          method: "POST",
          body: formData,
        });

        const result = await response.json();
        if (result.success) {
          this.state.project = result.project;
          this.updateUI();
          this.showSuccess("Project loaded successfully");
        }
      } else {
        // No GET /api/project endpoint exists; skip silent fetch.
        // Optionally we could implement a backend endpoint to return current project state.
        console.warn("No direct /api/project fetch implemented (skipping)");
      }
    } catch (error) {
      this.showError("Failed to load project");
    }
  }

  async saveProject() {
    try {
      const filename = prompt(
        "Enter filename:",
        `${this.state.project.name}.json`
      );
      if (!filename) return;

      const response = await fetch("/api/project/save", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ filename }),
      });

      if (response.ok) {
        const blob = await response.blob();
        this.downloadFile(blob, filename);
        this.showSuccess("Project saved successfully");
      }
    } catch (error) {
      this.showError("Failed to save project");
    }
  }

  // Folder and Mapping Management
  async scanFolder() {
    try {
      // Fallback: if state not yet updated (race), pull current input value
      if (!this.state.project.folder_path) {
        const inputEl =
          this.folderPath || document.getElementById("folderPath");
        if (inputEl && inputEl.value && inputEl.value.trim()) {
          this.state.project.folder_path = inputEl.value.trim();
        }
      }
      if (!this.state.project.folder_path) {
        this.showError("Please select a folder first");
        return;
      }

      this.showStatus("Scanning folder...");
      // Allow user to type full absolute path manually; if only a simple name given, backend will treat as relative
      let scanPath = this.state.project.folder_path.trim();
      if (!scanPath) {
        this.showError("Folder path is empty");
        return;
      }
      const result = await this.apiCall("/folder/scan", "POST", {
        path: scanPath,
      });

      // Persist mappings
      this.state.mappings = result.mappings;

      // Capture fallback/space images discovered on the backend
      if (result.fallback_image_abs || result.fallback_image) {
        this.state.project.fallback_image =
          result.fallback_image_abs || result.fallback_image;
        if (result.fallback_thumb && this.fallbackPreview) {
          this.fallbackPreview.innerHTML = `<img src="${result.fallback_thumb}" alt="Fallback">`;
          this.fallbackPreview.classList.add("has-image");
        }
      }

      if (result.space_image_abs || result.space_image) {
        const spacePath = result.space_image_abs || result.space_image;
        this.state.project.space_image = spacePath;
        // Use the provided thumbnail for the space tile preview
        if (result.space_thumb) {
          this.state.project.letter_map[" "] = result.space_thumb;
        }
      } else {
        // Clear space mapping if none found
        delete this.state.project.letter_map[" "];
        this.state.project.space_image = null;
      }

      // Update grid and thumbnails after enhancing state
      this.updateMappingGrid();
      this.loadMappingThumbnails();
      this.validateMappings();

      this.showSuccess(
        `Mapped ${result.mapped_count}/${result.total_letters} characters`
      );
    } catch (error) {
      this.showError("Failed to scan folder");
    }
  }

  async loadMappingThumbnails() {
    try {
      const letters = Object.keys(this.state.mappings).filter(
        (letter) => this.state.mappings[letter].mapped
      );

      if (letters.length === 0) return;

      const result = await this.apiCall("/mapping/thumbnails", "POST", {
        letters,
      });

      // Update mapping grid with thumbnails
      Object.entries(result.thumbnails).forEach(([letter, thumbnail]) => {
        const item = document.querySelector(`[data-letter="${letter}"]`);
        if (item) {
          const preview = item.querySelector(".mapping-preview");
          preview.innerHTML = `<img src="${thumbnail}" alt="${letter}">`;
          item.classList.add("mapped");
        }
      });
    } catch (error) {
      console.error("Failed to load thumbnails:", error);
    }
  }

  // Sequence Management
  async buildSequence() {
    try {
      console.log("Current project state:", this.state.project);

      if (!this.state.project.text || this.state.project.text.trim() === "") {
        this.showError("Please enter text first");
        return;
      }

      this.showStatus("Building sequence...");

      // First update the project on the server
      console.log("Updating project on server...");
      await this.apiCall("/api/project", "POST", {
        text: this.state.project.text,
        settings: this.state.project.settings,
        name: this.state.project.name,
      });

      // Check if we're in audio-driven mode
      if (
        this.state.isAudioDriven &&
        this.audioManager &&
        this.audioManager.isAudioMode
      ) {
        // Use audio-driven sequence building
        console.log("Building sequence with audio timing...");
        return this.buildSequenceWithAudio();
      } else {
        // Use traditional sequence building
        console.log("Building sequence with manual timing...");
        const result = await this.apiCall("/api/sequence/build", "POST");

        this.state.project.sequence = result.sequence;
        this.state.sequence = result.sequence; // Sync both sequence locations
        this.updateTimeline();
        this.updateTimelineInfo();

        this.showSuccess(`Built sequence with ${result.total_frames} frames`);
      }
    } catch (error) {
      console.error("Build sequence error:", error);
      this.showError(`Failed to build sequence: ${error.message}`);
    }
  }

  async updateFrameDuration() {
    try {
      if (
        this.state.currentFrame < 0 ||
        this.state.currentFrame >= this.state.sequence.length
      ) {
        return;
      }

      const duration = parseInt(this.selectedFrameDuration.value);
      await this.apiCall("/sequence/update", "POST", {
        frame_id: this.state.currentFrame,
        updates: { duration },
      });

      // Update local state
      this.state.sequence[this.state.currentFrame].duration = duration;
      this.updateTimeline();
    } catch (error) {
      this.showError("Failed to update frame duration");
    }
  }

  async deleteFrame() {
    try {
      if (
        this.state.currentFrame < 0 ||
        this.state.currentFrame >= this.state.sequence.length
      ) {
        return;
      }

      await this.apiCall("/sequence/delete", "POST", {
        frame_id: this.state.currentFrame,
      });

      // Update local state
      this.state.sequence.splice(this.state.currentFrame, 1);
      this.state.currentFrame = Math.max(0, this.state.currentFrame - 1);
      this.updateTimeline();
      this.updateTimelineInfo();
      this.showSuccess("Frame deleted");
    } catch (error) {
      this.showError("Failed to delete frame");
    }
  }

  // Preview and Playback
  async playSequence() {
    this.syncSequenceState();
    if (!this.state.sequence || this.state.sequence.length === 0) {
      this.showError("No sequence to play");
      return;
    }

    this.state.playing = true;
    this.playBtn.innerHTML = '<i class="fas fa-pause"></i>';

    let frameIndex = this.state.currentFrame;

    const playFrame = async () => {
      if (!this.state.playing || frameIndex >= this.state.sequence.length) {
        this.stopSequence();
        return;
      }

      try {
        const result = await this.apiCall(`/sequence/frame/${frameIndex}`);

        if (result.is_pause) {
          this.showPauseFrame(result);
        } else {
          this.showFrameImage(result.image);
        }

        this.selectFrame(frameIndex);
        frameIndex++;

        // Get the frame duration - prefer ms property but fall back to duration if needed
        const frameDuration = result.ms ?? result.duration ?? 80;

        setTimeout(() => {
          if (this.state.playing) {
            playFrame();
          }
        }, frameDuration);
      } catch (error) {
        this.stopSequence();
        this.showError("Playback error");
      }
    };

    playFrame();
  }

  stopSequence() {
    this.state.playing = false;
    this.playBtn.innerHTML = '<i class="fas fa-play"></i>';
    if (this.previewInterval) {
      clearInterval(this.previewInterval);
      this.previewInterval = null;
    }
  }

  async togglePreview() {
    if (this.state.playing) {
      this.stopSequence();
    } else {
      this.playSequence();
    }
  }

  showFrameImage(imageSrc) {
    this.previewFrame.innerHTML = `<img src="${imageSrc}" alt="Preview">`;
  }

  showPauseFrame(frameData) {
    const duration = frameData.ms || frameData.duration || 0;
    this.previewFrame.innerHTML = `
            <div class="preview-placeholder pause-indicator">
                <i class="fas fa-pause"></i>
                <span>Pause (${duration}ms)</span>
            </div>
        `;
  }

  // Export Management
  showExportModal() {
    this.exportModal.style.display = "flex";
    this.exportModal.classList.add("fade-in");
  }

  hideExportModal() {
    this.exportModal.style.display = "none";
    this.exportModal.classList.remove("fade-in");
  }

  async exportVideo() {
    try {
      if (this.state.sequence.length === 0) {
        this.showError("No sequence to export");
        return;
      }

      const filename =
        document.getElementById("exportName").value || "sequence.mp4";
      const quality =
        document.getElementById("exportQuality").value || "medium";

      this.hideExportModal();
      this.showStatus("Starting video export...");

      const result = await this.apiCall("/export/video", "POST", {
        filename,
        quality,
      });

      this.state.exportTask = result.task_id;
      this.monitorExportProgress();
    } catch (error) {
      this.showError("Failed to start export");
    }
  }

  async monitorExportProgress() {
    // Create or update progress modal
    if (!this.exportProgressModal) {
      this.exportProgressModal = document.createElement("div");
      this.exportProgressModal.className = "modal progress-modal";
      this.exportProgressModal.innerHTML = `
        <div class="modal-content">
          <h2>Exporting Video</h2>
          <div class="progress-container">
            <div class="progress-bar">
              <div class="progress-fill"></div>
            </div>
            <div class="progress-text">0%</div>
          </div>
          <div class="progress-message">Starting export...</div>
          <div class="progress-actions">
            <button class="btn btn-secondary cancel-export-btn">Cancel</button>
          </div>
        </div>
      `;
      document.body.appendChild(this.exportProgressModal);

      // Add event listener for cancel button
      const cancelBtn =
        this.exportProgressModal.querySelector(".cancel-export-btn");
      if (cancelBtn) {
        cancelBtn.addEventListener("click", () => {
          // We can't actually cancel the export, but we can stop monitoring
          this.hideExportProgressModal();
          this.showStatus("Export continues in background");
        });
      }
    }

    // Show the modal
    this.exportProgressModal.style.display = "flex";

    // Close any existing SSE connections for this task
    if (window.sseClient) {
      window.sseClient.unsubscribe(this.state.exportTask, "export_progress");
    }

    // Handler for SSE updates
    const handleProgressUpdate = (data) => {
      // Update progress bar and message
      const progressFill =
        this.exportProgressModal.querySelector(".progress-fill");
      const progressText =
        this.exportProgressModal.querySelector(".progress-text");
      const progressMessage =
        this.exportProgressModal.querySelector(".progress-message");

      if (progressFill && progressText) {
        const progress = data.progress || 0;
        progressFill.style.width = `${progress}%`;
        progressText.textContent = `${progress}%`;

        if (progressMessage && data.message) {
          progressMessage.textContent = data.message;
        }

        // Update visual state based on status
        if (data.status === "error") {
          progressFill.classList.add("error");
          progressMessage.classList.add("error");
        } else {
          progressFill.classList.remove("error");
          progressMessage.classList.remove("error");
        }
      }

      // Handle completed or error states
      if (data.status === "completed") {
        // Handle completion just like before
        this.handleExportCompletion();
      } else if (data.status === "error") {
        // Handle error state
        this.showError(`Export failed: ${data.error || "Unknown error"}`);

        // Change the cancel button to close
        const cancelBtn =
          this.exportProgressModal.querySelector(".cancel-export-btn");
        if (cancelBtn) {
          cancelBtn.textContent = "Close";
        }
      }
    };

    // Subscribe to SSE updates for this task
    if (window.sseClient) {
      window.sseClient.subscribe(
        this.state.exportTask,
        "export_progress",
        handleProgressUpdate
      );
    } else {
      // Fallback to polling if SSE client is not available
      this.pollExportProgress();
    }
  }

  // Fallback method using polling (called if SSE is not available)
  pollExportProgress() {
    const checkProgress = async () => {
      try {
        const result = await this.apiCall(
          `/export/status/${this.state.exportTask}`
        );
        const task = result.task;

        if (task.status === "processing") {
          // Update progress bar and message
          const progressFill =
            this.exportProgressModal.querySelector(".progress-fill");
          const progressText =
            this.exportProgressModal.querySelector(".progress-text");
          const progressMessage =
            this.exportProgressModal.querySelector(".progress-message");

          if (progressFill && progressText) {
            const progress = task.progress || 0;
            progressFill.style.width = `${progress}%`;
            progressText.textContent = `${progress}%`;

            if (progressMessage && task.message) {
              progressMessage.textContent = task.message;
            }
          }

          setTimeout(checkProgress, 1000);
        } else if (task.status === "completed") {
          // Use the centralized method for handling export completion
          this.handleExportCompletion();
        } else if (task.status === "error") {
          // Update modal to show error
          const progressMessage =
            this.exportProgressModal.querySelector(".progress-message");
          if (progressMessage) {
            progressMessage.textContent = `Error: ${
              task.error || "Unknown error"
            }`;
            progressMessage.style.color = "red";
          }

          // Change the cancel button to close
          const cancelBtn =
            this.exportProgressModal.querySelector(".cancel-export-btn");
          if (cancelBtn) {
            cancelBtn.textContent = "Close";
          }

          this.showError(`Export failed: ${task.error}`);
        }
      } catch (error) {
        this.hideExportProgressModal();
        this.showError("Failed to check export progress");
      }
    };

    checkProgress();
  }

  hideExportProgressModal() {
    if (this.exportProgressModal) {
      this.exportProgressModal.style.display = "none";

      // Unsubscribe from SSE updates when hiding the modal
      if (window.sseClient && this.state.exportTask) {
        window.sseClient.unsubscribe(this.state.exportTask, "export_progress");
      }
    }
  }

  handleExportCompletion() {
    // Update modal to show validation
    const progressMessage =
      this.exportProgressModal.querySelector(".progress-message");
    if (progressMessage) {
      progressMessage.textContent = "Export completed. Validating file...";
    }

    // Validate the file before downloading
    this.validateAndDownloadExport();
  }

  async validateAndDownloadExport() {
    const progressMessage =
      this.exportProgressModal.querySelector(".progress-message");

    try {
      // First verify the export is valid
      const validateResponse = await this.apiCall(
        `/export/validate/${this.state.exportTask}`
      );

      if (validateResponse.success && validateResponse.valid) {
        // Update message to show validation success
        if (progressMessage) {
          progressMessage.textContent =
            "Export validated successfully! Starting download...";
        }

        // Auto-download after short delay
        setTimeout(() => {
          this.hideExportProgressModal();
          this.downloadExport();
        }, 1000);
      } else {
        // Show validation error
        if (progressMessage) {
          progressMessage.textContent = `Export validation failed: ${
            validateResponse.error || "Unknown error"
          }`;
          progressMessage.style.color = "red";
        }

        // Change the cancel button to retry
        const cancelBtn =
          this.exportProgressModal.querySelector(".cancel-export-btn");
        if (cancelBtn) {
          cancelBtn.textContent = "Close";
        }

        // Add a retry button if it doesn't exist
        this.addRetryExportButton();
      }
    } catch (validateError) {
      console.error("Export validation error:", validateError);
      // Continue with download anyway
      setTimeout(() => {
        this.hideExportProgressModal();
        this.downloadExport();
      }, 1000);
    }
  }

  addRetryExportButton() {
    const actionsDiv =
      this.exportProgressModal.querySelector(".progress-actions");
    if (actionsDiv && !actionsDiv.querySelector(".retry-export-btn")) {
      const retryBtn = document.createElement("button");
      retryBtn.className = "btn btn-primary retry-export-btn";
      retryBtn.textContent = "Retry Export";
      retryBtn.addEventListener("click", () => {
        this.hideExportProgressModal();
        this.exportVideo();
      });
      actionsDiv.appendChild(retryBtn);
    }
  }

  async downloadExport() {
    try {
      // Show status while fetching
      this.showStatus("Downloading exported file...");

      // Create a unique timestamp to prevent caching issues
      const timestamp = new Date().getTime();
      const downloadUrl = `/api/export/download/${this.state.exportTask}?t=${timestamp}`;

      console.log(
        `Starting download for task: ${this.state.exportTask} via URL: ${downloadUrl}`
      );

      // Try direct browser download first (this often works better for binary files)
      try {
        // Create a hidden link and click it (direct download approach)
        const link = document.createElement("a");
        link.href = downloadUrl;
        link.download = "export.mp4"; // This will be overridden by Content-Disposition
        link.target = "_blank"; // Open in new tab/window
        link.style.display = "none";
        document.body.appendChild(link);

        console.log("Triggering direct download...");
        link.click();

        // Give browser time to start the download
        await new Promise((resolve) => setTimeout(resolve, 1000));

        document.body.removeChild(link);

        // Assume download started successfully
        this.showSuccess("Download started! Check your downloads folder.");
        return;
      } catch (directError) {
        console.warn(
          "Direct download approach failed, falling back to fetch API",
          directError
        );
      }

      // Fallback to fetch API if direct download fails
      const response = await fetch(downloadUrl, {
        method: "GET",
        cache: "no-cache",
        headers: {
          Accept: "video/mp4,application/octet-stream",
        },
      });

      console.log(
        "Fetch response status:",
        response.status,
        response.statusText
      );

      if (response.ok) {
        console.log("Response is OK, getting blob...");
        const blob = await response.blob();
        console.log(`Got blob: type=${blob.type}, size=${blob.size} bytes`);

        // Check if the blob is valid
        if (!blob || blob.size === 0) {
          this.showError("The exported file is empty or corrupted");
          return;
        }

        // Check if the blob type is correct, but be more lenient with MIME types
        if (
          !blob.type.includes("video/") &&
          !blob.type.includes("mp4") &&
          !blob.type.includes("octet-stream")
        ) {
          console.warn(
            `Unexpected blob type: ${blob.type} (size: ${blob.size} bytes), continuing anyway`
          );
        }

        // Get filename from headers or use default
        let filename = response.headers
          .get("Content-Disposition")
          ?.split("filename=")[1];
        if (filename) {
          filename = filename.replace(/["']/g, "");
        } else {
          filename = "export.mp4";
        }

        console.log(`Using filename: ${filename}`);
        this.downloadFile(blob, filename);
        this.showSuccess("Video exported successfully");
      } else {
        // Parse error response
        try {
          // Try to get the text response first
          const responseText = await response.text();
          console.error(`Error response text: ${responseText}`);

          try {
            // Try to parse as JSON
            const errorData = JSON.parse(responseText);
            this.showError(
              `Export error: ${errorData.error || "Unknown error"}`
            );
          } catch (jsonError) {
            // Not JSON, use the text directly
            this.showError(
              `Export error: ${responseText || response.statusText}`
            );
          }
        } catch (textError) {
          this.showError(
            `Export failed with status ${response.status}: ${response.statusText}`
          );
        }
      }
    } catch (error) {
      console.error("Download export error:", error);
      this.showError(
        `Failed to download export: ${error.message || "Unknown error"}`
      );
    }
  }

  // UI Update Methods
  updateUI() {
    // Ensure state is in sync
    this.syncSequenceState();

    // Update form fields
    this.textInput.value = this.state.project.text;
    // Race guard: avoid clobbering a user-typed folder path if state not yet populated
    // Scenario: init() triggers loadProject() (async) then updateUI() runs immediately while
    // user (or automated test) is typing the folder path. Original code overwrote the input
    // with an empty string, causing subsequent scanFolder() to early-exit and no thumbnails load.
    // Fix: Only overwrite if (a) state has a non-empty folder_path OR (b) input currently empty.
    // Additionally, never overwrite while the input is focused and state folder_path is empty.
    const currentInputVal = this.folderPath.value;
    const statePath = this.state.project.folder_path || "";
    const folderInputFocused = document.activeElement === this.folderPath;
    if (
      // Allow overwrite when we actually have a state path
      (statePath && currentInputVal !== statePath) ||
      // Or when input is blank (no user data lost)
      (!currentInputVal && !folderInputFocused)
    ) {
      // Do not overwrite if user is actively typing and statePath is still empty
      if (!(folderInputFocused && !statePath)) {
        this.folderPath.value = statePath;
      }
    }
    this.frameDuration.value = this.state.project.settings.frame_duration;
    this.pauseDuration.value = this.state.project.settings.pause_duration;
    this.fps.value = this.state.project.settings.fps;
    this.quality.value = this.state.project.settings.quality;

    this.updateCharCount();
    this.validateMappings();
  }

  updateCharCount() {
    const count = this.state.project.text.length;
    this.charCount.textContent = `${count} character${count !== 1 ? "s" : ""}`;
  }

  validateMappings() {
    const text = this.state.project.text.toUpperCase();
    const uniqueChars = [...new Set(text.split("").filter((c) => c !== " "))];

    let mappedCount = 0;
    uniqueChars.forEach((char) => {
      if (this.state.mappings[char]?.mapped) {
        mappedCount++;
      }
    });

    if (uniqueChars.length === 0) {
      this.mappingStatus.textContent = "Ready";
      this.mappingStatus.className = "mapping-status";
    } else if (mappedCount === uniqueChars.length) {
      this.mappingStatus.textContent = "All Mapped";
      this.mappingStatus.className = "mapping-status";
    } else {
      this.mappingStatus.textContent = `${mappedCount}/${uniqueChars.length} Mapped`;
      this.mappingStatus.className = "mapping-status warning";
    }
  }

  generateMappingGrid() {
    this.mappingGrid.innerHTML = "";

    // Generate regular letter mappings A-Z
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").forEach((letter) => {
      const item = document.createElement("div");
      item.className = "mapping-item";
      item.setAttribute("data-letter", letter);

      item.innerHTML = `
                <div class="mapping-char">${letter}</div>
                <div class="mapping-preview">
                    <i class="fas fa-image"></i>
                </div>
                <div class="mapping-status-icon missing" style="display: none;">
                    <i class="fas fa-exclamation"></i>
                </div>
            `;

      // Add drag and drop functionality
      this.setupDragAndDrop(item, letter);

      // Add click to browse functionality
      item.addEventListener("click", () => {
        this.selectImageForLetter(letter);
      });

      this.mappingGrid.appendChild(item);
    });

    // Add special space mapping item
    const spaceItem = document.createElement("div");
    spaceItem.className = "mapping-item space-item";
    spaceItem.setAttribute("data-letter", " ");

    spaceItem.innerHTML = `
            <div class="mapping-char">SPACE</div>
            <div class="mapping-preview">
                <i class="fas fa-square"></i>
            </div>
            <div class="mapping-status-icon" style="display: none;">
                <i class="fas fa-check"></i>
            </div>
        `;

    // Add drag and drop functionality for space
    this.setupDragAndDrop(spaceItem, " ");

    // Add click to browse functionality for space
    spaceItem.addEventListener("click", () => {
      this.spaceImageInput.click();
    });

    this.mappingGrid.appendChild(spaceItem);
  }

  setupDragAndDrop(item, letter) {
    // Enhanced drag enter
    item.addEventListener("dragenter", (e) => {
      e.preventDefault();
      if (this._isFileDrag(e)) {
        item.classList.add("drop-zone-active");
      }
    });

    // Drag over handler (required to allow drop)
    item.addEventListener("dragover", (e) => {
      e.preventDefault();
      if (this._isFileDrag(e)) {
        item.classList.add("drop-zone-active");
      }
    });

    // Drag leave handler
    item.addEventListener("dragleave", (e) => {
      if (!item.contains(e.relatedTarget)) {
        item.classList.remove("drop-zone-active");
      }
    });

    // Drop handler
    item.addEventListener("drop", (e) => {
      e.preventDefault();
      item.classList.remove("drop-zone-active");
      item.classList.remove("drag-over");

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        const imageFiles = Array.from(files).filter((f) => this.isImageFile(f));
        if (imageFiles.length === 0) {
          this.triggerDropError(
            item,
            "Unsupported file type. Use JPG, PNG, WEBP, BMP."
          );
        } else {
          // First image goes to the explicit letter
          this.assignImageToLetter(letter, imageFiles[0], item);
          // Remaining images auto-map to next unmapped letters
          if (imageFiles.length > 1) {
            const remaining = imageFiles.slice(1);
            const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
            let startIndex = letters.indexOf(letter) + 1;
            remaining.forEach((f) => {
              const targetLetter = letters
                .slice(startIndex)
                .find((L) => !this.state.mappings[L]?.mapped);
              if (targetLetter) {
                this.assignImageToLetter(targetLetter, f);
                startIndex = letters.indexOf(targetLetter) + 1;
              }
            });
            this.announceStatus(
              `${imageFiles.length} images mapped starting at ${letter}.`
            );
          } else {
            this.announceStatus(`Image mapped to letter ${letter}.`);
          }
        }
      }
      this.hideDragGhost();
    });

    // Ensure we don't treat mapping tiles as draggable sources currently
    item.setAttribute("draggable", "false");
  }

  selectImageForLetter(letter) {
    // Create temporary file input for this specific letter
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = (e) => {
      if (e.target.files.length > 0) {
        this.assignImageToLetter(letter, e.target.files[0]);
      }
    };
    input.click();
  }

  async assignImageToLetter(letter, file, targetItem = null) {
    return new Promise((resolve, reject) => {
      try {
        const reader = new FileReader();
        reader.onload = (e) => {
          const item =
            targetItem || document.querySelector(`[data-letter="${letter}"]`);
          if (item) {
            const preview = item.querySelector(".mapping-preview");
            preview.innerHTML = `<img src="${e.target.result}" alt="${letter}">`;
            item.classList.add("mapped");
            item.classList.remove("missing");
            const statusIcon = item.querySelector(".mapping-status-icon");
            if (statusIcon) statusIcon.style.display = "none";
            this.triggerDropSuccess(item);
          }
          if (!this.state.mappings[letter]) this.state.mappings[letter] = {};
          this.state.mappings[letter].mapped = true;
          this.state.mappings[letter].filename = file.name;
          this.validateMappings();
          this.showSuccess(`Assigned image to letter ${letter}`);
          this.announceStatus(`Assigned image to letter ${letter}`);
          resolve();
        };
        reader.onerror = () => {
          this.showError(`Failed to read file for ${letter}`);
          this.announceAlert(`File read failed for ${letter}`);
          reject(reader.error);
        };
        reader.readAsDataURL(file);
      } catch (err) {
        this.showError(`Failed to assign image: ${err.message}`);
        this.announceAlert(`Failed to assign image for letter ${letter}`);
        reject(err);
      }
    });
  }

  /* ---------------- Drag Visual Feedback Helpers ---------------- */
  initDragVisualFeedback() {
    // Create ghost element once
    this.dragGhostEl = document.createElement("div");
    this.dragGhostEl.className = "drag-ghost";
    this.dragGhostEl.innerHTML = '<i class="fas fa-file-image"></i>';
    document.body.appendChild(this.dragGhostEl);

    // Window-level drag events to manage ghost visibility
    window.addEventListener("dragenter", (e) => {
      if (this._isFileDrag(e)) {
        this._dragCounter++;
        this._dragFileActive = true;
        this.showDragGhost();
      }
    });

    window.addEventListener("dragover", (e) => {
      if (this._dragFileActive) {
        this.positionDragGhost(e);
      }
    });

    window.addEventListener("dragleave", (e) => {
      // Manage nested dragenter/leaves
      if (this._isFileDrag(e)) {
        this._dragCounter--;
        if (this._dragCounter <= 0) {
          this.resetDragState();
        }
      }
    });

    window.addEventListener("drop", () => {
      this.resetDragState();
    });
  }

  _isFileDrag(e) {
    return (
      e?.dataTransfer?.types &&
      Array.from(e.dataTransfer.types).includes("Files")
    );
  }

  positionDragGhost(e) {
    if (!this.dragGhostEl) return;
    this.dragGhostEl.style.top = `${e.clientY}px`;
    this.dragGhostEl.style.left = `${e.clientX}px`;
  }

  showDragGhost() {
    if (this.dragGhostEl) {
      this.dragGhostEl.classList.add("visible");
    }
    this.maybeShowDragOnboardingBanner();
  }

  hideDragGhost() {
    if (this.dragGhostEl) {
      this.dragGhostEl.classList.remove("visible");
    }
  }

  resetDragState() {
    this._dragFileActive = false;
    this._dragCounter = 0;
    this.hideDragGhost();
    // Clean any active highlight still lingering
    document
      .querySelectorAll(".mapping-item.drop-zone-active")
      .forEach((el) => el.classList.remove("drop-zone-active"));
  }

  triggerDropSuccess(item) {
    if (!item) return;
    item.classList.remove("drop-error");
    item.classList.add("drop-success");

    // Add transient check icon
    const indicator = document.createElement("div");
    indicator.className = "drop-success-indicator";
    indicator.innerHTML = '<i class="fas fa-check"></i>';
    item.appendChild(indicator);

    const cleanup = () => {
      item.classList.remove("drop-success");
      indicator.remove();
      item.removeEventListener("animationend", cleanup);
    };
    item.addEventListener("animationend", cleanup);
  }

  triggerDropError(item, message) {
    if (message) this.showError(message);
    if (!item) return;
    item.classList.remove("drop-success");
    item.classList.add("drop-error");
    // Inline hint
    if (!item.querySelector(".drop-error-hint")) {
      const hint = document.createElement("div");
      hint.className = "drop-error-hint";
      hint.innerHTML = `<i class=\"fas fa-exclamation-triangle\"></i><span>${message}</span>`;
      item.appendChild(hint);
      setTimeout(() => hint.remove(), 3600);
    }
    this.announceAlert(message);
    const cleanup = () => {
      item.classList.remove("drop-error");
      item.removeEventListener("animationend", cleanup);
    };
    item.addEventListener("animationend", cleanup);
  }

  async processBatchMapping(files, startAfterLetter = null) {
    const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
    let pointer = 0;
    if (startAfterLetter && letters.includes(startAfterLetter)) {
      pointer = letters.indexOf(startAfterLetter) + 1;
    }
    const imageFiles = files.filter((f) => this.isImageFile(f));
    if (!imageFiles.length) return;
    const total = imageFiles.length;
    this.showStatus(`Starting bulk import of ${total} images...`);
    this.announceStatus(`Bulk import started with ${total} images`);
    let mapped = 0;
    for (const file of imageFiles) {
      const targetLetter =
        letters.slice(pointer).find((L) => !this.state.mappings[L]?.mapped) ||
        letters.find((L) => L);
      if (!targetLetter) break;
      await this.assignImageToLetter(targetLetter, file);
      mapped++;
      pointer = letters.indexOf(targetLetter) + 1;
      if (total > 3) {
        this.announceStatus(`(${mapped}/${total}) mapped to ${targetLetter}`);
      }
    }
    this.showSuccess(`Bulk import complete (${mapped}/${total})`);
    this.announceStatus(`Bulk import complete. ${mapped} images mapped.`);
  }

  /* ---------------- Localization ---------------- */
  initLocalization() {
    this.translations = {
      en: {
        drag_banner_text:
          "Drag one or multiple image files from your computer and drop them onto the character tiles to map them. The first file goes to the tile you drop on; the rest will auto-fill the next unmapped letters.",
        drag_help_btn: "Drag Help",
        bulk_import_btn: "Bulk Import",
        auto_map_btn: "Auto Map",
        clear_all_btn: "Clear All",
        ui_language_heading: "Interface Language",
      },
      "pt-BR": {
        drag_banner_text:
          "Arraste um ou vários arquivos de imagem do seu computador e solte sobre os blocos de caracteres para mapeá-los. O primeiro arquivo vai para o bloco onde você soltar; os demais preencherão automaticamente as próximas letras não mapeadas.",
        drag_help_btn: "Ajuda de Arrastar",
        bulk_import_btn: "Importar em Lote",
        auto_map_btn: "Mapear Auto",
        clear_all_btn: "Limpar Tudo",
        ui_language_heading: "Idioma da Interface",
      },
    };
    this.uiLanguageSelect = document.getElementById("uiLanguageSelect");
    const stored = localStorage.getItem("uiLanguage") || "en";
    if (this.uiLanguageSelect) {
      this.uiLanguageSelect.value = stored;
      this.uiLanguageSelect.addEventListener("change", () => {
        localStorage.setItem("uiLanguage", this.uiLanguageSelect.value);
        this.applyTranslations();
      });
    }
    this.applyTranslations();
    if (
      localStorage.getItem("dragOnboardingShown") === "1" &&
      this.showDragHelpBtn
    ) {
      this.showDragHelpBtn.style.display = "inline-flex";
    }
  }

  applyTranslations() {
    const lang = this.uiLanguageSelect?.value || "en";
    const dict = this.translations[lang] || this.translations["en"];
    document.querySelectorAll("[data-i18n-key]").forEach((el) => {
      const key = el.getAttribute("data-i18n-key");
      if (dict[key]) el.textContent = dict[key];
    });
  }

  /* ---------------- Accessibility & Onboarding ---------------- */
  initAriaRegions() {
    this.ariaStatusRegion = document.getElementById("ariaStatusRegion");
    this.ariaAlertRegion = document.getElementById("ariaAlertRegion");
  }
  announceStatus(msg) {
    if (this.ariaStatusRegion) {
      this.ariaStatusRegion.textContent = msg;
    }
  }
  announceAlert(msg) {
    if (this.ariaAlertRegion) {
      this.ariaAlertRegion.textContent = msg;
    }
  }

  maybeShowDragOnboardingBanner() {
    try {
      if (localStorage.getItem("dragOnboardingShown") === "1") return;
      const banner = document.getElementById("dragOnboardingBanner");
      if (!banner) return;
      if (banner.style.display === "none") {
        banner.style.display = "flex";
        banner.setAttribute("aria-hidden", "false");
        setTimeout(() => {
          if (banner.getAttribute("aria-hidden") !== "true") {
            banner.style.display = "none";
            banner.setAttribute("aria-hidden", "true");
            localStorage.setItem("dragOnboardingShown", "1");
          }
        }, 8000);
      }
    } catch (e) {}
  }

  isImageFile(file) {
    const allowedTypes = [
      "image/jpeg",
      "image/jpg",
      "image/png",
      "image/webp",
      "image/bmp",
    ];
    return allowedTypes.includes(file.type);
  }

  updateMappingGrid() {
    // Update regular letter mappings A-Z
    Object.entries(this.state.mappings).forEach(([letter, mapping]) => {
      const item = document.querySelector(`[data-letter="${letter}"]`);
      if (item) {
        const statusIcon = item.querySelector(".mapping-status-icon");

        if (mapping.mapped) {
          item.classList.add("mapped");
          item.classList.remove("missing");
          statusIcon.style.display = "none";
        } else {
          item.classList.add("missing");
          item.classList.remove("mapped");
          statusIcon.style.display = "flex";
        }
      }
    });

    // Update space mapping
    const spaceItem = document.querySelector(`[data-letter=" "]`);
    if (spaceItem) {
      const preview = spaceItem.querySelector(".mapping-preview");
      const statusIcon = spaceItem.querySelector(".mapping-status-icon");

      if (this.state.project.space_image) {
        spaceItem.classList.add("mapped");
        spaceItem.classList.remove("missing");
        statusIcon.style.display = "flex";
        statusIcon.classList.remove("missing");
        statusIcon.innerHTML = '<i class="fas fa-check"></i>';
        // Update preview with space image
        if (this.state.project.letter_map[" "]) {
          preview.innerHTML = `<img src="${this.state.project.letter_map[" "]}" alt="Space Image">`;
        }
      } else {
        spaceItem.classList.remove("mapped", "missing");
        statusIcon.style.display = "none";
        preview.innerHTML = '<i class="fas fa-square"></i>';
      }
    }
  }

  updateTimeline() {
    try {
      this.timelineFrames.innerHTML = "";
      // Precompute frame start times for ms -> frame mapping / playback line
      this.frameStartTimes = [];
      let cumulative = 0;
      this.state.sequence.forEach((frame, index) => {
        const frameElement = document.createElement("div");
        frameElement.className = `timeline-frame ${
          frame.is_pause ? "pause" : ""
        }`;
        frameElement.setAttribute("data-frame", index);
        const thumbnail = frame.is_pause
          ? '<div class="frame-thumbnail pause-frame">⏸</div>'
          : frame.thumbnail
          ? `<div class="frame-thumbnail"><img src="${frame.thumbnail}" alt="${frame.char}"></div>`
          : '<div class="frame-thumbnail"><i class="fas fa-image"></i></div>';
        frameElement.innerHTML = `
          ${thumbnail}
          <div class="frame-info">
            <div class="frame-char">${
              frame.char === " " ? "Space" : frame.char
            }</div>
            <div class="frame-duration">${frame.ms || frame.duration}ms</div>
          </div>
          <div class="frame-index">${index + 1}</div>`;
        frameElement.addEventListener("click", () => this.selectFrame(index));
        this.timelineFrames.appendChild(frameElement);
        this.frameStartTimes[index] = cumulative;
        cumulative +=
          frame.ms ||
          frame.duration ||
          this.state.project.settings.frame_duration;
      });
      if (this.timelineEnhancer) this.timelineEnhancer.refresh();
    } catch (err) {
      console.error("Timeline render failed", err);
      this.timelineFrames.innerHTML = `<div class="timeline-error">Timeline failed to render. <button class="btn btn-outline btn-sm" id="retryTimelineBtn">Retry</button></div>`;
      document
        .getElementById("retryTimelineBtn")
        ?.addEventListener("click", () => this.updateTimeline());
      this.reportError("Timeline rendering error", {
        action: () => this.updateTimeline(),
        actionLabel: "Retry Timeline",
      });
    }
  }

  selectFrame(index) {
    // Remove previous selection
    this.timelineFrames.querySelectorAll(".timeline-frame").forEach((el) => {
      el.classList.remove("selected");
    });

    // Select new frame
    const frameElement = this.timelineFrames.querySelector(
      `[data-frame="${index}"]`
    );
    if (frameElement) {
      frameElement.classList.add("selected");
      frameElement.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    this.state.currentFrame = index;

    // Update frame editor
    if (index >= 0 && index < this.state.sequence.length) {
      this.frameEditor.style.display = "block";
      const dur =
        this.state.sequence[index].ms ??
        this.state.sequence[index].duration ??
        0;
      this.selectedFrameDuration.value = Math.max(0, Number(dur));
    } else {
      this.frameEditor.style.display = "none";
    }

    // Load frame preview
    this.loadFramePreview(index);
    // Update playback line
    if (this.timelineEnhancer)
      this.timelineEnhancer.updatePlaybackPositionByFrame(index);
  }

  // Map millisecond offset to frame index using frameStartTimes (binary search)
  getFrameIndexForMs(ms) {
    if (!this.frameStartTimes) return 0;
    let lo = 0,
      hi = this.frameStartTimes.length - 1,
      ans = 0;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (this.frameStartTimes[mid] <= ms) {
        ans = mid;
        lo = mid + 1;
      } else {
        hi = mid - 1;
      }
    }
    return ans;
  }

  async loadFramePreview(index) {
    try {
      if (index < 0 || index >= this.state.sequence.length) return;
      const result = await this.apiCall(`/sequence/frame/${index}`);

      if (result.is_pause) {
        this.showPauseFrame(result);
      } else {
        this.showFrameImage(result.image);
      }
    } catch (error) {
      // Gracefully handle not-found during fast scrubs or missing assets
      console.warn("Failed to load frame preview:", error?.message || error);
    }
  }

  updateTimelineInfo() {
    const frameCount = this.state.sequence.length;
    const totalDuration = this.state.sequence.reduce(
      (sum, frame) => sum + (frame.ms || frame.duration || 0),
      0
    );

    this.timelineInfo.textContent = `${frameCount} frames (${(
      totalDuration / 1000
    ).toFixed(1)}s)`;
  }

  // Utility Methods
  downloadFile(blob, filename) {
    try {
      console.log(
        `Downloading file: ${filename} (${blob.size} bytes, type: ${blob.type})`
      );

      // Enhanced blob validation
      if (!blob) {
        this.showError("Invalid file data");
        return;
      }

      if (blob.size === 0) {
        this.showError("The exported file is empty");
        return;
      }

      // For MP4 files, do additional validation
      if (filename.toLowerCase().endsWith(".mp4")) {
        if (blob.size < 1024) {
          // Less than 1KB
          this.showError("The MP4 file is too small and may be corrupted");
          return;
        }

        // Be more lenient with MIME type checking
        const validMimeTypes = [
          "video/mp4",
          "video/",
          "mp4",
          "application/octet-stream",
          "application/mp4",
        ];

        const hasValidType = validMimeTypes.some((type) =>
          blob.type.toLowerCase().includes(type.toLowerCase())
        );

        if (!hasValidType) {
          console.warn(
            `Warning: MP4 file has unexpected MIME type: ${blob.type}. Will try to download anyway.`
          );
          // Continue anyway since the server already validated the file
        }
      }

      // Create object URL
      const url = URL.createObjectURL(blob);

      // Create and trigger download
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.target = "_self"; // Force same window
      document.body.appendChild(a);

      // Log and notify before click
      console.log("Initiating download...");
      this.showStatus(
        `Downloading ${filename}... (${(blob.size / 1024 / 1024).toFixed(
          2
        )} MB)`
      );

      // Trigger download
      a.click();

      // Clean up with a slightly longer timeout
      setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        // Show success message
        this.showSuccess(
          `File "${filename}" downloaded successfully (${(
            blob.size /
            1024 /
            1024
          ).toFixed(2)} MB)`
        );
      }, 500);
    } catch (error) {
      console.error("Download failed:", error);
      this.showError(
        `Failed to download file: ${error.message || "Unknown error"}`
      );
    }
  }

  showStatus(message) {
    this.statusMessage.textContent = message;
  }

  showSuccess(message) {
    this.showStatus(message);
    setTimeout(() => {
      this.showStatus("Ready");
    }, 3000);
  }

  showError(message) {
    this.showStatus(`Error: ${message}`);
    console.error(message);
  }

  showInfo(message) {
    this.showStatus(message);
    setTimeout(() => {
      this.showStatus("Ready");
    }, 3000);
  }

  showProgress(percent) {
    this.progressContainer.style.display = "flex";
    this.progressFill.style.width = `${percent}%`;
    if (this.progressText) {
      this.progressText.textContent = `${Math.round(percent)}%`;
    }
  }

  // Helper method to keep sequence state in sync
  syncSequenceState() {
    if (
      this.state &&
      this.state.project &&
      Array.isArray(this.state.project.sequence)
    ) {
      this.state.sequence = this.state.project.sequence;
    } else if (this.state) {
      // Ensure sequence exists at both levels
      this.state.sequence = this.state.sequence || [];
      if (!this.state.project) this.state.project = {};

      // Error toast manager (WP-UX-007)
      if (window.ErrorToastManager) {
        this.errorToasts = new window.ErrorToastManager();
      }
      this.state.project.sequence = this.state.project.sequence || [];
    }
    // Do not update progress here - this method is just for state sync
  }

  // Centralized error reporting -> toast + console + ARIA (WP-UX-007)
  reportError(message, options = {}) {
    console.error("[AppError]", message, options?.error || "");
    // ARIA assertive region if present
    try {
      const alertRegion = document.getElementById("ariaAlertRegion");
      if (alertRegion) {
        alertRegion.textContent =
          typeof message === "string"
            ? message
            : message?.toString?.() || "Error";
      }
    } catch (_) {}
    if (this.errorToasts) {
      this.errorToasts.show(message, {
        level: options.level || "error",
        action: options.action,
        actionLabel: options.actionLabel,
        autoDismiss: options.autoDismiss !== false,
      });
    } else if (window.alert) {
      alert(message);
    }
  }

  // Helper to validate a required input field and show inline errors
  validateRequiredInput(el, hintMessage = "This field is required") {
    if (!el) return true;
    const value = (el.value || "").trim();
    if (!value) {
      this.errorToasts?.fieldError(el, hintMessage);
      return false;
    } else {
      this.errorToasts?.clearFieldError(el);
      return true;
    }
  }

  // Generic FormData upload helper with retry & correlation (returns JSON)
  async uploadFormData(
    endpoint,
    formData,
    { attempts = 2, onProgress, actionLabel = "Retry Upload" } = {}
  ) {
    const correlationId = `fd-${Date.now().toString(36)}-${Math.random()
      .toString(36)
      .slice(2, 6)}`;
    window.ErrorInstrumentation?.record("upload.start", {
      endpoint,
      correlationId,
    });
    let lastErr;
    for (let i = 0; i < attempts; i++) {
      try {
        const resp = await fetch(endpoint, {
          method: "POST",
          body: formData,
          _retryAttempts: 1,
        });
        const json = await resp.json();
        if (!json.success)
          throw new Error(json.error || `Upload failed (${resp.status})`);
        window.ErrorInstrumentation?.record("upload.success", {
          endpoint,
          correlationId,
          attempt: i + 1,
        });
        return json;
      } catch (err) {
        lastErr = err;
        window.ErrorInstrumentation?.record("upload.retry", {
          endpoint,
          correlationId,
          attempt: i + 1,
          error: err.message,
        });
        if (i < attempts - 1)
          await new Promise((r) => setTimeout(r, 400 * (i + 1)));
      }
    }
    this.reportError(`Upload error: ${lastErr.message}`, {
      action: () =>
        this.uploadFormData(endpoint, formData, {
          attempts,
          onProgress,
          actionLabel,
        }),
      actionLabel,
    });
    window.ErrorInstrumentation?.record("upload.failure", {
      endpoint,
      correlationId,
      error: lastErr?.message,
    });
    throw lastErr;
  }

  hideProgress() {
    this.progressContainer.style.display = "none";
  }

  setupTimelineScrubber() {
    const scrubber = document.getElementById("timelineScrubber");
    let isDragging = false;

    // Create keyboard navigation hint below the timeline
    this.createKeyboardHint();

    const updateScrubberPosition = (clientX) => {
      const rect = scrubber.getBoundingClientRect();
      let percentage = Math.max(
        0,
        Math.min(1, (clientX - rect.left) / rect.width)
      );
      let frameIndex = 0;
      const seqLen = this.state.sequence?.length || 0;
      if (seqLen > 0) {
        if (this.timelineEnhancer?.snapEnabled) {
          // Convert percentage to ms using total duration
          if (!this.frameStartTimes) this.buildFrameStartTimes?.();
          const totalMs =
            (this.frameStartTimes?.[seqLen - 1] || 0) +
            (this.state.sequence[seqLen - 1].ms ||
              this.state.sequence[seqLen - 1].duration ||
              this.state.project.settings.frame_duration);
          let ms = percentage * totalMs;
          // Snap to nearest alignment token boundary if available
          const snapped = this.getNearestSnapMs(ms);
          ms = snapped;
          percentage = totalMs ? ms / totalMs : percentage;
          frameIndex = this.getFrameIndexForMs(ms);
        } else {
          frameIndex = Math.min(Math.floor(percentage * seqLen), seqLen - 1);
        }
      }
      this.scrubberHandle.style.left = `${percentage * 100}%`;
      if (
        frameIndex !== this.state.currentFrame &&
        frameIndex >= 0 &&
        frameIndex < seqLen
      ) {
        this.selectFrame(frameIndex);
        this.previewFrame.classList.add("loading");
        this.loadFramePreview(frameIndex);
        this.updateTimelineInfo(frameIndex);
        this.highlightTimelineFrame(frameIndex);
        setTimeout(() => this.previewFrame.classList.remove("loading"), 100);
      }
      return frameIndex;
    };

    // Helper: build frameStartTimes if missing
    this.buildFrameStartTimes = () => {
      this.frameStartTimes = [];
      let c = 0;
      (this.state.sequence || []).forEach((f, i) => {
        this.frameStartTimes[i] = c;
        c += f.ms || f.duration || this.state.project.settings.frame_duration;
      });
    };

    this.getFrameIndexForMs = (ms) => {
      if (!this.frameStartTimes) this.buildFrameStartTimes();
      const starts = this.frameStartTimes;
      let lo = 0,
        hi = starts.length - 1;
      let ans = 0;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (starts[mid] <= ms) {
          ans = mid;
          lo = mid + 1;
        } else hi = mid - 1;
      }
      return ans;
    };

    this.getNearestSnapMs = (ms) => {
      const tokens =
        this.alignmentTokens ||
        this.audioManager?.alignmentTokens ||
        this.app?.alignmentTokens ||
        [];
      if (Array.isArray(tokens) && tokens.length) {
        // Collect candidate boundaries (start_ms)
        let best = ms;
        let bestDiff = Infinity;
        // Binary search by assuming tokens sorted by start
        // Build array of starts lazily
        if (!this._tokenStartsCache) {
          this._tokenStartsCache = tokens
            .map((t) => t.start_ms ?? t.start ?? 0)
            .sort((a, b) => a - b);
        }
        const arr = this._tokenStartsCache;
        // Binary search nearest
        let lo = 0,
          hi = arr.length - 1;
        while (lo <= hi) {
          const mid = (lo + hi) >> 1;
          const v = arr[mid];
          if (v === ms) {
            best = v;
            bestDiff = 0;
            break;
          }
          if (v < ms) {
            if (ms - v < bestDiff) {
              best = v;
              bestDiff = ms - v;
            }
            lo = mid + 1;
          } else {
            if (v - ms < bestDiff) {
              best = v;
              bestDiff = v - ms;
            }
            hi = mid - 1;
          }
        }
        return best;
      }
      // Fallback numeric snapping
      const interval = this.timelineEnhancer?.snapIntervalMs || 40;
      return Math.round(ms / interval) * interval;
    };

    scrubber.addEventListener("mousedown", (e) => {
      // Stop any ongoing playback when manual seeking
      if (this.state.playing) {
        this.stopSequence();
      }

      // Start dragging and update position
      isDragging = true;
      updateScrubberPosition(e.clientX);

      // Add 'active' class for visual feedback
      this.scrubberHandle.classList.add("active");

      // Add active state to timeline scrubber
      scrubber.classList.add("active");

      // Prevent text selection while dragging
      e.preventDefault();
    });

    document.addEventListener("mousemove", (e) => {
      if (isDragging) {
        updateScrubberPosition(e.clientX);

        // Show frame position tooltip
        this.showFrameTooltip(this.state.currentFrame);
      }
    });

    document.addEventListener("mouseup", () => {
      if (isDragging) {
        // When mouse is released, make sure to load the final frame preview
        const frameIndex = parseInt(this.state.currentFrame);
        if (frameIndex >= 0 && frameIndex < this.state.sequence.length) {
          this.loadFramePreview(frameIndex);
        }

        // Hide tooltip
        this.hideFrameTooltip();

        // Remove active classes
        this.scrubberHandle.classList.remove("active");
        scrubber.classList.remove("active");
      }
      isDragging = false;
    });

    // Click to seek
    scrubber.addEventListener("click", (e) => {
      if (!isDragging) {
        // Stop any ongoing playback
        if (this.state.playing) {
          this.stopSequence();
        }

        const frameIndex = updateScrubberPosition(e.clientX);
        // Make sure to load the preview
        this.loadFramePreview(frameIndex);
      }
    });

    // Add keyboard navigation
    document.addEventListener("keydown", (e) => {
      // Only if we have a sequence and not in a text input
      if (
        this.state.sequence &&
        this.state.sequence.length > 0 &&
        !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)
      ) {
        let newFrameIndex = this.state.currentFrame;
        let jumpSize = 1; // Default jump size

        // Modify jump size with Shift key
        if (e.shiftKey) {
          jumpSize = 5; // Jump 5 frames when Shift is pressed
        } else if (e.ctrlKey || e.metaKey) {
          jumpSize = 10; // Jump 10 frames when Ctrl/Cmd is pressed
        }

        // Arrow keys for frame navigation
        if (e.key === "ArrowLeft") {
          // Previous frame(s)
          newFrameIndex = Math.max(0, this.state.currentFrame - jumpSize);
          this.showTemporaryNotification(
            `Frame: ${newFrameIndex + 1}/${this.state.sequence.length}`
          );
          e.preventDefault();
        } else if (e.key === "ArrowRight") {
          // Next frame(s)
          newFrameIndex = Math.min(
            this.state.sequence.length - 1,
            this.state.currentFrame + jumpSize
          );
          this.showTemporaryNotification(
            `Frame: ${newFrameIndex + 1}/${this.state.sequence.length}`
          );
          e.preventDefault();
        } else if (e.key === "Home") {
          // Go to first frame
          newFrameIndex = 0;
          this.showTemporaryNotification("First Frame");
          e.preventDefault();
        } else if (e.key === "End") {
          // Go to last frame
          newFrameIndex = this.state.sequence.length - 1;
          this.showTemporaryNotification("Last Frame");
          e.preventDefault();
        } else if (e.key === " ") {
          // Space bar toggles play/pause
          this.togglePreview();
          e.preventDefault();
        } else if (e.key === "p" || e.key === "P") {
          // Alternative play/pause key
          this.togglePreview();
          e.preventDefault();
        }

        // Update if the frame has changed
        if (newFrameIndex !== this.state.currentFrame) {
          // Add loading indicator
          this.previewFrame.classList.add("loading");

          // Update frame
          this.selectFrame(newFrameIndex);
          this.loadFramePreview(newFrameIndex);

          // Update scrubber position with animation
          const percentage = newFrameIndex / (this.state.sequence.length - 1);
          this.scrubberHandle.style.left = `${percentage * 100}%`;

          // Highlight the timeline frame
          this.highlightTimelineFrame(newFrameIndex);

          // Scroll timeline to ensure current frame is visible
          this.scrollTimelineToCurrentFrame();

          // Remove loading indicator after a short delay
          setTimeout(() => {
            this.previewFrame.classList.remove("loading");
          }, 100);
        }
      }
    });
  }

  createKeyboardHint() {
    // Create keyboard hint element if it doesn't exist
    if (!document.getElementById("keyboard-hint")) {
      const hintContainer = document.createElement("div");
      hintContainer.className = "keyboard-hint";
      hintContainer.innerHTML = `
        Navigation: <kbd>←</kbd><kbd>→</kbd> Frames | 
        <kbd>Home</kbd> First | <kbd>End</kbd> Last | 
        <kbd>Space</kbd> Play/Pause | 
        <kbd>Shift</kbd>+<kbd>←/→</kbd> Jump 5 frames
      `;

      // Use the element with class "timeline-container" instead of ID
      const timelineContainer = document.querySelector(".timeline-container");

      // Only append if the container exists
      if (timelineContainer) {
        timelineContainer.appendChild(hintContainer);
      } else {
        console.warn(
          "Timeline container not found. Keyboard hints will not be displayed."
        );
      }
    }
  }

  showTemporaryNotification(message) {
    // Create notification element if it doesn't exist
    let notification = document.getElementById("timeline-notification");
    if (!notification) {
      notification = document.createElement("div");
      notification.id = "timeline-notification";
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

      const timelineContainer = document.querySelector(".timeline-container");

      // Only proceed if we found the container
      if (timelineContainer) {
        timelineContainer.style.position = "relative";
        timelineContainer.appendChild(notification);
      } else {
        // Fallback: append to body if timeline container not found
        document.body.appendChild(notification);
        console.warn(
          "Timeline container not found. Notification added to body instead."
        );
      }
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

  showFrameTooltip(frameIndex) {
    // Create or update tooltip
    let tooltip = document.getElementById("frame-tooltip");
    if (!tooltip) {
      tooltip = document.createElement("div");
      tooltip.id = "frame-tooltip";
      tooltip.style.cssText = `
        position: absolute;
        bottom: 30px;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 3px 8px;
        border-radius: 3px;
        font-size: 11px;
        pointer-events: none;
        z-index: 1000;
      `;
      document.body.appendChild(tooltip);
    }

    // Get frame information
    const frame = this.state.sequence[frameIndex] || {};
    const duration =
      frame.ms || frame.duration || this.state.project.settings.frame_duration;

    // Set content
    tooltip.textContent = `Frame ${frameIndex + 1} | ${duration}ms`;

    // Position tooltip at scrubber
    const scrubberRect = this.scrubberHandle.getBoundingClientRect();
    tooltip.style.left = `${scrubberRect.left + scrubberRect.width / 2}px`;
    tooltip.style.bottom = `${window.innerHeight - scrubberRect.top + 10}px`;
    tooltip.style.display = "block";
  }

  hideFrameTooltip() {
    const tooltip = document.getElementById("frame-tooltip");
    if (tooltip) {
      tooltip.style.display = "none";
    }
  }

  highlightTimelineFrame(frameIndex) {
    // Remove highlight from all frames
    const timelineFrames = document.querySelectorAll(".timeline-frame");
    timelineFrames.forEach((frame) => frame.classList.remove("selected"));

    // Add highlight to current frame
    if (timelineFrames[frameIndex]) {
      timelineFrames[frameIndex].classList.add("selected");
    }
  }

  scrollTimelineToCurrentFrame() {
    const timelineContainer = document.getElementById("timelineFrames");
    const timelineFrames = document.querySelectorAll(".timeline-frame");

    if (timelineContainer && timelineFrames[this.state.currentFrame]) {
      const frameElement = timelineFrames[this.state.currentFrame];
      const containerRect = timelineContainer.getBoundingClientRect();
      const frameRect = frameElement.getBoundingClientRect();

      // Check if frame is out of view
      if (
        frameRect.left < containerRect.left ||
        frameRect.right > containerRect.right
      ) {
        frameElement.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
          inline: "nearest",
        });
      }
    }
  }

  // Enhanced sequence editing features
  async duplicateFrame() {
    try {
      if (
        this.state.currentFrame < 0 ||
        this.state.currentFrame >= this.state.sequence.length
      ) {
        return;
      }

      const originalFrame = this.state.sequence[this.state.currentFrame];
      const duplicatedFrame = { ...originalFrame };

      // Insert after current frame
      this.state.sequence.splice(
        this.state.currentFrame + 1,
        0,
        duplicatedFrame
      );

      // Update timeline
      this.updateTimeline();
      this.updateTimelineInfo();

      // Select the new frame
      this.selectFrame(this.state.currentFrame + 1);

      this.showSuccess("Frame duplicated");
    } catch (error) {
      this.showError("Failed to duplicate frame");
    }
  }

  // Enhanced auto-mapping with intelligent filename detection
  autoMapCharacters() {
    // Create demo mappings for testing
    const demoMappings = {};
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").forEach((letter) => {
      demoMappings[letter] = {
        mapped: true,
        filename: `${letter.toLowerCase()}_mouth.png`,
        path: `/demo/${letter.toLowerCase()}_mouth.png`,
      };
    });

    this.state.mappings = demoMappings;
    this.updateMappingGrid();
    this.validateMappings();

    this.showSuccess("Auto-mapped all 26 characters with demo data");
  }

  clearMappings() {
    if (confirm("Clear all character mappings?")) {
      this.state.mappings = {};
      this.generateMappingGrid();
      this.validateMappings();
      this.showSuccess("Mappings cleared");
    }
  }

  // Enhanced batch operations
  async batchExport() {
    const formats = ["mp4", "json", "gif"];
    const selectedFormats = formats.filter((format) =>
      confirm(`Export as ${format.toUpperCase()}?`)
    );

    if (selectedFormats.length === 0) return;

    for (const format of selectedFormats) {
      try {
        if (format === "mp4") {
          await this.exportVideo();
        } else if (format === "json") {
          await this.exportSequenceJSON();
        }
        // Add GIF export in future enhancement
      } catch (error) {
        this.showError(`Failed to export ${format}: ${error.message}`);
      }
    }
  }

  async exportSequenceJSON() {
    try {
      if (this.state.sequence.length === 0) {
        this.showError("No sequence to export");
        return;
      }

      const filename = prompt("Enter JSON filename:", "sequence.json");
      if (!filename) return;

      const response = await fetch("/api/export/json", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ filename }),
      });

      if (response.ok) {
        const blob = await response.blob();
        this.downloadFile(blob, filename);
        this.showSuccess("JSON exported successfully");
      }
    } catch (error) {
      this.showError("Failed to export JSON");
    }
  }

  handleFallbackImage(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      this.fallbackPreview.innerHTML = `<img src="${e.target.result}" alt="Fallback">`;
      this.fallbackPreview.classList.add("has-image");
      this.state.project.fallback_image = file.name;
    };
    reader.readAsDataURL(file);
  }

  handleSpaceImage(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      this.spacePreview.innerHTML = `<img src="${e.target.result}" alt="Space Image">`;
      this.spacePreview.classList.add("has-image");
      this.state.project.space_image = file.name;
      this.state.project.letter_map[" "] = e.target.result; // Use base64 for spaces
      this.showSuccess(`Imagem configurada para espaços: ${file.name}`);
      this.updateMappingGrid();
    };
    reader.readAsDataURL(file);
  }

  clearSpaceImage() {
    this.spacePreview.innerHTML = `
      <i class="fas fa-square"></i>
      <span>Use pause/transparent</span>
    `;
    this.spacePreview.classList.remove("has-image");
    this.state.project.space_image = null;
    delete this.state.project.letter_map[" "];
    this.showSuccess("Imagem de espaço removida - usando pausa");
    this.updateMappingGrid();
  }

  enableTestMode() {
    // Set up test environment with Portuguese text
    const testText = `"COMO COMEÇAR A FAZER UM JOGO DO JEITO CERTO"

Três pontos:
Primeiro, ter um batatador — um computador com poder de processamento mínimo de uma batata.
Segundo, entender que qualquer pessoa pode fazer isso — o segredo não é ser gênio, é só começar.
Terceiro, e o principal: ser lei — ter força de vontade e determinação.

Primeiro, no seu batatador, baixe dois programas:
Primeiro, o VS Code — é onde a mágica vai acontecer.
Segundo, o Node.js.

Se sentir dificuldade ou encontrar algum problema, manda nos comentários que a gente ajuda.

Agora, dentro do VS Code, clique no ícone que parece o Tetris e abra a aba de extensões.
Escreva Live Server e instale.
Isso vai servir pra rodar nosso projeto.`;

    this.textInput.value = testText;
    this.state.project.text = testText;
    this.state.project.folder_path = "images";
    this.folderPath.value = "images";

    // Load images from the images folder
    this.scanFolder();

    // Update UI
    this.updateCharCount();

    this.showSuccess(
      "Test mode enabled with Portuguese text! Loading images from 'images' folder..."
    );
  }

  // Audio-related Methods
  onTimingModeChange(isAudioMode) {
    // Handle timing mode change
    console.log(
      `Timing mode changed to: ${isAudioMode ? "audio-driven" : "manual"}`
    );

    // Update UI or state as needed
    this.state.isAudioDriven = isAudioMode;

    // Disable/enable relevant controls based on mode
    if (isAudioMode) {
      // When in audio-driven mode, certain settings might be controlled by audio
      this.frameDuration.disabled = true;
      this.showInfo(
        "Audio-driven timing mode enabled. Frame durations will sync to audio."
      );
    } else {
      // In manual mode, enable all settings
      this.frameDuration.disabled = false;
      this.showInfo("Manual timing mode enabled.");
    }
  }

  syncFrameToMarker(marker) {
    // Find the frame that corresponds to this marker in the sequence
    const timeMs = marker.time;

    if (
      !this.state.project.sequence ||
      this.state.project.sequence.length === 0
    ) {
      return;
    }

    // Find the frame that should be showing at this time point
    let cumulativeTime = 0;
    let targetFrameIndex = 0;

    for (let i = 0; i < this.state.project.sequence.length; i++) {
      const frame = this.state.project.sequence[i];
      cumulativeTime += frame.duration;

      if (cumulativeTime > timeMs) {
        targetFrameIndex = i;
        break;
      }
    }

    // Set the current frame and update the preview
    if (targetFrameIndex !== this.state.currentFrame) {
      this.state.currentFrame = targetFrameIndex;
      this.updatePreview();
      this.updateTimeline();
    }
  }

  async buildSequenceWithAudio() {
    // This method would be called when building a sequence with audio timing
    this.showInfo("Building sequence with audio timing...");

    // Get the uploaded audio file ID from state
    let audioFileId = this.state.audioFileId;

    // If user selected a file but hasn't uploaded yet, auto-upload and wait briefly
    if (!audioFileId && this.audioManager && this.audioManager.audioFile) {
      try {
        // Trigger upload (non-blocking API); then poll for state update
        this.audioManager.uploadAudio();
        const deadline = Date.now() + 8000; // wait up to 8s for upload to complete
        while (!this.state.audioFileId && Date.now() < deadline) {
          // small delay between checks
          // eslint-disable-next-line no-await-in-loop
          await new Promise((r) => setTimeout(r, 250));
        }
        audioFileId = this.state.audioFileId;
      } catch (e) {
        // Fall through to error handling below
      }
    }

    if (!audioFileId) {
      this.showError(
        "No audio file uploaded. Please upload an audio file first."
      );
      return;
    }

    // Primeiro alinhamos o áudio com o texto para obter os tokens de alinhamento
    return this.alignAudioWithText(audioFileId)
      .then((alignmentResult) => {
        console.log("Audio alignment successful:", alignmentResult);

        if (!alignmentResult.alignment || !alignmentResult.alignment.tokens) {
          throw new Error("No alignment tokens received from server");
        }

        // Armazenar tokens de alinhamento
        if (this.audioManager) {
          this.audioManager.alignmentTokens = alignmentResult.alignment.tokens;
          console.log(
            "Alignment tokens stored:",
            this.audioManager.alignmentTokens
          );

          // Opcionalmente, exibir marcadores no visualizador de áudio
          this.audioManager.createTimingMarkers(
            alignmentResult.alignment.tokens
          );
        }

        // Agora construir a sequência com os tokens de alinhamento
        console.log("Building sequence with audio file ID:", audioFileId);
        console.log("Project text:", this.state.project.text);

        const requestData = {
          audio_filename: audioFileId,
          text: this.state.project.text,
          alignment_tokens: alignmentResult.alignment.tokens,
          text_driven: this.audioTextDrivenToggle
            ? !!this.audioTextDrivenToggle.checked
            : true,
        };

        console.log("Sending request data:", requestData);
        return this.apiCall(
          "/api/sequence/build-from-audio",
          "POST",
          requestData
        );
      })
      .then((data) => {
        if (data.success) {
          // Update sequence with audio-timed frames
          this.state.project.sequence = data.sequence;
          this.state.sequence = data.sequence; // Sync both sequence locations
          this.updateTimeline();
          this.showSuccess("Sequence built successfully with audio timing!");
        } else {
          this.showError(`Failed to build sequence: ${data.error}`);
        }
      })
      .catch((error) => {
        console.error("Error building sequence:", error);
        this.showError("An error occurred while building the sequence.");
      });
  }

  // Synchronized audio and animation playback
  initSyncPlayback() {
    // Initialize sync playback UI elements
    this.syncPlaybackBtn = document.getElementById("syncPlaybackBtn");

    // Bind event listeners
    if (this.syncPlaybackBtn) {
      this.syncPlaybackBtn.addEventListener("click", () => {
        this.toggleSyncPlayback();
      });
    }
  }

  toggleSyncPlayback() {
    if (this.state.syncPlaybackActive) {
      this.stopSyncPlayback();
    } else {
      this.startSyncPlayback();
    }
  }

  startSyncPlayback() {
    // Check if audio and sequence are available
    if (
      !this.audioManager ||
      !this.audioManager.wavesurfer ||
      !this.state.sequence ||
      this.state.sequence.length === 0
    ) {
      this.showError(
        "No audio or sequence available for synchronized playback"
      );
      return;
    }

    // Stop any existing playback
    this.stopSequence();

    // Set the state
    this.state.syncPlaybackActive = true;

    // Update UI
    this.syncPlaybackBtn.classList.add("sync-active");
    this.syncPlaybackBtn.innerHTML =
      '<i class="fas fa-pause"></i> Stop Sync Playback';

    // Start audio playback
    this.audioManager.wavesurfer.play();

    // Set up a handler for audio timeupdate to sync with animation frames
    this.audioManager.wavesurfer.on("audioprocess", (currentTime) => {
      this.updateAnimationForAudioTime(currentTime * 1000); // Convert to ms
    });

    // Handle audio playback end
    this.audioManager.wavesurfer.on("finish", () => {
      this.stopSyncPlayback();
    });
  }

  stopSyncPlayback() {
    if (!this.state.syncPlaybackActive) return;

    // Update state
    this.state.syncPlaybackActive = false;

    // Stop audio
    if (this.audioManager && this.audioManager.wavesurfer) {
      this.audioManager.wavesurfer.pause();
      // Remove the event listeners
      this.audioManager.wavesurfer.un("audioprocess");
      this.audioManager.wavesurfer.un("finish");
    }

    // Reset UI
    this.syncPlaybackBtn.classList.remove("sync-active");
    this.syncPlaybackBtn.innerHTML =
      '<i class="fas fa-film"></i> <i class="fas fa-music"></i> Play Audio + Animation';

    // Clear any active frame timer
    if (this.state.syncAnimationFrameTimer) {
      clearTimeout(this.state.syncAnimationFrameTimer);
      this.state.syncAnimationFrameTimer = null;
    }
  }

  updateAnimationForAudioTime(timeMs) {
    // Show loading indicator for preview frame
    this.previewFrame.classList.add("loading");

    // Create loading indicator if it doesn't exist
    if (!this.previewFrame.querySelector(".preview-loading-indicator")) {
      const loadingIndicator = document.createElement("div");
      loadingIndicator.className = "preview-loading-indicator";
      loadingIndicator.innerHTML =
        '<i class="fas fa-circle-notch fa-spin"></i>';
      this.previewFrame.appendChild(loadingIndicator);
    }

    // Find the frame that corresponds to the current audio time
    let cumulativeTime = 0;
    let targetFrameIndex = -1;

    // Iterate through frames to find the one that corresponds to the current audio time
    for (let i = 0; i < this.state.sequence.length; i++) {
      const frame = this.state.sequence[i];
      const frameDuration = frame.ms || frame.duration || 80; // Default to 80ms if no duration

      // If we have audio_start and audio_end, use those for precise timing (preferred)
      if (frame.audio_start !== undefined && frame.audio_end !== undefined) {
        // Convert to numbers to ensure proper comparison
        const startMs = parseFloat(frame.audio_start);
        const endMs = parseFloat(frame.audio_end);

        if (timeMs >= startMs && timeMs < endMs) {
          targetFrameIndex = i;
          break;
        }
      } else {
        // Otherwise use the cumulative frame durations as fallback
        cumulativeTime += frameDuration;
        if (cumulativeTime > timeMs) {
          targetFrameIndex = i;
          break;
        }
      }
    }

    // If we found a valid frame, show it
    if (
      targetFrameIndex >= 0 &&
      targetFrameIndex < this.state.sequence.length
    ) {
      // Only update the frame if it's different from the current one
      if (targetFrameIndex !== this.state.currentFrame) {
        // Add visual indicator for active frame in timeline
        const timelineFrames = document.querySelectorAll(".timeline-frame");
        timelineFrames.forEach((frame) => frame.classList.remove("selected"));

        if (timelineFrames[targetFrameIndex]) {
          timelineFrames[targetFrameIndex].classList.add("selected");

          // Scroll into view if not visible
          const timelineContainer = document.getElementById("timelineFrames");
          if (timelineContainer) {
            const frameElement = timelineFrames[targetFrameIndex];
            const containerRect = timelineContainer.getBoundingClientRect();
            const frameRect = frameElement.getBoundingClientRect();

            // Check if frame is out of view
            if (
              frameRect.left < containerRect.left ||
              frameRect.right > containerRect.right
            ) {
              frameElement.scrollIntoView({
                behavior: "smooth",
                block: "nearest",
                inline: "nearest",
              });
            }
          }
        }

        // Update the frame display
        this.selectFrame(targetFrameIndex);
        this.loadFramePreview(targetFrameIndex);

        // Update timeline scrubber position
        if (this.scrubberHandle && this.state.sequence.length > 0) {
          const percent =
            (targetFrameIndex / (this.state.sequence.length - 1)) * 100;
          this.scrubberHandle.style.left = `${percent}%`;
        }

        // Display frame info in status bar
        this.updateTimelineInfo(targetFrameIndex);
      }
    }

    // Remove loading state after a short delay
    setTimeout(() => {
      this.previewFrame.classList.remove("loading");
    }, 100);
  }

  // Enhanced Audio Alignment Methods
  async initEnhancedAlignment() {
    console.log("Initializing enhanced audio alignment...");

    try {
      // Check if enhanced features are available
      const statusResponse = await this.apiCall("/api/audio/status", "GET");

      if (statusResponse && statusResponse.features) {
        const features = statusResponse.features;
        this.enhancedAlignmentAvailable =
          features.enhanced_silence_detection &&
          features.forced_alignment &&
          features.sub_frame_timing;

        // Update UI based on availability
        this.updateEnhancedAlignmentUI(features);

        // Initialize enhanced settings in project state
        if (!this.state.project.settings.alignmentMethod) {
          this.state.project.settings.alignmentMethod = "auto";
        }
        if (!this.state.project.settings.targetFps) {
          this.state.project.settings.targetFps = 30;
        }

        console.log("Enhanced alignment features:", features);
      } else {
        this.enhancedAlignmentAvailable = false;
        this.updateEnhancedAlignmentUI({});
        console.warn("Could not determine enhanced alignment availability");
      }
    } catch (error) {
      console.error("Failed to check enhanced alignment status:", error);
      this.enhancedAlignmentAvailable = false;
      this.updateEnhancedAlignmentUI({});
    }
  }

  updateEnhancedAlignmentUI(features) {
    if (!this.enhancementStatus) return;

    const available = this.enhancedAlignmentAvailable;

    if (available) {
      this.enhancementStatus.innerHTML = `
        <i class="fas fa-check-circle" style="color: #10B981;"></i> 
        Enhanced features available: 
        ${
          features.enhanced_silence_detection
            ? "✓ Advanced Silence Detection"
            : ""
        } 
        ${features.forced_alignment ? "✓ Forced Alignment" : ""} 
        ${features.sub_frame_timing ? "✓ Sub-frame Timing" : ""}
      `;

      // Enable enhanced controls
      if (this.useEnhancedAlignment) {
        this.useEnhancedAlignment.disabled = false;
      }
    } else {
      this.enhancementStatus.innerHTML = `
        <i class="fas fa-exclamation-triangle" style="color: #F59E0B;"></i> 
        Enhanced features not available - install additional dependencies for advanced alignment
      `;

      // Disable enhanced controls
      if (this.useEnhancedAlignment) {
        this.useEnhancedAlignment.disabled = true;
        this.useEnhancedAlignment.checked = false;
      }
    }

    // Update visibility of enhanced settings
    this.toggleEnhancedAlignmentSettings();
  }

  toggleEnhancedAlignmentSettings() {
    const isEnabled =
      this.useEnhancedAlignment?.checked && this.enhancedAlignmentAvailable;

    if (this.alignmentMethodContainer) {
      this.alignmentMethodContainer.style.display = isEnabled
        ? "block"
        : "none";
    }
    if (this.targetFpsContainer) {
      this.targetFpsContainer.style.display = isEnabled ? "block" : "none";
    }

    // Update project settings
    this.state.project.settings.useEnhancedAlignment = isEnabled;

    console.log("Enhanced alignment", isEnabled ? "enabled" : "disabled");
  }

  // Modified alignment method to use enhanced when enabled
  async alignAudioWithText(audioFileId) {
    const useEnhanced =
      this.useEnhancedAlignment?.checked && this.enhancedAlignmentAvailable;
    const endpoint = useEnhanced
      ? "/api/audio/align-enhanced"
      : "/api/audio/align";

    console.log(
      `Aligning audio with text using ${
        useEnhanced ? "enhanced" : "standard"
      } method...`
    );

    this.showStatus(
      `Aligning audio with text (${useEnhanced ? "Enhanced" : "Standard"})...`
    );

    const requestData = {
      filename: audioFileId,
      text: this.state.project.text,
    };

    // Add enhanced-specific parameters
    if (useEnhanced) {
      requestData.fps = parseInt(this.targetFps?.value || this.fps.value || 30);
      requestData.method = this.alignmentMethod?.value || "auto";
      requestData.language = "pt-BR"; // Could be made configurable
    }

    return this.apiCall(endpoint, "POST", requestData)
      .then((alignmentResult) => {
        console.log(
          `${
            useEnhanced ? "Enhanced" : "Standard"
          } audio alignment successful:`,
          alignmentResult
        );

        if (!alignmentResult.alignment || !alignmentResult.alignment.tokens) {
          throw new Error("No alignment tokens received from server");
        }

        // Store alignment tokens
        if (this.audioManager) {
          this.audioManager.alignmentTokens = alignmentResult.alignment.tokens;
          console.log(
            "Alignment tokens stored:",
            this.audioManager.alignmentTokens
          );

          // Create timing markers
          this.audioManager.createTimingMarkers(
            alignmentResult.alignment.tokens
          );
        }

        // Store enhanced data if available
        if (useEnhanced && alignmentResult.alignment.timeline) {
          this.audioManager.enhancedTimeline =
            alignmentResult.alignment.timeline;
          console.log(
            "Enhanced timeline stored:",
            alignmentResult.alignment.timeline.length,
            "entries"
          );
        }

        if (useEnhanced && alignmentResult.alignment.frame_states) {
          this.audioManager.frameStates =
            alignmentResult.alignment.frame_states;
          console.log(
            "Frame states stored:",
            alignmentResult.alignment.frame_states.length,
            "frames"
          );
        }

        return alignmentResult;
      })
      .catch((error) => {
        console.error(
          `${useEnhanced ? "Enhanced" : "Standard"} alignment failed:`,
          error
        );

        // If enhanced alignment fails, try falling back to standard
        if (useEnhanced) {
          console.log("Attempting fallback to standard alignment...");
          this.showStatus(
            "Enhanced alignment failed, trying standard method..."
          );

          return this.apiCall("/api/audio/align", "POST", {
            filename: audioFileId,
            text: this.state.project.text,
          });
        } else {
          throw error;
        }
      });
  }
}

// Expose class globally so extension scripts (export_progress.js, timeline_enhancements.js, etc.)
// can safely patch prototype even se executados antes da instância ser criada.
if (typeof window !== "undefined" && !window.FaceSequencerApp) {
  window.FaceSequencerApp = FaceSequencerApp;
}

// Initialize the application when DOM is loaded
// Note: Main initialization moved to index.html
// document.addEventListener("DOMContentLoaded", () => {
//   new FaceSequencerApp();
// });
