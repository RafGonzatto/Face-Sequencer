// Smart Panel Manager - Reduces cognitive overload by organizing interface intelligently
class SmartPanelManager {
  constructor(app) {
    this.app = app;
    this.currentTab = "setup";
    try {
      if (!document.querySelector(".left-panel")) {
        console.warn(
          "[SmartPanels] .left-panel not found – disabling SmartPanelManager"
        );
        this.disabled = true;
        return;
      }
      this.init();
    } catch (err) {
      console.error("[SmartPanels] Initialization failed:", err);
      this.disabled = true;
    }
  }

  init() {
    this.createTabSystem();
    this.optimizeLayout();
    this.addSmartHiding();
    this.improveWorkflow();
  }

  // ===== TAB SYSTEM FOR BETTER ORGANIZATION =====
  createTabSystem() {
    const leftPanel = document.querySelector(".left-panel");
    if (!leftPanel) return;

    // Create tab navigation
    const tabNav = document.createElement("div");
    tabNav.className = "smart-tabs-nav";
    tabNav.innerHTML = `
      <button class="smart-tab active" data-tab="setup">
        <i class="fas fa-cog"></i> Setup
      </button>
      <button class="smart-tab" data-tab="content">
        <i class="fas fa-edit"></i> Content
      </button>
      <button class="smart-tab" data-tab="advanced">
        <i class="fas fa-sliders-h"></i> Advanced
      </button>
    `;

    // Insert after panel header
    const panelHeader = leftPanel.querySelector(".panel-header");
    panelHeader.insertAdjacentElement("afterend", tabNav);

    // Organize existing sections into tabs
    this.organizeSectionsIntoTabs();
    this.bindTabEvents();
  }

  organizeSectionsIntoTabs() {
    const sections = document.querySelectorAll(".left-panel .section");

    // Define which sections belong to which tabs
    const tabMapping = {
      setup: ["folderPath", "fallback", "space"], // Image source, fallback, space image
      content: ["textInput", "audioFileInput"], // Text input, audio upload
      advanced: [
        "frameDuration",
        "quality",
        "useEnhancedAlignment",
        "uiLanguageSelect",
      ], // Settings
    };

    // Create tab containers
    const tabContainers = {};
    ["setup", "content", "advanced"].forEach((tabName) => {
      const container = document.createElement("div");
      container.className = `smart-tab-content ${
        tabName === "setup" ? "active" : ""
      }`;
      container.dataset.tab = tabName;
      tabContainers[tabName] = container;
    });

    // Move sections to appropriate tabs
    sections.forEach((section) => {
      let targetTab = "advanced"; // Default tab

      // Find which tab this section belongs to
      Object.entries(tabMapping).forEach(([tab, elements]) => {
        elements.forEach((elementId) => {
          if (section.querySelector(`#${elementId}`)) {
            targetTab = tab;
          }
        });
      });

      // Clone section to target tab
      const sectionClone = section.cloneNode(true);
      tabContainers[targetTab].appendChild(sectionClone);
    });

    // Replace original sections with tab containers
    const firstSection = sections[0];
    const parent = firstSection.parentNode;

    // Remove original sections
    sections.forEach((section) => section.remove());

    // Add tab containers
    Object.values(tabContainers).forEach((container) => {
      parent.appendChild(container);
    });

    // Add action buttons to content tab
    const actionButtons = document.querySelector(".action-buttons");
    if (actionButtons) {
      const actionContainer = document.createElement("div");
      actionContainer.className = "section";
      actionContainer.appendChild(actionButtons.cloneNode(true));
      tabContainers.content.appendChild(actionContainer);
      actionButtons.closest(".section").remove();
    }
  }

  bindTabEvents() {
    document.addEventListener("click", (e) => {
      const tab = e.target.closest(".smart-tab");
      if (!tab) return;

      const tabName = tab.dataset.tab;
      this.switchTab(tabName);
    });
  }

  switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll(".smart-tab").forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll(".smart-tab-content").forEach((content) => {
      content.classList.toggle("active", content.dataset.tab === tabName);
    });

    this.currentTab = tabName;
    this.updateTabIndicators();
  }

  updateTabIndicators() {
    // Add completion indicators to tabs
    const setupComplete = this.checkSetupComplete();
    const contentComplete = this.checkContentComplete();

    const setupTab = document.querySelector('[data-tab="setup"]');
    const contentTab = document.querySelector('[data-tab="content"]');

    if (setupTab) {
      setupTab.classList.toggle("completed", setupComplete);
    }
    if (contentTab) {
      contentTab.classList.toggle("completed", contentComplete);
    }
  }

  checkSetupComplete() {
    const folderPath = document.getElementById("folderPath")?.value;
    const hasMappings = Object.keys(this.app.state.mappings || {}).length > 0;
    return !!(folderPath && hasMappings);
  }

  checkContentComplete() {
    const hasText = document.getElementById("textInput")?.value?.trim();
    const hasAudio = this.app.state.project?.audio_file;
    return !!(hasText || hasAudio);
  }

  // ===== SMART WORKFLOW GUIDANCE =====
  improveWorkflow() {
    if (this.disabled) return;
    // Add workflow indicator
    this.addWorkflowIndicator();

    // Add smart suggestions
    this.addSmartSuggestions();

    // Auto-advance workflow when possible
    this.setupAutoAdvance();
  }

  addWorkflowIndicator() {
    const indicator = document.createElement("div");
    indicator.className = "workflow-indicator";
    indicator.innerHTML = `
      <div class="workflow-step" data-step="setup">
        <div class="step-number">1</div>
        <div class="step-info">
          <div class="step-title">Setup Images</div>
          <div class="step-desc">Add character images</div>
        </div>
      </div>
      <div class="workflow-step" data-step="content">
        <div class="step-number">2</div>
        <div class="step-info">
          <div class="step-title">Add Content</div>
          <div class="step-desc">Text or audio input</div>
        </div>
      </div>
      <div class="workflow-step" data-step="generate">
        <div class="step-number">3</div>
        <div class="step-info">
          <div class="step-title">Generate</div>
          <div class="step-desc">Build animation</div>
        </div>
      </div>
    `;

    const leftPanel = document.querySelector(".left-panel");
    const tabNav = document.querySelector(".smart-tabs-nav");
    if (tabNav) {
      tabNav.insertAdjacentElement("afterend", indicator);
    }

    this.updateWorkflowIndicator();
  }

  updateWorkflowIndicator() {
    const setupComplete = this.checkSetupComplete();
    const contentComplete = this.checkContentComplete();

    // Update step states
    const steps = document.querySelectorAll(".workflow-step");

    if (steps[0]) {
      // Setup step
      steps[0].classList.toggle("completed", setupComplete);
      steps[0].classList.toggle("active", !setupComplete);
    }

    if (steps[1]) {
      // Content step
      steps[1].classList.toggle("completed", contentComplete);
      steps[1].classList.toggle("active", setupComplete && !contentComplete);
    }

    if (steps[2]) {
      // Generate step
      steps[2].classList.toggle("active", setupComplete && contentComplete);
    }
  }

  addSmartSuggestions() {
    // Create suggestion system
    const suggestionContainer = document.createElement("div");
    suggestionContainer.className = "smart-suggestions";
    suggestionContainer.id = "smartSuggestions";

    const leftPanel = document.querySelector(".left-panel");
    if (!leftPanel) {
      console.warn(
        "[SmartPanels] Cannot append suggestions, .left-panel missing"
      );
      return;
    }
    leftPanel.appendChild(suggestionContainer);

    // Update suggestions based on current state
    this.updateSuggestions();
  }

  updateSuggestions() {
    const container = document.getElementById("smartSuggestions");
    if (!container) return;

    const suggestions = this.getSuggestions();

    if (suggestions.length === 0) {
      container.style.display = "none";
      return;
    }

    container.style.display = "block";
    container.innerHTML = `
      <div class="suggestion-header">
        <i class="fas fa-lightbulb"></i>
        <span>Smart Suggestions</span>
      </div>
      ${suggestions
        .map(
          (suggestion) => `
        <div class="suggestion-item" ${
          suggestion.action ? `data-action="${suggestion.action}"` : ""
        }>
          <div class="suggestion-icon">
            <i class="${suggestion.icon}"></i>
          </div>
          <div class="suggestion-content">
            <div class="suggestion-title">${suggestion.title}</div>
            <div class="suggestion-desc">${suggestion.description}</div>
          </div>
          ${
            suggestion.action
              ? '<div class="suggestion-arrow"><i class="fas fa-chevron-right"></i></div>'
              : ""
          }
        </div>
      `
        )
        .join("")}
    `;
    // Bind suggestion actions (guard against duplicate binding on refresh)
    if (!container.dataset.bound) {
      container.addEventListener("click", (e) => {
        const item = e.target.closest(".suggestion-item");
        if (item?.dataset.action) {
          console.log("[SmartSuggestions] click action", item.dataset.action);
          this.executeSuggestion(item.dataset.action);
        }
      });
      container.dataset.bound = "1";
    }

    // Acessibilidade + teclado
    container
      .querySelectorAll(".suggestion-item[data-action]")
      .forEach((el) => {
        el.tabIndex = 0;
        el.setAttribute("role", "button");
        // Remove potential previous keydown to avoid stacking by cloning node pattern not used here
        el.onkeydown = (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            console.log("[SmartSuggestions] key action", el.dataset.action);
            this.executeSuggestion(el.dataset.action);
          }
        };
      });
  }

  getSuggestions() {
    const suggestions = [];
    if (this.disabled) return;
    const setupComplete = this.checkSetupComplete();
    const contentComplete = this.checkContentComplete();
    const hasSequence = this.app.state.sequence?.length > 0;

    if (!setupComplete) {
      if (!document.getElementById("folderPath")?.value) {
        suggestions.push({
          title: "Add Character Images",
          description: "Upload or browse for character mouth images",
          icon: "fas fa-images",
          action: "browse_folder",
        });
      } else if (Object.keys(this.app.state.mappings || {}).length === 0) {
        suggestions.push({
          title: "Scan for Images",
          description: "Scan your folder to find character images",
          icon: "fas fa-search",
          action: "scan_folder",
        });
      }
    } else if (!contentComplete) {
      suggestions.push({
        title: "Add Your Content",
        description: "Enter text or upload audio for lip-sync",
        icon: "fas fa-edit",
        action: "switch_content_tab",
      });
    } else if (!hasSequence) {
      suggestions.push({
        title: "Generate Animation",
        description: "Ready to build your lip-sync animation!",
        icon: "fas fa-play",
        action: "build_sequence",
      });
    } else {
      suggestions.push({
        title: "Export Video",
        description: "Your animation is ready for export",
        icon: "fas fa-download",
        action: "export_video",
      });
    }

    return suggestions;
  }

  executeSuggestion(action) {
    console.log("[SmartSuggestions] executeSuggestion", action);
    switch (action) {
      case "browse_folder":
        document.getElementById("browseFolderBtn")?.click();
        break;
      case "scan_folder":
        document.getElementById("scanFolderBtn")?.click();
        break;
      case "switch_content_tab":
        this.switchTab("content");
        break;
      case "build_sequence":
        document.getElementById("buildSequenceBtn")?.click();
        break;
      case "export_video":
        document.getElementById("exportVideo")?.click();
        break;
      default:
        console.warn("[SmartSuggestions] Unhandled action", action);
    }
  }

  setupAutoAdvance() {
    // Auto-advance to next tab when current is complete
    const checkAndAdvance = () => {
      if (this.currentTab === "setup" && this.checkSetupComplete()) {
        setTimeout(() => this.switchTab("content"), 1000);
      }
    };

    // Listen for state changes
    document.addEventListener("folderScanned", checkAndAdvance);
    document.addEventListener("mappingsUpdated", checkAndAdvance);
  }

  // ===== LAYOUT OPTIMIZATION =====
  optimizeLayout() {
    try {
      this.addLayoutToggle();
    } catch (e) {
      console.warn("[SmartPanels] addLayoutToggle skipped:", e.message);
    }
    try {
      this.improvePreviewArea();
    } catch (e) {
      console.warn("[SmartPanels] improvePreviewArea skipped:", e.message);
    }
  }

  addLayoutToggle() {
    // Defensive layout toggle insertion
    const header = document.querySelector(".app-header");
    if (!header) {
      throw new Error("app-header not found");
    }
    const headerRight = header.querySelector(".header-right");
    if (!headerRight) {
      throw new Error("header-right not found");
    }
    if (headerRight.querySelector(".layout-toggle")) return; // avoid duplicates
    const toggleBtn = document.createElement("button");
    toggleBtn.className = "btn btn-outline btn-sm layout-toggle";
    toggleBtn.type = "button";
    toggleBtn.setAttribute("aria-label", "Toggle compact layout");
    toggleBtn.innerHTML = '<i class="fas fa-table"></i>';
    toggleBtn.title = "Toggle Layout";
    headerRight.insertBefore(toggleBtn, headerRight.firstChild || null);
    toggleBtn.addEventListener("click", () => {
      document.body.classList.toggle("compact-layout");
    });
  }

  improvePreviewArea() {
    // Make preview area more prominent when sequence is ready
    const rightPanel = document.querySelector(".right-panel");
    if (!rightPanel) return;

    // Add preview enhancement
    const previewContainer = rightPanel.querySelector(".preview-container");
    if (previewContainer) {
      previewContainer.classList.add("enhanced-preview");
    }
  }

  // ===== SMART HIDING =====
  addSmartHiding() {
    // Hide irrelevant options based on current mode
    this.setupConditionalDisplay();
  }

  setupConditionalDisplay() {
    // Show/hide audio options based on timing mode
    const timingToggle = document.getElementById("timingModeToggle");
    const audioSections = document.querySelectorAll(
      '[id*="audio"], [id*="enhanced"]'
    );

    if (timingToggle) {
      const updateAudioVisibility = () => {
        const isAudioMode = timingToggle.checked;
        audioSections.forEach((section) => {
          const parent = section.closest(".section");
          if (parent) {
            parent.style.display = isAudioMode ? "block" : "none";
          }
        });
      };

      timingToggle.addEventListener("change", updateAudioVisibility);
      updateAudioVisibility(); // Initial state
    }
  }

  // ===== PUBLIC METHODS =====
  refresh() {
    if (this.disabled) return;
    this.updateTabIndicators();
    this.updateWorkflowIndicator();
    this.updateSuggestions();
  }

  setCurrentTab(tabName) {
    this.switchTab(tabName);
  }
}

// Initialize when UX enhancer is ready
document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    if (window.faceSequencerApp && window.uxEnhancer) {
      window.smartPanelManager = new SmartPanelManager(window.faceSequencerApp);

      // Refresh panel state when app state changes
      const originalUpdateUI = window.faceSequencerApp.updateUI;
      window.faceSequencerApp.updateUI = function () {
        originalUpdateUI.call(this);
        if (window.smartPanelManager) {
          window.smartPanelManager.refresh();
        }
      };
    }
  }, 300);
});
