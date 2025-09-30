// Test script for debugging button functionality
console.log("=== Button Functionality Test ===");

// Test Welcome Modal
console.log("1. Testing Welcome Modal elements...");
const welcomeWizard = document.getElementById("welcomeWizard");
const nextBtn = document.getElementById("wizardNext");
const prevBtn = document.getElementById("wizardPrev");
const skipBtn = document.getElementById("wizardSkip");

console.log("Welcome Wizard:", welcomeWizard ? "✓ Found" : "✗ Not found");
console.log("Next Button:", nextBtn ? "✓ Found" : "✗ Not found");
console.log("Prev Button:", prevBtn ? "✓ Found" : "✗ Not found");
console.log("Skip Button:", skipBtn ? "✓ Found" : "✗ Not found");

// Test Mode Buttons
console.log("\n2. Testing Mode buttons...");
const faceAnimationBtn = document.getElementById("faceAnimationMode");
const videoEditorBtn = document.getElementById("videoEditorMode");

console.log(
  "Face Animation Button:",
  faceAnimationBtn ? "✓ Found" : "✗ Not found"
);
console.log("Video Editor Button:", videoEditorBtn ? "✓ Found" : "✗ Not found");

// Test Quick Start Cards
console.log("\n3. Testing Quick Start Cards...");
const quickStartCards = document.querySelectorAll(".quick-start-card");
console.log("Quick Start Cards found:", quickStartCards.length);

quickStartCards.forEach((card, index) => {
  console.log(`Card ${index + 1}:`, card.dataset.template || "No template");
});

// Test Event Listeners
console.log("\n4. Testing Event Listeners...");
if (nextBtn) {
  console.log(
    "Next button onclick:",
    nextBtn.onclick ? "Has onclick" : "No onclick"
  );
  console.log(
    "Next button listeners:",
    nextBtn.getEventListeners
      ? nextBtn.getEventListeners()
      : "Cannot check listeners"
  );
}

// Test UX Enhancement Manager
console.log("\n5. Testing UX Enhancement Manager...");
console.log(
  "Window.uxEnhancer:",
  window.uxEnhancer ? "✓ Available" : "✗ Not available"
);
if (window.uxEnhancer) {
  console.log("UX Enhancer wizard data:", window.uxEnhancer.wizardData);
  console.log("UX Enhancer current step:", window.uxEnhancer.currentWizardStep);
}

// Test Video Editor Module
console.log("\n6. Testing Video Editor Module...");
console.log(
  "Window.faceSequencerApp:",
  window.faceSequencerApp ? "✓ Available" : "✗ Not available"
);
if (window.faceSequencerApp && window.faceSequencerApp.videoEditor) {
  console.log("Video Editor Module:", "✓ Available");
} else {
  console.log("Video Editor Module:", "✗ Not available");
}

console.log("\n=== Test Complete ===");

// Add test functions
window.testNextButton = function () {
  console.log("Testing Next button manually...");
  if (window.uxEnhancer) {
    window.uxEnhancer.nextWizardStep();
  } else {
    console.log("UX Enhancer not available");
  }
};

window.testVideoEditor = function () {
  console.log("Testing Video Editor button manually...");
  if (window.faceSequencerApp && window.faceSequencerApp.videoEditor) {
    window.faceSequencerApp.videoEditor.switchToVideoEditorMode();
  } else {
    console.log("Video Editor not available");
  }
};

window.testCardSelection = function (template) {
  console.log("Testing card selection for template:", template);
  const card = document.querySelector(`[data-template="${template}"]`);
  if (card) {
    card.click();
    console.log("Card clicked");
  } else {
    console.log("Card not found");
  }
};

console.log("Test functions added to window:");
console.log("- window.testNextButton()");
console.log("- window.testVideoEditor()");
console.log("- window.testCardSelection('basic')");

// Additional debugging for Video Editor button
window.debugVideoEditorButton = function () {
  console.log("\n=== Video Editor Button Debug ===");

  const btn = document.getElementById("videoEditorMode");
  console.log("Button element:", btn);

  if (btn) {
    console.log("Button classes:", btn.className);
    console.log("Button data-mode:", btn.dataset.mode);
    console.log("Button onclick:", btn.onclick);

    // Check event listeners (if browser supports it)
    console.log(
      "Button event listeners:",
      btn.getEventListeners ? btn.getEventListeners() : "Cannot check"
    );

    // Test manual click
    console.log("Testing manual click...");
    btn.click();
  }

  // Check VideoEditor module
  console.log("\n=== VideoEditor Module Debug ===");
  console.log("window.VideoEditorModule:", window.VideoEditorModule);

  if (window.faceSequencerApp) {
    console.log(
      "App videoEditor instance:",
      window.faceSequencerApp.videoEditor
    );

    if (window.faceSequencerApp.videoEditor) {
      const ve = window.faceSequencerApp.videoEditor;
      console.log("VideoEditor elements:");
      console.log("- videoEditorMode:", ve.videoEditorMode);
      console.log("- faceAnimationMode:", ve.faceAnimationMode);
      console.log("- videoEditorInterface:", ve.videoEditorInterface);
      console.log("- faceAnimationInterface:", ve.faceAnimationInterface);
    }
  }
};

console.log("- window.debugVideoEditorButton()");
