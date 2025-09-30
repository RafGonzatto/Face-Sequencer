/**
 * Advanced Video Editor - Phase 3 Frontend Components
 * AI-powered optimization, batch processing, and collaborative editing UI
 */

class AdvancedVideoEditorPhase3 {
  constructor(app) {
    this.app = app;
    this.socket = null;
    this.currentProjectId = null;
    this.currentUserId = null;
    this.currentUsername = null;
    this.userRole = "editor";

    // Component managers
    this.aiOptimizer = new AIOptimizerManager();
    this.batchProcessor = new BatchProcessorManager();
    this.collaborativeEditor = new CollaborativeEditorManager();

    // UI state
    this.activeMode = "standard"; // 'standard', 'ai', 'batch', 'collaborative'
    this.connectedUsers = new Map();
    this.activeLocks = new Map();

    this.initializePhase3UI();
    this.setupEventListeners();
  }

  initializePhase3UI() {
    console.log("Initializing Phase 3 Advanced Video Editor UI");

    // Add advanced mode switcher to header
    this.addAdvancedModeSelector();

    // Initialize component UIs
    this.aiOptimizer.initialize();
    this.batchProcessor.initialize();
    this.collaborativeEditor.initialize();

    // Setup real-time communication
    this.initializeWebSocket();
  }

  addAdvancedModeSelector() {
    const header = document.querySelector(".header-right");
    if (!header) return;

    const modeSelector = document.createElement("div");
    modeSelector.className = "advanced-mode-selector";
    modeSelector.innerHTML = `
            <div class="mode-dropdown">
                <button class="mode-btn active" data-mode="standard">
                    <i class="fas fa-video"></i>
                    Standard Editor
                </button>
                <div class="mode-options">
                    <button class="mode-option" data-mode="ai">
                        <i class="fas fa-brain"></i>
                        AI Optimization
                    </button>
                    <button class="mode-option" data-mode="batch">
                        <i class="fas fa-layer-group"></i>
                        Batch Processing
                    </button>
                    <button class="mode-option" data-mode="collaborative">
                        <i class="fas fa-users"></i>
                        Collaborative Edit
                    </button>
                </div>
            </div>
        `;

    header.appendChild(modeSelector);
  }

  setupEventListeners() {
    // Mode switching
    document.addEventListener("click", (e) => {
      if (e.target.matches(".mode-btn, .mode-option")) {
        const mode = e.target.getAttribute("data-mode");
        this.switchToMode(mode);
      }
    });

    // AI optimization events
    document.addEventListener("ai-optimization-requested", (e) => {
      this.handleAIOptimization(e.detail);
    });

    // Batch processing events
    document.addEventListener("batch-job-submitted", (e) => {
      this.handleBatchJobSubmission(e.detail);
    });

    // Collaborative editing events
    document.addEventListener("collaborative-session-requested", (e) => {
      this.handleCollaborativeSession(e.detail);
    });

    // Keyboard shortcuts for advanced features
    document.addEventListener("keydown", (e) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case "o":
            if (e.shiftKey) {
              e.preventDefault();
              this.showAIOptimizationDialog();
            }
            break;
          case "b":
            if (e.shiftKey) {
              e.preventDefault();
              this.showBatchProcessingDialog();
            }
            break;
          case "u":
            if (e.shiftKey) {
              e.preventDefault();
              this.showCollaborativeDialog();
            }
            break;
        }
      }
    });
  }

  switchToMode(mode) {
    console.log(`Switching to ${mode} mode`);

    // Update active mode
    this.activeMode = mode;

    // Update UI
    document.querySelectorAll(".mode-btn, .mode-option").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-mode") === mode);
    });

    // Show/hide relevant panels
    this.updateModeDisplay(mode);

    // Initialize mode-specific features
    switch (mode) {
      case "ai":
        this.aiOptimizer.activate();
        break;
      case "batch":
        this.batchProcessor.activate();
        break;
      case "collaborative":
        this.collaborativeEditor.activate();
        break;
      default:
        this.deactivateAdvancedModes();
        break;
    }
  }

  updateModeDisplay(mode) {
    // Hide all advanced panels
    document.querySelectorAll(".advanced-panel").forEach((panel) => {
      panel.style.display = "none";
    });

    // Show relevant panel
    const panel = document.querySelector(`.${mode}-panel`);
    if (panel) {
      panel.style.display = "block";
    }
  }

  deactivateAdvancedModes() {
    this.aiOptimizer.deactivate();
    this.batchProcessor.deactivate();
    this.collaborativeEditor.deactivate();
  }

  initializeWebSocket() {
    if (!window.io) {
      console.warn("Socket.IO not available for real-time features");
      return;
    }

    this.socket = io();

    this.socket.on("connect", () => {
      console.log("WebSocket connected for real-time collaboration");
    });

    this.socket.on("disconnect", () => {
      console.log("WebSocket disconnected");
    });

    // Collaborative editing events
    this.socket.on("user_connected", (data) => {
      this.handleUserConnected(data);
    });

    this.socket.on("user_disconnected", (data) => {
      this.handleUserDisconnected(data);
    });

    this.socket.on("segment_locked", (data) => {
      this.handleSegmentLocked(data);
    });

    this.socket.on("segment_unlocked", (data) => {
      this.handleSegmentUnlocked(data);
    });

    this.socket.on("edit_applied", (data) => {
      this.handleRemoteEdit(data);
    });

    this.socket.on("cursor_update", (data) => {
      this.handleCursorUpdate(data);
    });
  }

  // AI Optimization Methods
  async handleAIOptimization(options) {
    try {
      this.showLoadingIndicator("Applying AI optimization...");

      const segments = this.getCurrentSubtitleSegments();
      if (!segments || segments.length === 0) {
        throw new Error("No subtitle segments to optimize");
      }

      const response = await fetch("/api/v3/ai/optimize-subtitles", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          segments: segments,
          optimization_level: options.level || "balanced",
          target_platform: options.platform || "general",
          user_preferences: options.preferences || {},
        }),
      });

      const result = await response.json();

      if (result.success) {
        this.applyOptimizedSegments(result.optimized_segments);
        this.displayOptimizationMetrics(result.optimization_metrics);
        this.showSuccess("AI optimization completed successfully!");
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      console.error("AI optimization failed:", error);
      this.showError(`AI optimization failed: ${error.message}`);
    } finally {
      this.hideLoadingIndicator();
    }
  }

  showAIOptimizationDialog() {
    const dialog = this.createDialog(
      "AI Subtitle Optimization",
      `
            <div class="ai-optimization-form">
                <div class="form-group">
                    <label>Optimization Level:</label>
                    <select id="optimization-level">
                        <option value="conservative">Conservative - Minimal changes</option>
                        <option value="balanced" selected>Balanced - Recommended</option>
                        <option value="aggressive">Aggressive - Maximum optimization</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>Target Platform:</label>
                    <select id="target-platform">
                        <option value="general" selected>General Purpose</option>
                        <option value="instagram">Instagram Stories/Reels</option>
                        <option value="tiktok">TikTok</option>
                        <option value="youtube">YouTube Shorts</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="improve-readability" checked>
                        Improve text readability
                    </label>
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="optimize-timing" checked>
                        Optimize segment timing
                    </label>
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="enhance-coherence">
                        Enhance text coherence
                    </label>
                </div>
                
                <div class="dialog-buttons">
                    <button class="btn-secondary" onclick="this.closest('.dialog-overlay').remove()">Cancel</button>
                    <button class="btn-primary" onclick="window.advancedEditor.executeAIOptimization()">
                        Apply AI Optimization
                    </button>
                </div>
            </div>
        `
    );

    document.body.appendChild(dialog);
  }

  executeAIOptimization() {
    const level = document.getElementById("optimization-level").value;
    const platform = document.getElementById("target-platform").value;
    const preferences = {
      improve_readability: document.getElementById("improve-readability")
        .checked,
      optimize_timing: document.getElementById("optimize-timing").checked,
      enhance_coherence: document.getElementById("enhance-coherence").checked,
    };

    document.querySelector(".dialog-overlay").remove();

    this.handleAIOptimization({ level, platform, preferences });
  }

  // Batch Processing Methods
  async handleBatchJobSubmission(jobData) {
    try {
      this.showLoadingIndicator("Submitting batch job...");

      const response = await fetch("/api/v3/batch/submit-job", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(jobData),
      });

      const result = await response.json();

      if (result.success) {
        this.addBatchJobToQueue(result.job_id, jobData);
        this.showSuccess(
          `Batch job submitted successfully! Job ID: ${result.job_id}`
        );
        this.startJobMonitoring(result.job_id);
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      console.error("Batch job submission failed:", error);
      this.showError(`Failed to submit batch job: ${error.message}`);
    } finally {
      this.hideLoadingIndicator();
    }
  }

  showBatchProcessingDialog() {
    const dialog = this.createDialog(
      "Batch Processing",
      `
            <div class="batch-processing-form">
                <div class="batch-type-selector">
                    <label>Batch Operation Type:</label>
                    <select id="batch-type">
                        <option value="generation">Subtitle Generation</option>
                        <option value="optimization">AI Optimization</option>
                        <option value="export">Video Export</option>
                    </select>
                </div>
                
                <div id="batch-options">
                    <!-- Dynamic options based on batch type -->
                </div>
                
                <div class="file-upload-area">
                    <label>Upload Files:</label>
                    <div class="upload-zone" id="batch-upload-zone">
                        <i class="fas fa-cloud-upload-alt"></i>
                        <p>Drag and drop files here or click to select</p>
                        <input type="file" multiple id="batch-files" style="display: none;">
                    </div>
                    <div id="file-list"></div>
                </div>
                
                <div class="dialog-buttons">
                    <button class="btn-secondary" onclick="this.closest('.dialog-overlay').remove()">Cancel</button>
                    <button class="btn-primary" onclick="window.advancedEditor.executeBatchProcessing()">
                        Start Batch Processing
                    </button>
                </div>
            </div>
        `
    );

    document.body.appendChild(dialog);
    this.setupBatchProcessingHandlers();
  }

  // Collaborative Editing Methods
  async handleCollaborativeSession(sessionData) {
    try {
      this.showLoadingIndicator("Connecting to collaborative session...");

      // Create or connect to collaborative session
      if (sessionData.create) {
        await this.createCollaborativeSession(sessionData);
      } else {
        await this.connectToCollaborativeSession(sessionData);
      }
    } catch (error) {
      console.error("Collaborative session failed:", error);
      this.showError(`Collaborative session failed: ${error.message}`);
    } finally {
      this.hideLoadingIndicator();
    }
  }

  async createCollaborativeSession(sessionData) {
    const response = await fetch("/api/v3/collaborative/create-session", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        project_id: sessionData.projectId || this.generateProjectId(),
        conflict_resolution:
          sessionData.conflictResolution || "merge_automatic",
      }),
    });

    const result = await response.json();

    if (result.success) {
      this.currentProjectId = result.project_id;
      await this.connectUser(sessionData.username, sessionData.role);
      this.showSuccess("Collaborative session created successfully!");
    } else {
      throw new Error(result.error);
    }
  }

  async connectToCollaborativeSession(sessionData) {
    this.currentProjectId = sessionData.projectId;
    await this.connectUser(sessionData.username, sessionData.role);
  }

  async connectUser(username, role = "editor") {
    this.currentUserId = this.generateUserId();
    this.currentUsername = username;
    this.userRole = role;

    const response = await fetch(
      `/api/v3/collaborative/connect/${this.currentProjectId}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: this.currentUserId,
          username: username,
          role: role,
        }),
      }
    );

    const result = await response.json();

    if (result.success) {
      // Join WebSocket room
      if (this.socket) {
        this.socket.emit("join_project", {
          project_id: this.currentProjectId,
          user_id: this.currentUserId,
        });
      }

      // Update UI with project state
      this.updateCollaborativeUI(result.project_state);
      this.showSuccess(`Connected as ${role} to collaborative session`);
    } else {
      throw new Error(result.error);
    }
  }

  showCollaborativeDialog() {
    const dialog = this.createDialog(
      "Collaborative Editing",
      `
            <div class="collaborative-form">
                <div class="session-options">
                    <div class="option-group">
                        <input type="radio" name="session-type" id="create-session" value="create" checked>
                        <label for="create-session">Create New Session</label>
                    </div>
                    <div class="option-group">
                        <input type="radio" name="session-type" id="join-session" value="join">
                        <label for="join-session">Join Existing Session</label>
                    </div>
                </div>
                
                <div id="create-options">
                    <div class="form-group">
                        <label>Project Name:</label>
                        <input type="text" id="project-name" placeholder="Enter project name">
                    </div>
                    <div class="form-group">
                        <label>Conflict Resolution:</label>
                        <select id="conflict-resolution">
                            <option value="merge_automatic">Automatic Merge</option>
                            <option value="prefer_latest">Prefer Latest</option>
                            <option value="prefer_role_priority">Role Priority</option>
                            <option value="manual_review">Manual Review</option>
                        </select>
                    </div>
                </div>
                
                <div id="join-options" style="display: none;">
                    <div class="form-group">
                        <label>Project ID:</label>
                        <input type="text" id="project-id" placeholder="Enter project ID">
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Your Name:</label>
                    <input type="text" id="username" placeholder="Enter your name" required>
                </div>
                
                <div class="form-group">
                    <label>Role:</label>
                    <select id="user-role">
                        <option value="editor">Editor</option>
                        <option value="reviewer">Reviewer</option>
                        <option value="viewer">Viewer</option>
                    </select>
                </div>
                
                <div class="dialog-buttons">
                    <button class="btn-secondary" onclick="this.closest('.dialog-overlay').remove()">Cancel</button>
                    <button class="btn-primary" onclick="window.advancedEditor.executeCollaborativeSession()">
                        Connect
                    </button>
                </div>
            </div>
        `
    );

    document.body.appendChild(dialog);
    this.setupCollaborativeHandlers();
  }

  // UI Helper Methods
  createDialog(title, content) {
    const overlay = document.createElement("div");
    overlay.className = "dialog-overlay";
    overlay.innerHTML = `
            <div class="dialog-box">
                <div class="dialog-header">
                    <h3>${title}</h3>
                    <button class="close-btn" onclick="this.closest('.dialog-overlay').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="dialog-content">
                    ${content}
                </div>
            </div>
        `;
    return overlay;
  }

  showLoadingIndicator(message) {
    const existing = document.querySelector(".loading-overlay");
    if (existing) existing.remove();

    const overlay = document.createElement("div");
    overlay.className = "loading-overlay";
    overlay.innerHTML = `
            <div class="loading-content">
                <div class="spinner"></div>
                <p>${message}</p>
            </div>
        `;
    document.body.appendChild(overlay);
  }

  hideLoadingIndicator() {
    const overlay = document.querySelector(".loading-overlay");
    if (overlay) overlay.remove();
  }

  showSuccess(message) {
    this.showNotification(message, "success");
  }

  showError(message) {
    this.showNotification(message, "error");
  }

  showNotification(message, type = "info") {
    const notification = document.createElement("div");
    notification.className = `notification ${type}`;
    notification.innerHTML = `
            <i class="fas fa-${
              type === "success"
                ? "check"
                : type === "error"
                ? "exclamation"
                : "info"
            }-circle"></i>
            <span>${message}</span>
            <button class="close-btn" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;

    const container =
      document.querySelector(".notification-container") ||
      this.createNotificationContainer();
    container.appendChild(notification);

    setTimeout(() => {
      if (notification.parentElement) {
        notification.remove();
      }
    }, 5000);
  }

  createNotificationContainer() {
    const container = document.createElement("div");
    container.className = "notification-container";
    document.body.appendChild(container);
    return container;
  }

  generateProjectId() {
    return "project_" + Math.random().toString(36).substr(2, 9);
  }

  generateUserId() {
    return "user_" + Math.random().toString(36).substr(2, 9);
  }

  getCurrentSubtitleSegments() {
    // This would get segments from the current subtitle editor
    // Placeholder implementation
    return [];
  }
}

// Initialize Phase 3 when the page loads
document.addEventListener("DOMContentLoaded", () => {
  if (window.FaceSequencerApp && window.FaceSequencerApp.videoEditorModule) {
    window.advancedEditor = new AdvancedVideoEditorPhase3(
      window.FaceSequencerApp
    );
  }
});

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = AdvancedVideoEditorPhase3;
}
