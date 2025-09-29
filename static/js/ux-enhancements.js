// UX Enhancement Manager - Workflow Improvements
class UXEnhancementManager {
  constructor(app) {
    this.app = app;
    this.currentWizardStep = 0;
    this.wizardData = {};
    this.isFirstTime = !localStorage.getItem("faceSequencer_hasUsed");
    this.init();
  }

  init() {
    this.createWizardModal();
    this.enhanceUploadZones();
    this.addContextualHelp();
    this.improveResponsiveness();
    this.addProgressiveDisclosure();

    // Show wizard for first-time users
    if (this.isFirstTime) {
      this.showWelcomeWizard();
    }
  }

  // ===== WELCOME WIZARD SYSTEM =====
  createWizardModal() {
    const wizardHTML = `
      <div id="welcomeWizard" class="workflow-wizard">
        <div class="wizard-content">
          <div class="wizard-header">
            <h2>Welcome to Face Sequencer Pro!</h2>
            <p>Let's set up your first lip-sync animation in just a few steps</p>
            <div class="wizard-progress">
              <div class="wizard-step active" data-step="0">1</div>
              <div class="wizard-step" data-step="1">2</div>
              <div class="wizard-step" data-step="2">3</div>
              <div class="wizard-step" data-step="3">4</div>
            </div>
          </div>
          
          <div class="wizard-body">
            <!-- Step 1: Choose Template -->
            <div class="wizard-step-content active" data-step="0">
              <h3>Choose Your Project Type</h3>
              <div class="quick-start-cards">
                <div class="quick-start-card" data-template="basic">
                  <div class="card-header">
                    <div class="card-icon"><i class="fas fa-text-width"></i></div>
                    <h4 class="card-title">Text Animation</h4>
                  </div>
                  <p class="card-description">Create lip-sync animation from text input with manual timing control.</p>
                  <ul class="card-features">
                    <li>Perfect for short messages</li>
                    <li>Full control over timing</li>
                    <li>No audio required</li>
                  </ul>
                </div>
                
                <div class="quick-start-card" data-template="audio">
                  <div class="card-header">
                    <div class="card-icon"><i class="fas fa-microphone"></i></div>
                    <h4 class="card-title">Audio Sync</h4>
                  </div>
                  <p class="card-description">Automatic lip-sync from audio file with advanced timing alignment.</p>
                  <ul class="card-features">
                    <li>Automatic timing from audio</li>
                    <li>Perfect synchronization</li>
                    <li>Professional results</li>
                  </ul>
                </div>
                
                <div class="quick-start-card" data-template="advanced">
                  <div class="card-header">
                    <div class="card-icon"><i class="fas fa-cogs"></i></div>
                    <h4 class="card-title">Custom Setup</h4>
                  </div>
                  <p class="card-description">Full control over all settings for experienced users.</p>
                  <ul class="card-features">
                    <li>All features available</li>
                    <li>Maximum customization</li>
                    <li>Expert mode</li>
                  </ul>
                </div>
              </div>
            </div>
            
            <!-- Step 2: Upload Content -->
            <div class="wizard-step-content" data-step="1">
              <h3>Add Your Content</h3>
              <div id="wizardContentStep">
                <!-- Content will be dynamically generated based on template selection -->
              </div>
            </div>
            
            <!-- Step 3: Character Images -->
            <div class="wizard-step-content" data-step="2">
              <h3>Add Character Images</h3>
              <p>Upload images for each character that will appear in your animation.</p>
              <div class="smart-upload-zone" id="wizardImageUpload">
                <div class="upload-icon"><i class="fas fa-images"></i></div>
                <div class="upload-text">Drop your character images here</div>
                <div class="upload-hint">Or click to browse files • Supports PNG, JPG, WEBP</div>
              </div>
              <div class="upload-tips">
                <h4>💡 Tips for best results:</h4>
                <ul>
                  <li>Use images of the same size (recommended: 512x512px)</li>
                  <li>Make sure faces are clearly visible</li>
                  <li>PNG format for transparent backgrounds</li>
                </ul>
              </div>
            </div>
            
            <!-- Step 4: Review & Generate -->
            <div class="wizard-step-content" data-step="3">
              <h3>Review & Generate</h3>
              <div id="wizardReviewContent">
                <!-- Review content will be populated here -->
              </div>
            </div>
          </div>
          
          <div class="wizard-footer">
            <button class="btn btn-secondary" id="wizardPrev" style="display: none;">Previous</button>
            <div class="wizard-footer-center">
              <button class="btn btn-outline" id="wizardSkip">Skip Tutorial</button>
            </div>
            <button class="btn btn-primary" id="wizardNext">Next</button>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML("beforeend", wizardHTML);
    this.bindWizardEvents();
  }

  bindWizardEvents() {
    const wizard = document.getElementById("welcomeWizard");
    const nextBtn = document.getElementById("wizardNext");
    const prevBtn = document.getElementById("wizardPrev");
    const skipBtn = document.getElementById("wizardSkip");

    nextBtn.addEventListener("click", () => this.nextWizardStep());
    prevBtn.addEventListener("click", () => this.prevWizardStep());
    skipBtn.addEventListener("click", () => this.closeWizard());

    // Template selection
    wizard.addEventListener("click", (e) => {
      const card = e.target.closest(".quick-start-card");
      if (card) {
        wizard
          .querySelectorAll(".quick-start-card")
          .forEach((c) => c.classList.remove("selected"));
        card.classList.add("selected");
        this.wizardData.template = card.dataset.template;
      }
    });
  }

  showWelcomeWizard() {
    document.getElementById("welcomeWizard").style.display = "flex";
    document.body.style.overflow = "hidden";
  }

  nextWizardStep() {
    if (this.currentWizardStep === 0 && !this.wizardData.template) {
      this.showNotification(
        "Please select a project type to continue",
        "warning"
      );
      return;
    }

    if (this.currentWizardStep < 3) {
      this.currentWizardStep++;
      this.updateWizardStep();
    } else {
      this.completeWizard();
    }
  }

  prevWizardStep() {
    if (this.currentWizardStep > 0) {
      this.currentWizardStep--;
      this.updateWizardStep();
    }
  }

  updateWizardStep() {
    const wizard = document.getElementById("welcomeWizard");

    // Update progress indicators
    wizard.querySelectorAll(".wizard-step").forEach((step, index) => {
      step.classList.remove("active", "completed");
      if (index < this.currentWizardStep) {
        step.classList.add("completed");
      } else if (index === this.currentWizardStep) {
        step.classList.add("active");
      }
    });

    // Update content visibility
    wizard
      .querySelectorAll(".wizard-step-content")
      .forEach((content, index) => {
        content.classList.remove("active");
        if (index === this.currentWizardStep) {
          content.classList.add("active");
        }
      });

    // Update buttons
    const prevBtn = document.getElementById("wizardPrev");
    const nextBtn = document.getElementById("wizardNext");

    prevBtn.style.display = this.currentWizardStep > 0 ? "block" : "none";
    nextBtn.textContent =
      this.currentWizardStep === 3 ? "Get Started!" : "Next";

    // Update step-specific content
    this.updateWizardStepContent();
  }

  updateWizardStepContent() {
    if (this.currentWizardStep === 1) {
      this.generateContentStep();
    } else if (this.currentWizardStep === 3) {
      this.generateReviewStep();
    }
  }

  generateContentStep() {
    const container = document.getElementById("wizardContentStep");
    const template = this.wizardData.template;

    let contentHTML = "";

    if (template === "audio") {
      contentHTML = `
        <div class="smart-upload-zone" id="wizardAudioUpload">
          <div class="upload-icon"><i class="fas fa-music"></i></div>
          <div class="upload-text">Drop your audio file here</div>
          <div class="upload-hint">Supports MP3, WAV, OGG, FLAC, M4A</div>
        </div>
        <div style="margin-top: 1rem;">
          <label for="wizardTextInput">Transcript (optional but recommended):</label>
          <textarea id="wizardTextInput" class="text-area" placeholder="Enter the text that matches your audio..." rows="3"></textarea>
        </div>
      `;
    } else {
      contentHTML = `
        <div>
          <label for="wizardTextInput">Enter your text:</label>
          <textarea id="wizardTextInput" class="text-area" placeholder="Type the text you want to animate..." rows="4"></textarea>
          <div class="text-stats">
            <span id="wizardCharCount">0 characters</span>
          </div>
        </div>
      `;
    }

    container.innerHTML = contentHTML;

    // Bind events for this step
    const textInput = document.getElementById("wizardTextInput");
    if (textInput) {
      textInput.addEventListener("input", () => {
        this.wizardData.text = textInput.value;
        const charCount = document.getElementById("wizardCharCount");
        if (charCount) {
          charCount.textContent = `${textInput.value.length} characters`;
        }
      });
    }
  }

  completeWizard() {
    // Apply wizard selections to main app
    this.applyWizardSettings();

    // Close wizard
    this.closeWizard();

    // Mark as not first time
    localStorage.setItem("faceSequencer_hasUsed", "true");

    // Show completion message
    this.showNotification(
      "Welcome! Your project has been set up successfully. You can now start creating your animation!",
      "success"
    );
  }

  closeWizard() {
    document.getElementById("welcomeWizard").style.display = "none";
    document.body.style.overflow = "auto";
  }

  applyWizardSettings() {
    // Apply settings based on wizard data
    if (this.wizardData.text) {
      this.app.textInput.value = this.wizardData.text;
      this.app.state.project.text = this.wizardData.text;
    }

    // Configure based on template
    switch (this.wizardData.template) {
      case "basic":
        this.app.state.project.settings.frame_duration = 100;
        this.app.state.project.settings.pause_duration = 150;
        break;
      case "audio":
        // Enable audio features
        const audioToggle = document.getElementById("timingModeToggle");
        if (audioToggle) audioToggle.checked = true;
        break;
      case "advanced":
        // Show all advanced options
        this.showAdvancedSections();
        break;
    }

    this.app.updateUI();
  }

  // ===== ENHANCED UPLOAD ZONES =====
  enhanceUploadZones() {
    this.createSmartAudioUpload();
    this.createSmartImageUpload();
  }

  createSmartAudioUpload() {
    const audioSection = document.querySelector(
      ".section:has(#audioFileInput)"
    );
    if (!audioSection) return;

    const uploadHTML = `
      <div class="smart-upload-zone" id="smartAudioUpload">
        <div class="upload-icon"><i class="fas fa-music"></i></div>
        <div class="upload-text">Drop audio file here or click to browse</div>
        <div class="upload-hint">Supports MP3, WAV, OGG, FLAC, M4A • Max size: 50MB</div>
        <div class="status-indicator" id="audioUploadStatus" style="display: none;">
          <span class="spinner"></span>
          <span>Processing audio...</span>
        </div>
      </div>
    `;

    const inputGroup = audioSection.querySelector(".input-group");
    inputGroup.insertAdjacentHTML("afterbegin", uploadHTML);

    this.bindSmartUpload("smartAudioUpload", "audio");
  }

  createSmartImageUpload() {
    const folderSection = document.querySelector(".section:has(#folderPath)");
    if (!folderSection) return;

    const uploadHTML = `
      <div class="smart-upload-zone" id="smartImageUpload" style="margin-top: 1rem;">
        <div class="upload-icon"><i class="fas fa-images"></i></div>
        <div class="upload-text">Drop character images here</div>
        <div class="upload-hint">Multiple files will be auto-mapped to characters A, B, C...</div>
      </div>
    `;

    folderSection.insertAdjacentHTML("beforeend", uploadHTML);
    this.bindSmartUpload("smartImageUpload", "images");
  }

  bindSmartUpload(zoneId, type) {
    const zone = document.getElementById(zoneId);
    if (!zone) return;

    zone.addEventListener("click", () => {
      if (type === "audio") {
        document.getElementById("audioFileInput").click();
      } else if (type === "images") {
        // Create and trigger file input for multiple images
        const input = document.createElement("input");
        input.type = "file";
        input.multiple = true;
        input.accept = "image/*";
        input.addEventListener("change", (e) => {
          this.handleBatchImageUpload(e.target.files);
        });
        input.click();
      }
    });

    // Drag and drop
    zone.addEventListener("dragenter", (e) => {
      e.preventDefault();
      zone.classList.add("drag-over");
    });

    zone.addEventListener("dragleave", (e) => {
      e.preventDefault();
      if (!zone.contains(e.relatedTarget)) {
        zone.classList.remove("drag-over");
      }
    });

    zone.addEventListener("dragover", (e) => {
      e.preventDefault();
    });

    zone.addEventListener("drop", (e) => {
      e.preventDefault();
      zone.classList.remove("drag-over");

      const files = Array.from(e.dataTransfer.files);
      if (type === "audio") {
        this.handleAudioUpload(files[0]);
      } else if (type === "images") {
        this.handleBatchImageUpload(files);
      }
    });
  }

  handleAudioUpload(file) {
    if (!file || !file.type.startsWith("audio/")) {
      this.showNotification("Please upload a valid audio file", "error");
      return;
    }

    // Show processing status
    const status = document.getElementById("audioUploadStatus");
    if (status) {
      status.style.display = "flex";
    }

    // Trigger the app's audio upload
    const audioInput = document.getElementById("audioFileInput");
    const dt = new DataTransfer();
    dt.items.add(file);
    audioInput.files = dt.files;
    audioInput.dispatchEvent(new Event("change", { bubbles: true }));
  }

  handleBatchImageUpload(files) {
    const imageFiles = files.filter((f) => f.type.startsWith("image/"));
    if (imageFiles.length === 0) {
      this.showNotification("Please upload valid image files", "error");
      return;
    }

    // Use the app's batch mapping functionality
    this.app.processBatchMapping(imageFiles);
    this.showNotification(
      `Uploaded ${imageFiles.length} images for character mapping`,
      "success"
    );
  }

  // ===== CONTEXTUAL HELP SYSTEM =====
  addContextualHelp() {
    const helpData = {
      frameDuration: {
        title: "Frame Duration",
        content:
          "How long each character is displayed in milliseconds. Lower values = faster speech, higher values = slower speech. Typical range: 50-150ms.",
      },
      quality: {
        title: "Video Quality (CRF)",
        content:
          "Lower numbers = higher quality but larger file size. 14-18 = High quality, 20-24 = Medium quality, 25+ = Lower quality.",
      },
      useEnhancedAlignment: {
        title: "Enhanced Audio Alignment",
        content:
          "Uses advanced AI models for better lip-sync accuracy. Recommended for professional results, but takes longer to process.",
      },
      alignmentMethod: {
        title: "Alignment Method",
        content:
          "Auto = Best method chosen automatically, Wav2Vec2 = Most accurate but slower, Whisper = Fast but less precise.",
      },
    };

    Object.entries(helpData).forEach(([elementId, help]) => {
      const element = document.getElementById(elementId);
      if (element && element.parentNode) {
        this.addHelpButton(element.parentNode, help);
      }
    });
  }

  addHelpButton(container, help) {
    const helpButton = document.createElement("div");
    helpButton.className = "contextual-help";
    helpButton.innerHTML = `
      <button class="help-trigger" type="button" aria-label="Help">?</button>
      <div class="help-content">
        <strong>${help.title}</strong><br>
        ${help.content}
      </div>
    `;

    container.appendChild(helpButton);

    const trigger = helpButton.querySelector(".help-trigger");
    const content = helpButton.querySelector(".help-content");

    trigger.addEventListener("click", (e) => {
      e.stopPropagation();
      // Hide other help tooltips
      document.querySelectorAll(".help-content.show").forEach((el) => {
        if (el !== content) el.classList.remove("show");
      });
      content.classList.toggle("show");
    });

    // Hide on outside click
    document.addEventListener("click", () => {
      content.classList.remove("show");
    });
  }

  // ===== PROGRESSIVE DISCLOSURE =====
  addProgressiveDisclosure() {
    const advancedSections = [
      {
        id: "enhancedAlignmentSettings",
        title: "Advanced Audio Settings",
        defaultOpen: false,
      },
      {
        id: "exportModal .export-settings",
        title: "Export Settings",
        defaultOpen: true,
      },
    ];

    // Make certain sections collapsible
    this.makeCollapsible(".section:has(#quality)", "Animation Settings", false);
    this.makeCollapsible(
      ".section:has(#uiLanguageSelect)",
      "Interface Settings",
      false
    );
  }

  makeCollapsible(selector, title, defaultOpen = false) {
    const section = document.querySelector(selector);
    if (!section) return;

    const originalContent = section.innerHTML;
    const sectionId = "collapsible_" + Math.random().toString(36).substr(2, 9);

    section.innerHTML = `
      <div class="collapsible-section">
        <div class="section-header" data-target="${sectionId}">
          <h3 class="section-title">
            <i class="fas fa-chevron-right section-toggle ${
              defaultOpen ? "expanded" : ""
            }"></i>
            ${title}
          </h3>
        </div>
        <div class="section-content ${
          defaultOpen ? "expanded" : ""
        }" id="${sectionId}">
          ${originalContent}
        </div>
      </div>
    `;

    // Bind toggle functionality
    const header = section.querySelector(".section-header");
    header.addEventListener("click", () => {
      this.toggleSection(sectionId);
    });
  }

  toggleSection(sectionId) {
    const content = document.getElementById(sectionId);
    const toggle = document.querySelector(
      `[data-target="${sectionId}"] .section-toggle`
    );

    if (content && toggle) {
      const isExpanded = content.classList.contains("expanded");

      if (isExpanded) {
        content.classList.remove("expanded");
        toggle.classList.remove("expanded");
        content.style.display = "none";
      } else {
        content.classList.add("expanded");
        toggle.classList.add("expanded");
        content.style.display = "block";
      }
    }
  }

  // ===== IMPROVED RESPONSIVENESS =====
  improveResponsiveness() {
    // Add mobile-friendly touch gestures
    this.addTouchGestures();

    // Implement smart panel resizing
    this.implementSmartPanels();

    // Add keyboard shortcuts
    this.addKeyboardShortcuts();
  }

  implementSmartPanels() {
    const panels = document.querySelectorAll(".panel");

    // Add panel toggle buttons for mobile
    panels.forEach((panel, index) => {
      const header = panel.querySelector(".panel-header");
      if (header && window.innerWidth <= 768) {
        const toggleBtn = document.createElement("button");
        toggleBtn.className = "panel-toggle-btn";
        toggleBtn.innerHTML = '<i class="fas fa-chevron-down"></i>';
        header.appendChild(toggleBtn);

        toggleBtn.addEventListener("click", () => {
          panel.classList.toggle("collapsed");
        });
      }
    });
  }

  addKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
      // Ctrl/Cmd + S = Save project
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        if (this.app.saveProjectBtn) this.app.saveProjectBtn.click();
      }

      // Ctrl/Cmd + Enter = Build sequence
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        if (this.app.buildSequenceBtn) this.app.buildSequenceBtn.click();
      }

      // Space = Play/pause preview
      if (e.key === " " && !e.target.matches("input, textarea")) {
        e.preventDefault();
        if (this.app.playing) {
          if (this.app.stopBtn) this.app.stopBtn.click();
        } else {
          if (this.app.playBtn) this.app.playBtn.click();
        }
      }
    });
  }

  // ===== UTILITY METHODS =====
  showNotification(message, type = "info") {
    // Create notification if it doesn't exist
    let notification = document.getElementById("ux-notification");
    if (!notification) {
      notification = document.createElement("div");
      notification.id = "ux-notification";
      notification.className = "status-indicator";
      notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        min-width: 300px;
        padding: 12px 16px;
        border-radius: 6px;
        font-weight: 500;
        transform: translateX(100%);
        transition: transform 0.3s ease;
      `;
      document.body.appendChild(notification);
    }

    // Set type and message
    notification.className = `status-indicator ${type}`;
    notification.textContent = message;

    // Show notification
    notification.style.transform = "translateX(0)";

    // Auto-hide after 5 seconds
    setTimeout(() => {
      notification.style.transform = "translateX(100%)";
    }, 5000);
  }

  showAdvancedSections() {
    // Make all collapsible sections visible
    document
      .querySelectorAll(".collapsible-section .section-content")
      .forEach((section) => {
        section.classList.add("expanded");
        section.style.display = "block";
      });

    document.querySelectorAll(".section-toggle").forEach((toggle) => {
      toggle.classList.add("expanded");
    });
  }
}

// Auto-initialize when app is ready
document.addEventListener("DOMContentLoaded", () => {
  // Wait for main app to initialize
  setTimeout(() => {
    if (window.faceSequencerApp) {
      window.uxEnhancer = new UXEnhancementManager(window.faceSequencerApp);
    }
  }, 200);
});
