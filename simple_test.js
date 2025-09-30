// Simple test script to debug button click issue
console.log("=== SIMPLE BUTTON DEBUG TEST ===");

// Test 1: Check if button exists
const btn = document.getElementById("videoEditorMode");
console.log("Button found:", !!btn);
console.log("Button element:", btn);

if (btn) {
  // Test 2: Check button properties
  console.log("Button ID:", btn.id);
  console.log("Button classes:", btn.className);
  console.log("Button innerHTML:", btn.innerHTML);

  // Test 3: Add simple click listener
  btn.addEventListener("click", function () {
    console.log("🚨 CLICK DETECTED! This proves the button works!");
    alert(
      "Button clicked! The issue might be with the VideoEditor initialization."
    );
  });

  // Test 4: Check existing onclick
  console.log("Existing onclick:", btn.onclick);

  console.log("✅ Test listener added - try clicking the button now!");
} else {
  console.error("❌ Button not found!");
}

// Test 5: Check VideoEditor
console.log("\n=== VIDEO EDITOR MODULE CHECK ===");
console.log("window.VideoEditorModule:", typeof window.VideoEditorModule);
console.log("window.faceSequencerApp:", !!window.faceSequencerApp);

if (window.faceSequencerApp) {
  console.log("App videoEditor:", !!window.faceSequencerApp.videoEditor);
}

// Test 6: Manual interface toggle
window.testToggleInterface = function () {
  const faceInterface = document.getElementById("faceAnimationInterface");
  const videoInterface = document.getElementById("videoEditorInterface");

  console.log("Face Interface:", !!faceInterface);
  console.log("Video Interface:", !!videoInterface);

  if (faceInterface && videoInterface) {
    faceInterface.style.display = "none";
    videoInterface.style.display = "flex";
    console.log("✅ Interface toggled manually!");
  }
};

console.log("Manual toggle function: window.testToggleInterface()");
