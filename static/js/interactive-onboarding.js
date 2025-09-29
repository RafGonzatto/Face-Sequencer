// Interactive Onboarding System - Guides users through first use
class InteractiveOnboarding {
  constructor(app) {
    this.app = app;
    this.steps = [];
    this.currentStep = 0;
    this.isActive = false;
    this.overlay = null;
    this.tooltip = null;
    this.init();
  }

  init() {
    this.defineSteps();
    this.createOverlay();
    this.createTooltip();

    // Check if user wants onboarding
    if (this.shouldShowOnboarding()) {
      setTimeout(() => this.startOnboarding(), 1000);
    }
  }

  shouldShowOnboarding() {
    // Show onboarding if:
    // 1. First time user (no localStorage flag)
    // 2. No project data exists
    // 3. User explicitly requests help
    const hasUsed = localStorage.getItem("faceSequencer_onboardingCompleted");
    const hasProject =
      this.app.state.project?.text ||
      Object.keys(this.app.state.mappings || {}).length > 0;

    return !hasUsed && !hasProject;
  }

  defineSteps() {
    this.steps = [
      {
        target: ".app-title",
        title: "Welcome to Face Sequencer Pro!",
        content:
          "This tool creates lip-sync animations from text or audio. Let's walk through the basics together.",
        position: "bottom",
        showNext: true,
        showSkip: true,
      },
      {
        target: ".left-panel",
        title: "Configuration Panel",
        content:
          "This is where you'll set up your project. We've organized everything into simple tabs to make it easier.",
        position: "right",
        showNext: true,
        showBack: true,
      },
      {
        target: '[data-tab="setup"]',
        title: "Setup Tab",
        content:
          "Start here to add your character images. You can drag & drop files or browse for a folder.",
        position: "bottom",
        showNext: true,
        showBack: true,
        action: () => this.highlightTab("setup"),
      },
      {
        target: "#folderPath",
        title: "Image Source",
        content:
          "Enter a folder path or click Browse to select where your character mouth images are stored.",
        position: "bottom",
        showNext: true,
        showBack: true,
      },
      {
        target: ".mapping-grid",
        title: "Character Mapping",
        content:
          "Each letter will be mapped to a mouth position image. You can drag images directly onto letters or use auto-mapping.",
        position: "left",
        showNext: true,
        showBack: true,
      },
      {
        target: '[data-tab="content"]',
        title: "Content Tab",
        content:
          "Next, add your content - either text for manual timing or audio for automatic synchronization.",
        position: "bottom",
        showNext: true,
        showBack: true,
        action: () => this.highlightTab("content"),
      },
      {
        target: "#textInput",
        title: "Text Input",
        content:
          "Type the text you want to animate. Each character will be matched to your images.",
        position: "right",
        showNext: true,
        showBack: true,
      },
      {
        target: "#buildSequenceBtn",
        title: "Generate Animation",
        content:
          "When you're ready, click here to generate your lip-sync animation. You can also press Ctrl+Enter.",
        position: "top",
        showNext: true,
        showBack: true,
      },
      {
        target: ".preview-container",
        title: "Preview & Timeline",
        content:
          "Your animation will appear here. Use the timeline below to scrub through frames and make adjustments.",
        position: "left",
        showNext: true,
        showBack: true,
      },
      {
        target: "#exportVideo",
        title: "Export Your Video",
        content:
          "Finally, export your animation as an MP4 video file. You can choose quality settings in the export dialog.",
        position: "bottom",
        showNext: false,
        showBack: true,
        showFinish: true,
      },
    ];
  }

  createOverlay() {
    this.overlay = document.createElement("div");
    this.overlay.className = "onboarding-overlay";
    this.overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.7);
      z-index: 9998;
      display: none;
      pointer-events: none;
    `;
    document.body.appendChild(this.overlay);
  }

  createTooltip() {
    this.tooltip = document.createElement("div");
    this.tooltip.className = "onboarding-tooltip";
    this.tooltip.style.cssText = `
      position: absolute;
      background: white;
      border-radius: 8px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
      padding: 20px;
      max-width: 320px;
      z-index: 9999;
      display: none;
      pointer-events: all;
    `;
    document.body.appendChild(this.tooltip);
  }

  startOnboarding() {
    this.isActive = true;
    this.currentStep = 0;
    this.showStep();

    // Add keyboard listener
    this.keyListener = (e) => this.handleKeyPress(e);
    document.addEventListener("keydown", this.keyListener);
  }

  showStep() {
    const step = this.steps[this.currentStep];
    if (!step) return;

    // Execute step action if any
    if (step.action) step.action();

    // Show overlay and tooltip
    this.overlay.style.display = "block";
    this.tooltip.style.display = "block";

    // Position tooltip
    this.positionTooltip(step);

    // Update tooltip content
    this.updateTooltipContent(step);

    // Highlight target element
    this.highlightTarget(step.target);

    // Announce for screen readers
    this.announceStep(step);
  }

  positionTooltip(step) {
    const target = document.querySelector(step.target);
    if (!target) return;

    const targetRect = target.getBoundingClientRect();
    const tooltipRect = this.tooltip.getBoundingClientRect();

    let top, left;

    switch (step.position) {
      case "top":
        top = targetRect.top - tooltipRect.height - 20;
        left = targetRect.left + (targetRect.width - tooltipRect.width) / 2;
        break;
      case "bottom":
        top = targetRect.bottom + 20;
        left = targetRect.left + (targetRect.width - tooltipRect.width) / 2;
        break;
      case "left":
        top = targetRect.top + (targetRect.height - tooltipRect.height) / 2;
        left = targetRect.left - tooltipRect.width - 20;
        break;
      case "right":
        top = targetRect.top + (targetRect.height - tooltipRect.height) / 2;
        left = targetRect.right + 20;
        break;
      default:
        top = targetRect.bottom + 20;
        left = targetRect.left;
    }

    // Keep tooltip on screen
    top = Math.max(
      10,
      Math.min(top, window.innerHeight - tooltipRect.height - 10)
    );
    left = Math.max(
      10,
      Math.min(left, window.innerWidth - tooltipRect.width - 10)
    );

    this.tooltip.style.top = `${top}px`;
    this.tooltip.style.left = `${left}px`;
  }

  updateTooltipContent(step) {
    const stepNumber = this.currentStep + 1;
    const totalSteps = this.steps.length;

    this.tooltip.innerHTML = `
      <div class="tooltip-header">
        <div class="tooltip-progress">
          <div class="progress-bar">
            <div class="progress-fill" style="width: ${
              (stepNumber / totalSteps) * 100
            }%"></div>
          </div>
          <div class="progress-text">${stepNumber} of ${totalSteps}</div>
        </div>
      </div>
      <div class="tooltip-body">
        <h3 class="tooltip-title">${step.title}</h3>
        <p class="tooltip-content">${step.content}</p>
      </div>
      <div class="tooltip-footer">
        <div class="tooltip-actions">
          ${
            step.showSkip
              ? '<button class="btn-onboarding btn-skip">Skip Tour</button>'
              : ""
          }
          ${
            step.showBack
              ? '<button class="btn-onboarding btn-back">Back</button>'
              : ""
          }
          ${
            step.showNext
              ? '<button class="btn-onboarding btn-next btn-primary">Next</button>'
              : ""
          }
          ${
            step.showFinish
              ? '<button class="btn-onboarding btn-finish btn-primary">Get Started!</button>'
              : ""
          }
        </div>
      </div>
    `;

    // Bind button events
    this.bindTooltipEvents();
  }

  bindTooltipEvents() {
    const nextBtn = this.tooltip.querySelector(".btn-next");
    const backBtn = this.tooltip.querySelector(".btn-back");
    const skipBtn = this.tooltip.querySelector(".btn-skip");
    const finishBtn = this.tooltip.querySelector(".btn-finish");

    if (nextBtn) nextBtn.addEventListener("click", () => this.nextStep());
    if (backBtn) backBtn.addEventListener("click", () => this.prevStep());
    if (skipBtn) skipBtn.addEventListener("click", () => this.skipOnboarding());
    if (finishBtn)
      finishBtn.addEventListener("click", () => this.finishOnboarding());
  }

  highlightTarget(selector) {
    // Remove previous highlights
    document.querySelectorAll(".onboarding-highlight").forEach((el) => {
      el.classList.remove("onboarding-highlight");
    });

    // Add highlight to current target
    const target = document.querySelector(selector);
    if (target) {
      target.classList.add("onboarding-highlight");

      // Create spotlight effect
      const rect = target.getBoundingClientRect();
      const spotlight = document.createElement("div");
      spotlight.className = "onboarding-spotlight";
      spotlight.style.cssText = `
        position: fixed;
        top: ${rect.top - 10}px;
        left: ${rect.left - 10}px;
        width: ${rect.width + 20}px;
        height: ${rect.height + 20}px;
        border: 3px solid #2563eb;
        border-radius: 8px;
        box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.5);
        pointer-events: none;
        z-index: 9998;
        animation: pulse-border 2s infinite;
      `;

      // Remove existing spotlight
      const existingSpotlight = document.querySelector(".onboarding-spotlight");
      if (existingSpotlight) existingSpotlight.remove();

      document.body.appendChild(spotlight);
    }
  }

  highlightTab(tabName) {
    // Switch to the specified tab to show it
    const tab = document.querySelector(`[data-tab="${tabName}"]`);
    if (tab) tab.click();
  }

  nextStep() {
    if (this.currentStep < this.steps.length - 1) {
      this.currentStep++;
      this.showStep();
    }
  }

  prevStep() {
    if (this.currentStep > 0) {
      this.currentStep--;
      this.showStep();
    }
  }

  skipOnboarding() {
    if (
      confirm(
        "Are you sure you want to skip the tour? You can restart it anytime from the help menu."
      )
    ) {
      this.endOnboarding();
    }
  }

  finishOnboarding() {
    localStorage.setItem("faceSequencer_onboardingCompleted", "true");
    this.endOnboarding();

    // Show completion message
    this.showCompletionMessage();
  }

  endOnboarding() {
    this.isActive = false;

    // Hide overlay and tooltip
    this.overlay.style.display = "none";
    this.tooltip.style.display = "none";

    // Remove highlights and spotlight
    document.querySelectorAll(".onboarding-highlight").forEach((el) => {
      el.classList.remove("onboarding-highlight");
    });

    const spotlight = document.querySelector(".onboarding-spotlight");
    if (spotlight) spotlight.remove();

    // Remove keyboard listener
    if (this.keyListener) {
      document.removeEventListener("keydown", this.keyListener);
    }
  }

  showCompletionMessage() {
    const message = document.createElement("div");
    message.className = "onboarding-completion";
    message.innerHTML = `
      <div class="completion-content">
        <div class="completion-icon">🎉</div>
        <h3>You're all set!</h3>
        <p>You've completed the tour and are ready to create amazing lip-sync animations.</p>
        <button class="btn btn-primary" onclick="this.parentElement.parentElement.remove()">
          Start Creating
        </button>
      </div>
    `;

    message.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      z-index: 10000;
      background: white;
      border-radius: 12px;
      padding: 32px;
      text-align: center;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
      max-width: 400px;
    `;

    document.body.appendChild(message);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (message.parentElement) message.remove();
    }, 5000);
  }

  handleKeyPress(e) {
    if (!this.isActive) return;

    switch (e.key) {
      case "Escape":
        this.skipOnboarding();
        break;
      case "ArrowRight":
      case "Enter":
        if (this.currentStep < this.steps.length - 1) {
          this.nextStep();
        } else {
          this.finishOnboarding();
        }
        break;
      case "ArrowLeft":
        this.prevStep();
        break;
    }
  }

  announceStep(step) {
    // For screen readers
    if (window.uxEnhancer?.announceStatus) {
      window.uxEnhancer.announceStatus(`${step.title}: ${step.content}`);
    }
  }

  // Public methods
  restart() {
    this.currentStep = 0;
    this.startOnboarding();
  }

  isRunning() {
    return this.isActive;
  }
}

// Add help menu integration
document.addEventListener("DOMContentLoaded", () => {
  // Add help button to header
  setTimeout(() => {
    const header = document.querySelector(".header-right");
    if (header) {
      const helpBtn = document.createElement("button");
      helpBtn.className = "btn btn-outline btn-sm";
      helpBtn.innerHTML = '<i class="fas fa-question-circle"></i> Help';
      helpBtn.title = "Show interactive tour";

      helpBtn.addEventListener("click", () => {
        if (window.interactiveOnboarding) {
          window.interactiveOnboarding.restart();
        }
      });

      header.insertBefore(helpBtn, header.firstChild);
    }

    // Initialize onboarding
    if (window.faceSequencerApp) {
      window.interactiveOnboarding = new InteractiveOnboarding(
        window.faceSequencerApp
      );
    }
  }, 500);
});
