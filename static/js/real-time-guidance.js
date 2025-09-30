// Real-time User Guidance System
class RealTimeGuidance {
  constructor(app) {
    this.app = app;
    this.guidancePanel = null;
    this.currentSuggestions = [];
    this.isActive = true;
    this.init();
  }

  init() {
    this.createGuidancePanel();
    this.bindEvents();
    this.startAnalyzing();

    // Make instance globally available for direct calls from HTML
    window.realTimeGuidance = this;
  }

  createGuidancePanel() {
    this.guidancePanel = document.createElement("div");
    this.guidancePanel.className = "guidance-panel";
    this.guidancePanel.innerHTML = `
      <div class="guidance-header">
        <div class="guidance-title">
          <i class="fas fa-lightbulb"></i>
          Smart Suggestions
        </div>
        <button class="guidance-toggle" title="Toggle suggestions">
          <i class="fas fa-chevron-up"></i>
        </button>
      </div>
      <div class="guidance-content">
        <div class="guidance-suggestions"></div>
        <div class="guidance-progress">
          <div class="progress-item" data-step="setup">
            <i class="fas fa-circle-check"></i>
            <span>Setup character images</span>
          </div>
          <div class="progress-item" data-step="content">
            <i class="fas fa-circle"></i>
            <span>Add text or audio content</span>
          </div>
          <div class="progress-item" data-step="generate">
            <i class="fas fa-circle"></i>
            <span>Generate animation</span>
          </div>
          <div class="progress-item" data-step="export">
            <i class="fas fa-circle"></i>
            <span>Export final video</span>
          </div>
        </div>
      </div>
    `;

    // Position panel
    this.guidancePanel.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      width: 320px;
      max-height: 400px;
      background: white;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
      z-index: 1000;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      overflow: hidden;
      transition: all 0.3s ease;
    `;

    document.body.appendChild(this.guidancePanel);

    // Bind toggle
    this.guidancePanel
      .querySelector(".guidance-toggle")
      .addEventListener("click", () => {
        this.togglePanel();
      });
  }

  bindEvents() {
    // Monitor form changes
    document.addEventListener("input", (e) => this.onInputChange(e));
    document.addEventListener("change", (e) => this.onInputChange(e));

    // Monitor button clicks
    document.addEventListener("click", (e) => this.onButtonClick(e));

    // Monitor file operations
    if (this.app) {
      // Hook into app state changes
      const originalSetState = this.app.setState?.bind(this.app);
      if (originalSetState) {
        this.app.setState = (...args) => {
          const result = originalSetState(...args);
          this.analyzeCurrentState();
          return result;
        };
      }
    }
  }

  startAnalyzing() {
    // Initial analysis
    this.analyzeCurrentState();

    // Periodic analysis
    setInterval(() => {
      if (this.isActive) {
        this.analyzeCurrentState();
      }
    }, 2000);
  }

  // Handle input changes from form fields
  onInputChange(e) {
    // When input fields change, analyze the current state
    setTimeout(() => this.analyzeCurrentState(), 100);
  }

  analyzeCurrentState() {
    const suggestions = [];
    const progress = this.assessProgress();

    // Analyze based on current state
    if (!this.hasImages()) {
      suggestions.push({
        type: "setup",
        priority: "high",
        icon: "fas fa-images",
        title: "Add Character Images",
        message: "Start by adding mouth position images for your character.",
        action: () => this.focusElement("#folderPath"),
        actionText: "Browse Images",
      });
    } else if (!this.hasValidMappings()) {
      suggestions.push({
        type: "setup",
        priority: "high",
        icon: "fas fa-link",
        title: "Map Characters to Images",
        message:
          "Drag images onto letters or use auto-mapping to connect characters with mouth positions.",
        action: () => this.switchToTab("setup"),
        actionText: "Setup Mappings",
      });
    }

    if (this.hasValidMappings() && !this.hasContent()) {
      suggestions.push({
        type: "content",
        priority: "high",
        icon: "fas fa-font",
        title: "Add Text Content",
        message:
          "Enter the text you want to animate, or upload an audio file for automatic sync.",
        action: () => this.focusElement("#textInput"),
        actionText: "Add Text",
      });
    }

    if (this.hasContent() && this.hasValidMappings() && !this.hasSequence()) {
      suggestions.push({
        type: "generate",
        priority: "high",
        icon: "fas fa-play",
        title: "Generate Animation",
        message:
          "Everything is ready! Click to generate your lip-sync animation.",
        action: () => this.clickElement("#buildSequenceBtn"),
        actionText: "Generate Now",
      });
    }

    if (this.hasSequence() && !this.hasExported()) {
      suggestions.push({
        type: "export",
        priority: "medium",
        icon: "fas fa-download",
        title: "Export Video",
        message: "Your animation looks great! Export it as an MP4 video file.",
        action: () => this.clickElement("#exportVideo"),
        actionText: "Export Video",
      });
    }

    // Performance suggestions
    if (this.isLongSequence()) {
      suggestions.push({
        type: "performance",
        priority: "low",
        icon: "fas fa-tachometer-alt",
        title: "Optimize Performance",
        message:
          "For long sequences, consider reducing frame rate or using smaller images.",
        action: () => this.showPerformanceTips(),
        actionText: "Learn More",
      });
    }

    // Quality suggestions
    if (this.hasLowQualityImages()) {
      suggestions.push({
        type: "quality",
        priority: "medium",
        icon: "fas fa-exclamation-triangle",
        title: "Image Quality Notice",
        message:
          "Some images are low resolution. Consider using higher quality images for better results.",
        action: () => this.showQualityTips(),
        actionText: "Tips",
      });
    }

    this.updateSuggestions(suggestions);
    this.updateProgress(progress);
  }

  assessProgress() {
    const progress = {
      setup: this.hasImages() && this.hasValidMappings(),
      content: this.hasContent(),
      generate: this.hasSequence(),
      export: this.hasExported(),
    };

    return progress;
  }

  // State detection methods
  hasImages() {
    const folderPath = document.getElementById("folderPath")?.value;
    return folderPath && folderPath.trim().length > 0;
  }

  hasValidMappings() {
    const mappings = this.app?.state?.mappings || {};
    return Object.keys(mappings).length > 0;
  }

  hasContent() {
    const text = document.getElementById("textInput")?.value;
    const hasAudio = this.app?.state?.audioData;
    return (text && text.trim().length > 0) || hasAudio;
  }

  hasSequence() {
    return this.app?.state?.sequence?.length > 0;
  }

  hasExported() {
    // Check if export was recently performed
    return (
      localStorage.getItem("lastExportTime") &&
      Date.now() - parseInt(localStorage.getItem("lastExportTime")) < 300000
    ); // 5 minutes
  }

  isLongSequence() {
    return (this.app?.state?.sequence?.length || 0) > 300; // More than 10 seconds at 30fps
  }

  hasLowQualityImages() {
    // This would need to be implemented based on image analysis
    return false;
  }

  // UI update methods
  updateSuggestions(suggestions) {
    this.currentSuggestions = suggestions;
    const container = this.guidancePanel.querySelector(".guidance-suggestions");

    if (suggestions.length === 0) {
      container.innerHTML = `
        <div class="no-suggestions">
          <i class="fas fa-check-circle"></i>
          <p>You're all set! Everything looks good.</p>
        </div>
      `;
      return;
    }

    // Show top 2 most important suggestions
    const topSuggestions = suggestions
      .sort((a, b) => {
        const priorities = { high: 3, medium: 2, low: 1 };
        return priorities[b.priority] - priorities[a.priority];
      })
      .slice(0, 2);

    container.innerHTML = topSuggestions
      .map(
        (suggestion, index) => `
      <div class="suggestion-item priority-${suggestion.priority}" data-type="${suggestion.type}" data-index="${index}" tabindex="0" role="button">
        <div class="suggestion-icon">
          <i class="${suggestion.icon}"></i>
        </div>
        <div class="suggestion-content">
          <div class="suggestion-title">${suggestion.title}</div>
          <div class="suggestion-message">${suggestion.message}</div>
          <button class="suggestion-action btn btn-sm btn-primary" data-type="${suggestion.type}" data-index="${index}">
            ${suggestion.actionText}
          </button>
        </div>
      </div>
    `
      )
      .join("");

    // Add click event listeners to suggestions and buttons
    setTimeout(() => {
      // Add click handlers for all suggestion items
      const items = container.querySelectorAll(".suggestion-item");
      items.forEach((item, idx) => {
        const suggestionIndex = parseInt(item.dataset.index);
        const suggestion = topSuggestions[suggestionIndex];

        // Make the whole suggestion clickable
        item.addEventListener("click", (e) => {
          if (!e.target.closest(".suggestion-action")) {
            this.executeSuggestionByIndex(suggestionIndex);
          }
        });

        // Make it keyboard accessible
        item.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            this.executeSuggestionByIndex(suggestionIndex);
            e.preventDefault();
          }
        });

        // Handle button clicks
        const button = item.querySelector(".suggestion-action");
        if (button) {
          button.addEventListener("click", () => {
            this.executeSuggestionByIndex(suggestionIndex);
          });
        }
      });
    }, 0);
  }

  // Execute a suggestion by its index in the current suggestions array
  executeSuggestionByIndex(index) {
    const suggestion = this.currentSuggestions[index];
    if (suggestion && suggestion.action) {
      suggestion.action();
    } else {
      this.executeSuggestion(suggestion?.type || "setup");
    }
  }

  updateProgress(progress) {
    const progressItems = this.guidancePanel.querySelectorAll(".progress-item");

    progressItems.forEach((item) => {
      const step = item.dataset.step;
      const icon = item.querySelector("i");

      if (progress[step]) {
        icon.className = "fas fa-circle-check";
        item.classList.add("completed");
      } else {
        icon.className = "fas fa-circle";
        item.classList.remove("completed");
      }
    });
  }

  // Action methods
  executeSuggestion(type) {
    const suggestion = this.currentSuggestions.find((s) => s.type === type);
    if (suggestion && suggestion.action) {
      suggestion.action();
    }
  }

  focusElement(selector) {
    const element = document.querySelector(selector);
    if (element) {
      element.focus();
      element.scrollIntoView({ behavior: "smooth", block: "center" });

      // Add temporary highlight
      element.classList.add("guidance-highlight");
      setTimeout(() => element.classList.remove("guidance-highlight"), 2000);
    }
  }

  clickElement(selector) {
    const element = document.querySelector(selector);
    if (element) {
      element.click();
    }
  }

  switchToTab(tabName) {
    const tab = document.querySelector(`[data-tab="${tabName}"]`);
    if (tab) {
      tab.click();
    }
  }

  togglePanel() {
    const content = this.guidancePanel.querySelector(".guidance-content");
    const toggle = this.guidancePanel.querySelector(".guidance-toggle i");

    const isCollapsed = content.style.display === "none";

    content.style.display = isCollapsed ? "block" : "none";
    toggle.className = isCollapsed
      ? "fas fa-chevron-up"
      : "fas fa-chevron-down";

    this.isActive = isCollapsed;
  }

  showPerformanceTips() {
    alert(`Performance Tips:
• Use smaller image files (under 500KB each)
• Reduce frame rate for longer sequences
• Consider shorter text segments for complex animations
• Use compressed image formats like WebP`);
  }

  showQualityTips() {
    alert(`Quality Tips:
• Use high-resolution images (at least 512x512px)
• Ensure consistent lighting across mouth positions
• Use clear, sharp images without blur
• Keep consistent character positioning`);
  }

  // Public methods
  hide() {
    this.guidancePanel.style.display = "none";
  }

  show() {
    this.guidancePanel.style.display = "block";
  }

  destroy() {
    if (this.guidancePanel) {
      this.guidancePanel.remove();
    }
  }

  onButtonClick(event) {
    const target = event.target;
    const button = target.closest("button");

    if (!button) return;

    // Provide guidance based on button type
    const buttonId = button.id || button.className;
    const buttonText = button.textContent?.toLowerCase() || "";

    // Upload button guidance
    if (buttonText.includes("upload") || buttonId.includes("upload")) {
      this.showGuidance("upload_guidance", {
        title: "Upload Video",
        message:
          "Select a video file to start creating your lip-sync animation.",
        type: "info",
      });
    }

    // Export button guidance
    else if (buttonText.includes("export") || buttonId.includes("export")) {
      this.showGuidance("export_guidance", {
        title: "Export Options",
        message: "Choose your export format and quality settings.",
        type: "info",
      });
    }

    // Play/pause button guidance
    else if (buttonText.includes("play") || buttonText.includes("pause")) {
      this.showGuidance("playback_guidance", {
        title: "Playback Controls",
        message: "Use playback controls to review your animation.",
        type: "tip",
      });
    }
  }
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    if (window.faceSequencerApp) {
      window.realTimeGuidance = new RealTimeGuidance(window.faceSequencerApp);
    }
  }, 1000);
});
