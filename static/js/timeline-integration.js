// Timeline Integration Enhancements
// This file extends the existing timeline functionality with expandable features

// Integration with existing FaceSequencerApp
(function () {
  "use strict";

  // Wait for the main app to be available
  function waitForApp() {
    if (window.faceSequencerApp && window.expandableTimeline) {
      integrateWithApp();
    } else {
      setTimeout(waitForApp, 100);
    }
  }

  function integrateWithApp() {
    const app = window.faceSequencerApp;
    const timeline = window.expandableTimeline;

    if (!app || !timeline) return;

    // Enhance the existing renderTimeline function
    const originalRenderTimeline = app.renderTimeline;
    if (originalRenderTimeline) {
      app.renderTimeline = function () {
        const result = originalRenderTimeline.call(this);

        // After rendering, apply any zoom or expansion state
        if (timeline.zoomLevel !== 1) {
          timeline.applyZoom();
        }

        // Enhanced frame rendering for expanded mode
        if (timeline.isExpanded) {
          enhanceFramesForExpandedMode();
        }

        return result;
      };
    }

    // Enhance frame interaction in expanded mode
    enhanceFrameInteraction();

    // Add timeline stats
    addTimelineStats();

    console.log("Timeline integration enhanced");
  }

  function enhanceFramesForExpandedMode() {
    const framesContainer = document.getElementById("timelineFrames");
    if (!framesContainer) return;

    const frames = framesContainer.querySelectorAll(".timeline-frame");

    frames.forEach((frame, index) => {
      // Add frame numbers for better navigation
      if (!frame.querySelector(".frame-number")) {
        const frameNumber = document.createElement("div");
        frameNumber.className = "frame-number";
        frameNumber.textContent = index + 1;
        frame.appendChild(frameNumber);
      }

      // Add enhanced tooltips
      if (!frame.hasAttribute("data-enhanced")) {
        frame.setAttribute("data-enhanced", "true");

        const tooltip = createEnhancedTooltip(frame, index);
        frame.appendChild(tooltip);

        // Show tooltip on hover
        frame.addEventListener("mouseenter", () => {
          tooltip.style.display = "block";
        });

        frame.addEventListener("mouseleave", () => {
          tooltip.style.display = "none";
        });
      }
    });
  }

  function createEnhancedTooltip(frame, index) {
    const tooltip = document.createElement("div");
    tooltip.className = "enhanced-frame-tooltip";

    // Get frame data from the main app
    const app = window.faceSequencerApp;
    const sequence = app?.state?.sequence || [];
    const frameData = sequence[index];

    if (frameData) {
      tooltip.innerHTML = `
        <div class="tooltip-header">Frame ${index + 1}</div>
        <div class="tooltip-body">
          <div class="tooltip-item">
            <strong>Character:</strong> ${frameData.character || "N/A"}
          </div>
          <div class="tooltip-item">
            <strong>Image:</strong> ${
              frameData.imagePath ? frameData.imagePath.split("/").pop() : "N/A"
            }
          </div>
          <div class="tooltip-item">
            <strong>Time:</strong> ${formatTime(index * (1000 / 30))}
          </div>
        </div>
      `;
    } else {
      tooltip.innerHTML = `
        <div class="tooltip-header">Frame ${index + 1}</div>
        <div class="tooltip-body">No data available</div>
      `;
    }

    return tooltip;
  }

  function enhanceFrameInteraction() {
    // Add keyboard navigation for frames
    document.addEventListener("keydown", (e) => {
      if (!window.expandableTimeline?.isExpanded) return;

      const framesContainer = document.getElementById("timelineFrames");
      if (!framesContainer) return;

      const frames = framesContainer.querySelectorAll(".timeline-frame");
      const currentFrame = framesContainer.querySelector(
        ".timeline-frame.selected"
      );
      const currentIndex = currentFrame
        ? Array.from(frames).indexOf(currentFrame)
        : -1;

      let newIndex = currentIndex;

      switch (e.key) {
        case "ArrowLeft":
          e.preventDefault();
          newIndex = Math.max(0, currentIndex - 1);
          break;
        case "ArrowRight":
          e.preventDefault();
          newIndex = Math.min(frames.length - 1, currentIndex + 1);
          break;
        case "Home":
          e.preventDefault();
          newIndex = 0;
          break;
        case "End":
          e.preventDefault();
          newIndex = frames.length - 1;
          break;
        case "PageUp":
          e.preventDefault();
          newIndex = Math.max(0, currentIndex - 10);
          break;
        case "PageDown":
          e.preventDefault();
          newIndex = Math.min(frames.length - 1, currentIndex + 10);
          break;
      }

      if (
        newIndex !== currentIndex &&
        newIndex >= 0 &&
        newIndex < frames.length
      ) {
        selectFrame(frames[newIndex], newIndex);
      }
    });
  }

  function selectFrame(frameElement, index) {
    // Remove previous selection
    const frames = document.querySelectorAll(".timeline-frame");
    frames.forEach((f) => f.classList.remove("selected"));

    // Add selection to new frame
    frameElement.classList.add("selected");

    // Scroll frame into view
    frameElement.scrollIntoView({
      behavior: "smooth",
      block: "center",
      inline: "center",
    });

    // Update main app preview if available
    if (window.faceSequencerApp && window.faceSequencerApp.previewFrame) {
      window.faceSequencerApp.previewFrame(index);
    }
  }

  function addTimelineStats() {
    const container = document.getElementById("timelineContainer");
    if (!container || container.querySelector(".timeline-stats")) return;

    const stats = document.createElement("div");
    stats.className = "timeline-stats";
    stats.innerHTML = `
      <div class="stats-item">
        <span class="stats-label">Total Frames:</span>
        <span class="stats-value" id="totalFrames">0</span>
      </div>
      <div class="stats-item">
        <span class="stats-label">Duration:</span>
        <span class="stats-value" id="totalDuration">0:00</span>
      </div>
      <div class="stats-item">
        <span class="stats-label">FPS:</span>
        <span class="stats-value">30</span>
      </div>
    `;

    // Insert stats in expanded mode
    const timelineContent = document.getElementById("timelineContent");
    if (timelineContent) {
      timelineContent.insertBefore(stats, timelineContent.firstChild);
    }

    // Update stats when timeline changes
    updateTimelineStats();

    // Listen for timeline updates
    container.addEventListener("timeline-updated", updateTimelineStats);
  }

  function updateTimelineStats() {
    const app = window.faceSequencerApp;
    const sequence = app?.state?.sequence || [];

    const totalFramesElement = document.getElementById("totalFrames");
    const totalDurationElement = document.getElementById("totalDuration");

    if (totalFramesElement) {
      totalFramesElement.textContent = sequence.length;
    }

    if (totalDurationElement) {
      const durationMs = sequence.length * (1000 / 30); // 30 FPS
      totalDurationElement.textContent = formatTime(durationMs);
    }
  }

  function formatTime(milliseconds) {
    const seconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;

    return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
  }

  // Enhanced CSS for new features
  function addEnhancedStyles() {
    const style = document.createElement("style");
    style.textContent = `
      /* Frame Numbers */
      .timeline-frame {
        position: relative;
      }
      
      .frame-number {
        position: absolute;
        top: 2px;
        right: 2px;
        background: rgba(0, 0, 0, 0.7);
        color: white;
        font-size: 8px;
        padding: 1px 3px;
        border-radius: 2px;
        font-weight: bold;
        z-index: 10;
      }
      
      /* Enhanced Tooltips */
      .enhanced-frame-tooltip {
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.9);
        color: white;
        padding: 8px;
        border-radius: 4px;
        font-size: 11px;
        white-space: nowrap;
        z-index: 100;
        display: none;
        margin-bottom: 4px;
      }
      
      .enhanced-frame-tooltip::after {
        content: '';
        position: absolute;
        top: 100%;
        left: 50%;
        transform: translateX(-50%);
        border: 4px solid transparent;
        border-top-color: rgba(0, 0, 0, 0.9);
      }
      
      .tooltip-header {
        font-weight: bold;
        margin-bottom: 4px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        padding-bottom: 2px;
      }
      
      .tooltip-item {
        margin: 2px 0;
      }
      
      /* Timeline Stats */
      .timeline-stats {
        display: none;
        background: var(--bg-tertiary);
        padding: 8px 12px;
        border-bottom: 1px solid var(--border-color);
        font-size: 11px;
        gap: 16px;
      }
      
      .timeline-container.expanded .timeline-stats {
        display: flex;
      }
      
      .stats-item {
        display: flex;
        gap: 4px;
      }
      
      .stats-label {
        color: var(--text-muted);
      }
      
      .stats-value {
        font-weight: 600;
        color: var(--text-primary);
      }
      
      /* Frame Selection */
      .timeline-frame.selected {
        outline: 2px solid var(--primary-color);
        outline-offset: 1px;
        z-index: 20;
      }
      
      /* Responsive adjustments */
      @media (max-width: 768px) {
        .frame-number {
          font-size: 7px;
          padding: 0px 2px;
        }
        
        .enhanced-frame-tooltip {
          font-size: 10px;
          padding: 6px;
        }
        
        .timeline-stats {
          flex-direction: column;
          gap: 4px;
        }
      }
    `;

    document.head.appendChild(style);
  }

  // Initialize when DOM is ready
  document.addEventListener("DOMContentLoaded", () => {
    addEnhancedStyles();
    waitForApp();
  });
})();
