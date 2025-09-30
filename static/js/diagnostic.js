// Quick diagnostic script to check JavaScript initialization status
console.log("=== Face Sequencer Pro - JavaScript Diagnostic ===");

// Check if main app is initialized
console.log(
  "Main App Status:",
  window.faceSequencerApp ? "✅ Initialized" : "❌ Not Found"
);

// Check if UX enhancer is initialized
console.log(
  "UX Enhancer Status:",
  window.uxEnhancer ? "✅ Initialized" : "❌ Not Found"
);

// Check if timeline enhancer is available
console.log(
  "Timeline Enhancer Class:",
  window.TimelineEnhancer ? "✅ Available" : "❌ Not Found"
);

// Check for critical DOM elements
const criticalElements = [
  "#timelineContent",
  "#timelineFrames",
  "#frameEditor",
  "#audioUpload",
  ".timeline-container",
  ".timeline-frames-wrapper",
];

console.log("DOM Elements Status:");
criticalElements.forEach((selector) => {
  const element = document.querySelector(selector);
  console.log(`  ${selector}: ${element ? "✅ Found" : "❌ Missing"}`);
});

// Check for JavaScript errors
if (window.ErrorInstrumentation) {
  const errors = window.ErrorInstrumentation.export();
  const recentErrors = errors.slice(-10);
  if (recentErrors.length > 0) {
    console.log("Recent JavaScript Errors:");
    recentErrors.forEach((error) => {
      console.error(`  ${error.event}:`, error.payload);
    });
  } else {
    console.log("No recent JavaScript errors found");
  }
}

// Test basic functionality
try {
  if (window.faceSequencerApp) {
    console.log("App Methods Available:", {
      init: typeof window.faceSequencerApp.init,
      setupAudio: typeof window.faceSequencerApp.setupAudio,
      loadSequence: typeof window.faceSequencerApp.loadSequence,
    });
  }
} catch (error) {
  console.error("Error testing app methods:", error);
}

console.log("=== Diagnostic Complete ===");
