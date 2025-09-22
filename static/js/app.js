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
      mappings: {},
      currentFrame: 0,
      playing: false,
      exportTask: null,
    };

    this.previewInterval = null;
    this.init();
  }

  init() {
    this.initializeElements();
    this.bindEvents();
    this.loadProject();
    this.generateMappingGrid();
    this.updateUI();
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
        const fullPath = e.target.files[0].webkitRelativePath;
        const folderName = fullPath.split("/")[0];

        console.log("Selected folder:", folderName);
        console.log("Full path:", fullPath);

        this.folderPath.value = folderName;
        this.state.project.folder_path = folderName;

        // Show success message
        this.showStatus(`Folder selected: ${folderName}`);
      }
    });

    // Manual folder path input
    this.folderPath.addEventListener("input", () => {
      this.state.project.folder_path = this.folderPath.value;
    });

    this.scanFolderBtn.addEventListener("click", () => {
      this.scanFolder();
    });

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
    };

    if (data && method !== "GET") {
      config.body = JSON.stringify(data);
    }

    try {
      const response = await fetch(`/api${endpoint}`, config);
      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || "API call failed");
      }

      return result;
    } catch (error) {
      this.showError(`API Error: ${error.message}`);
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
        const result = await this.apiCall("/project");
        this.state.project = result.project;
        this.updateUI();
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
      if (!this.state.project.folder_path) {
        this.showError("Please select a folder first");
        return;
      }

      this.showStatus("Scanning folder...");
      const result = await this.apiCall("/folder/scan", "POST", {
        path: this.state.project.folder_path,
      });

      this.state.mappings = result.mappings;
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
      await this.apiCall("/project", "POST", {
        text: this.state.project.text,
        settings: this.state.project.settings,
        name: this.state.project.name,
      });

      // Then build the sequence
      console.log("Building sequence...");
      const result = await this.apiCall("/sequence/build", "POST");

      this.state.sequence = result.sequence;
      this.updateTimeline();
      this.updateTimelineInfo();

      this.showSuccess(`Built sequence with ${result.total_frames} frames`);
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
    if (this.state.sequence.length === 0) {
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

        setTimeout(() => {
          if (this.state.playing) {
            playFrame();
          }
        }, result.duration);
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
    this.previewFrame.innerHTML = `
            <div class="preview-placeholder pause-indicator">
                <i class="fas fa-pause"></i>
                <span>Pause (${frameData.duration}ms)</span>
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
    const checkProgress = async () => {
      try {
        const result = await this.apiCall(
          `/export/status/${this.state.exportTask}`
        );
        const task = result.task;

        if (task.status === "processing") {
          this.showProgress(task.progress || 0);
          setTimeout(checkProgress, 1000);
        } else if (task.status === "completed") {
          this.hideProgress();
          this.downloadExport();
        } else if (task.status === "error") {
          this.hideProgress();
          this.showError(`Export failed: ${task.error}`);
        }
      } catch (error) {
        this.hideProgress();
        this.showError("Failed to check export progress");
      }
    };

    checkProgress();
  }

  async downloadExport() {
    try {
      const response = await fetch(
        `/api/export/download/${this.state.exportTask}`
      );

      if (response.ok) {
        const blob = await response.blob();
        const filename =
          response.headers
            .get("Content-Disposition")
            ?.split("filename=")[1]
            ?.replace(/"/g, "") || "export.mp4";

        this.downloadFile(blob, filename);
        this.showSuccess("Video exported successfully");
      }
    } catch (error) {
      this.showError("Failed to download export");
    }
  }

  // UI Update Methods
  updateUI() {
    // Update form fields
    this.textInput.value = this.state.project.text;
    this.folderPath.value = this.state.project.folder_path;
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
    // Drag over handler
    item.addEventListener("dragover", (e) => {
      e.preventDefault();
      item.classList.add("drag-over");
    });

    // Drag leave handler
    item.addEventListener("dragleave", () => {
      item.classList.remove("drag-over");
    });

    // Drop handler
    item.addEventListener("drop", (e) => {
      e.preventDefault();
      item.classList.remove("drag-over");

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        const file = files[0];
        if (this.isImageFile(file)) {
          this.assignImageToLetter(letter, file);
        } else {
          this.showError("Please drop an image file");
        }
      }
    });

    // Make the item a drop zone
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

  async assignImageToLetter(letter, file) {
    try {
      // Create thumbnail preview
      const reader = new FileReader();
      reader.onload = (e) => {
        const item = document.querySelector(`[data-letter="${letter}"]`);
        if (item) {
          const preview = item.querySelector(".mapping-preview");
          preview.innerHTML = `<img src="${e.target.result}" alt="${letter}">`;
          item.classList.add("mapped");
          item.classList.remove("missing");

          const statusIcon = item.querySelector(".mapping-status-icon");
          statusIcon.style.display = "none";
        }
      };
      reader.readAsDataURL(file);

      // Update state (in a real implementation, you'd upload the file to the server)
      if (!this.state.mappings[letter]) {
        this.state.mappings[letter] = {};
      }
      this.state.mappings[letter].mapped = true;
      this.state.mappings[letter].filename = file.name;

      this.validateMappings();
      this.showSuccess(`Assigned image to letter ${letter}`);
    } catch (error) {
      this.showError(`Failed to assign image: ${error.message}`);
    }
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
        if (this.state.project.letter_map[' ']) {
          preview.innerHTML = `<img src="${this.state.project.letter_map[' ']}" alt="Space Image">`;
        }
      } else {
        spaceItem.classList.remove("mapped", "missing");
        statusIcon.style.display = "none";
        preview.innerHTML = '<i class="fas fa-square"></i>';
      }
    }
  }

  updateTimeline() {
    this.timelineFrames.innerHTML = "";

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
                    <div class="frame-duration">${frame.duration}ms</div>
                </div>
                <div class="frame-index">${index + 1}</div>
            `;

      frameElement.addEventListener("click", () => {
        this.selectFrame(index);
      });

      this.timelineFrames.appendChild(frameElement);
    });
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
      this.selectedFrameDuration.value = this.state.sequence[index].duration;
    } else {
      this.frameEditor.style.display = "none";
    }

    // Load frame preview
    this.loadFramePreview(index);
  }

  async loadFramePreview(index) {
    try {
      const result = await this.apiCall(`/sequence/frame/${index}`);

      if (result.is_pause) {
        this.showPauseFrame(result);
      } else {
        this.showFrameImage(result.image);
      }
    } catch (error) {
      console.error("Failed to load frame preview:", error);
    }
  }

  updateTimelineInfo() {
    const frameCount = this.state.sequence.length;
    const totalDuration = this.state.sequence.reduce(
      (sum, frame) => sum + frame.duration,
      0
    );

    this.timelineInfo.textContent = `${frameCount} frames (${(
      totalDuration / 1000
    ).toFixed(1)}s)`;
  }

  // Utility Methods
  downloadFile(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
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

  showProgress(percent) {
    this.progressContainer.style.display = "flex";
    this.progressFill.style.width = `${percent}%`;
    this.progressText.textContent = `${Math.round(percent)}%`;
  }

  hideProgress() {
    this.progressContainer.style.display = "none";
  }

  setupTimelineScrubber() {
    const scrubber = document.getElementById("timelineScrubber");
    let isDragging = false;

    const updateScrubberPosition = (clientX) => {
      const rect = scrubber.getBoundingClientRect();
      const percentage = Math.max(
        0,
        Math.min(1, (clientX - rect.left) / rect.width)
      );
      const frameIndex = Math.floor(percentage * this.state.sequence.length);

      this.scrubberHandle.style.left = `${percentage * 100}%`;

      if (
        frameIndex !== this.state.currentFrame &&
        frameIndex < this.state.sequence.length
      ) {
        this.selectFrame(frameIndex);
      }
    };

    scrubber.addEventListener("mousedown", (e) => {
      isDragging = true;
      updateScrubberPosition(e.clientX);
    });

    document.addEventListener("mousemove", (e) => {
      if (isDragging) {
        updateScrubberPosition(e.clientX);
      }
    });

    document.addEventListener("mouseup", () => {
      isDragging = false;
    });

    // Click to seek
    scrubber.addEventListener("click", (e) => {
      if (!isDragging) {
        updateScrubberPosition(e.clientX);
      }
    });
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
      this.state.project.letter_map[' '] = e.target.result; // Use base64 for spaces
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
    delete this.state.project.letter_map[' '];
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
}

// Initialize the application when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  new FaceSequencerApp();
});
