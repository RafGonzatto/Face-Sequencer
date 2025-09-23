// Add keyboard navigation hint to the HTML
let keyboardHint = document.createElement("div");
keyboardHint.className = "keyboard-hint";
keyboardHint.innerHTML = `
  <p>Keyboard Navigation:</p>
  <p><kbd>←</kbd><kbd>→</kbd> Navigate frames | <kbd>Space</kbd> Play/Pause | <kbd>Home</kbd>/<kbd>End</kbd> First/Last frame</p>
  <p><kbd>Shift</kbd>+<kbd>←/→</kbd> Jump 5 frames | <kbd>Ctrl</kbd>+<kbd>←/→</kbd> Jump 10 frames</p>
`;

// Add the hint to the page on load
document.addEventListener("DOMContentLoaded", () => {
  const timelineContainer = document.querySelector(".timeline-container");
  if (timelineContainer && !document.querySelector(".keyboard-hint")) {
    timelineContainer.appendChild(keyboardHint);
  } else {
    console.warn(
      "Timeline container not found or keyboard hint already exists."
    );
  }
});
