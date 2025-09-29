// Expandable Timeline Controller
class ExpandableTimeline {
  constructor() {
    this.container = null;
    this.content = null;
    this.resizeHandle = null;
    this.expandBtn = null;
    this.collapseBtn = null;
    this.heightSlider = null;
    this.isExpanded = false;
    this.isResizing = false;
    this.originalHeight = 300;
    this.zoomLevel = 1;

    this.init();
  }

  init() {
    this.bindElements();
    this.bindEvents();
    this.setupKeyboardShortcuts();
    this.restoreSettings();

    console.log("ExpandableTimeline initialized");
  }

  bindElements() {
    this.container = document.getElementById("timelineContainer");
    this.content = document.getElementById("timelineContent");
    this.resizeHandle = document.getElementById("timelineResizeHandle");
    this.expandBtn = document.getElementById("timelineExpandBtn");
    this.collapseBtn = document.getElementById("timelineCollapseBtn");
    this.heightSlider = document.getElementById("timelineHeightSlider");

    if (!this.container) {
      console.warn("Timeline container not found");
      return;
    }

    // Create zoom controls
    this.createZoomControls();

    // Create navigation controls for expanded mode
    this.createNavigationControls();
  }

  bindEvents() {
    if (!this.container) return;

    // Expand/Collapse buttons
    if (this.expandBtn) {
      this.expandBtn.addEventListener("click", () => this.expand());
    }

    if (this.collapseBtn) {
      this.collapseBtn.addEventListener("click", () => this.collapse());
    }

    // Height slider
    if (this.heightSlider) {
      this.heightSlider.addEventListener("input", (e) => {
        this.setHeight(parseInt(e.target.value));
      });
    }

    // Resize handle
    if (this.resizeHandle) {
      this.resizeHandle.addEventListener("mousedown", (e) =>
        this.startResize(e)
      );
    }

    // Document events for resizing
    document.addEventListener("mousemove", (e) => this.handleResize(e));
    document.addEventListener("mouseup", () => this.stopResize());

    // Window resize
    window.addEventListener("resize", () => this.handleWindowResize());

    // Escape key to collapse
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.isExpanded) {
        this.collapse();
      }
    });

    // Click outside to collapse (optional)
    document.addEventListener("click", (e) => {
      if (this.isExpanded && !this.container.contains(e.target)) {
        // Only collapse if clicked on overlay area
        if (e.target.classList.contains("timeline-overlay")) {
          this.collapse();
        }
      }
    });
  }

  createZoomControls() {
    const controls = this.container.querySelector(".timeline-controls");
    if (!controls) return;

    const zoomControls = document.createElement("div");
    zoomControls.className = "timeline-zoom-controls";
    zoomControls.innerHTML = `
      <button class="btn btn-outline btn-xs" id="zoomOutBtn" title="Zoom Out">
        <i class="fas fa-minus"></i>
      </button>
      <span class="zoom-level" id="zoomLevel">100%</span>
      <button class="btn btn-outline btn-xs" id="zoomInBtn" title="Zoom In">
        <i class="fas fa-plus"></i>
      </button>
      <button class="btn btn-outline btn-xs" id="zoomFitBtn" title="Fit to View">
        <i class="fas fa-compress"></i>
      </button>
    `;

    controls.appendChild(zoomControls);

    // Bind zoom events
    document
      .getElementById("zoomInBtn")
      ?.addEventListener("click", () => this.zoomIn());
    document
      .getElementById("zoomOutBtn")
      ?.addEventListener("click", () => this.zoomOut());
    document
      .getElementById("zoomFitBtn")
      ?.addEventListener("click", () => this.zoomToFit());
  }

  createNavigationControls() {
    const navigation = document.createElement("div");
    navigation.className = "timeline-navigation";
    navigation.innerHTML = `
      <button class="btn btn-outline btn-sm" id="timelineCloseBtn" title="Close Expanded View">
        <i class="fas fa-times"></i> Close
      </button>
      <button class="btn btn-outline btn-sm" id="timelineFullscreenBtn" title="Toggle Fullscreen">
        <i class="fas fa-expand"></i>
      </button>
    `;

    this.container.appendChild(navigation);

    // Bind navigation events
    document
      .getElementById("timelineCloseBtn")
      ?.addEventListener("click", () => this.collapse());
    document
      .getElementById("timelineFullscreenBtn")
      ?.addEventListener("click", () => this.toggleFullscreen());
  }

  expand() {
    if (this.isExpanded) return;

    this.isExpanded = true;
    this.originalHeight = this.container.offsetHeight;

    // Add expanded class
    this.container.classList.add("expanding");
    this.container.classList.add("expanded");

    // Update buttons
    if (this.expandBtn) this.expandBtn.style.display = "none";
    if (this.collapseBtn) this.collapseBtn.style.display = "inline-flex";

    // Create overlay
    this.createOverlay();

    // Disable body scroll
    document.body.style.overflow = "hidden";

    // Animation cleanup
    setTimeout(() => {
      this.container.classList.remove("expanding");
    }, 300);

    // Save state
    this.saveSettings();

    // Announce for screen readers
    this.announceChange("Timeline expanded to fullscreen view");

    // Fire custom event
    this.container.dispatchEvent(new CustomEvent("timeline-expanded"));
  }

  collapse() {
    if (!this.isExpanded) return;

    this.isExpanded = false;

    // Add collapsing class
    this.container.classList.add("collapsing");
    this.container.classList.remove("expanded");

    // Update buttons
    if (this.expandBtn) this.expandBtn.style.display = "inline-flex";
    if (this.collapseBtn) this.collapseBtn.style.display = "none";

    // Remove overlay
    this.removeOverlay();

    // Restore body scroll
    document.body.style.overflow = "";

    // Restore height
    this.container.style.height = this.originalHeight + "px";

    // Animation cleanup
    setTimeout(() => {
      this.container.classList.remove("collapsing");
    }, 300);

    // Save state
    this.saveSettings();

    // Announce for screen readers
    this.announceChange("Timeline collapsed to normal view");

    // Fire custom event
    this.container.dispatchEvent(new CustomEvent("timeline-collapsed"));
  }

  createOverlay() {
    const overlay = document.createElement("div");
    overlay.className = "timeline-overlay";
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      z-index: 999;
      backdrop-filter: blur(4px);
    `;

    document.body.appendChild(overlay);
  }

  removeOverlay() {
    const overlay = document.querySelector(".timeline-overlay");
    if (overlay) {
      overlay.remove();
    }
  }

  setHeight(height) {
    if (this.isExpanded) return; // Don't resize when expanded

    height = Math.max(200, Math.min(600, height));
    this.container.style.height = height + "px";

    if (this.heightSlider) {
      this.heightSlider.value = height;
    }

    this.saveSettings();
  }

  startResize(e) {
    if (this.isExpanded) return;

    this.isResizing = true;
    this.startY = e.clientY;
    this.startHeight = this.container.offsetHeight;

    document.body.style.cursor = "ns-resize";
    document.body.style.userSelect = "none";

    e.preventDefault();
  }

  handleResize(e) {
    if (!this.isResizing || this.isExpanded) return;

    const deltaY = e.clientY - this.startY;
    const newHeight = this.startHeight + deltaY;

    this.setHeight(newHeight);
  }

  stopResize() {
    if (!this.isResizing) return;

    this.isResizing = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }

  handleWindowResize() {
    if (this.isExpanded) {
      // Recalculate expanded size if needed
      this.updateExpandedSize();
    }
  }

  updateExpandedSize() {
    // This method can be used to adjust the timeline when window resizes in expanded mode
    if (!this.isExpanded) return;

    // Force recalculation of timeline layout
    if (window.faceSequencerApp && window.faceSequencerApp.renderTimeline) {
      setTimeout(() => window.faceSequencerApp.renderTimeline(), 100);
    }
  }

  // Zoom functionality
  zoomIn() {
    this.zoomLevel = Math.min(3, this.zoomLevel * 1.2);
    this.applyZoom();
  }

  zoomOut() {
    this.zoomLevel = Math.max(0.3, this.zoomLevel / 1.2);
    this.applyZoom();
  }

  zoomToFit() {
    this.zoomLevel = 1;
    this.applyZoom();
  }

  applyZoom() {
    const framesWrapper = document.getElementById("timelineFramesWrapper");
    const frames = document.getElementById("timelineFrames");

    if (frames) {
      frames.style.transform = `scale(${this.zoomLevel})`;
      frames.style.transformOrigin = "top left";
    }

    const zoomLevelSpan = document.getElementById("zoomLevel");
    if (zoomLevelSpan) {
      zoomLevelSpan.textContent = Math.round(this.zoomLevel * 100) + "%";
    }

    this.saveSettings();
  }

  // Keyboard shortcuts
  setupKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
      // Only handle shortcuts when timeline is focused or expanded
      if (!this.container.contains(document.activeElement) && !this.isExpanded)
        return;

      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case "e":
          case "E":
            e.preventDefault();
            this.isExpanded ? this.collapse() : this.expand();
            break;
          case "=":
          case "+":
            e.preventDefault();
            this.zoomIn();
            break;
          case "-":
            e.preventDefault();
            this.zoomOut();
            break;
          case "0":
            e.preventDefault();
            this.zoomToFit();
            break;
        }
      }
    });
  }

  toggleFullscreen() {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      this.container.requestFullscreen().catch(console.warn);
    }
  }

  // Settings persistence
  saveSettings() {
    const settings = {
      isExpanded: this.isExpanded,
      height: this.container.offsetHeight,
      zoomLevel: this.zoomLevel,
    };

    localStorage.setItem(
      "faceSequencer_timelineSettings",
      JSON.stringify(settings)
    );
  }

  restoreSettings() {
    const saved = localStorage.getItem("faceSequencer_timelineSettings");
    if (!saved) return;

    try {
      const settings = JSON.parse(saved);

      if (settings.height && !this.isExpanded) {
        this.setHeight(settings.height);
      }

      if (settings.zoomLevel) {
        this.zoomLevel = settings.zoomLevel;
        this.applyZoom();
      }

      // Don't auto-expand on restore, let user decide
    } catch (error) {
      console.warn("Error restoring timeline settings:", error);
    }
  }

  // Accessibility
  announceChange(message) {
    if (window.uxEnhancer && window.uxEnhancer.announceStatus) {
      window.uxEnhancer.announceStatus(message);
    }
  }

  // Public API
  getState() {
    return {
      isExpanded: this.isExpanded,
      isResizing: this.isResizing,
      height: this.container.offsetHeight,
      zoomLevel: this.zoomLevel,
    };
  }

  // Integration with existing timeline
  updateTimeline() {
    if (window.faceSequencerApp && window.faceSequencerApp.renderTimeline) {
      window.faceSequencerApp.renderTimeline();
    }
  }

  // Cleanup
  destroy() {
    if (this.isExpanded) {
      this.collapse();
    }

    // Remove event listeners
    window.removeEventListener("resize", this.handleWindowResize);
    document.removeEventListener("mousemove", this.handleResize);
    document.removeEventListener("mouseup", this.stopResize);
  }
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  // Wait a bit for other timeline components to initialize
  setTimeout(() => {
    window.expandableTimeline = new ExpandableTimeline();
  }, 500);
});

// Export for use in other modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = ExpandableTimeline;
}
