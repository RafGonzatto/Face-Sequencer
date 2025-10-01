// video_editor_history.js
// Undo/redo & history management extracted from video_editor.js
(function () {
  if (!window.VideoEditorModule) return;
  window.FaceSeqEditorModules = window.FaceSeqEditorModules || {};
  window.FaceSeqEditorModules.history = true;
  const proto = window.VideoEditorModule.prototype;

  proto._pushHistory = function () {
    const snapshot = JSON.stringify(this.subtitles.map((s) => ({ ...s })));
    this._undoStack.push(snapshot);
    if (this._undoStack.length > this._maxHistory) this._undoStack.shift();
    this._redoStack = [];
  };

  proto._applyEdgeSnapHighlight = function (segmentEl, sub, totalDuration) {
    if (!this.subtitleTimeline) return;
    let guideLayer = this.subtitleTimeline.querySelector(".snap-edge-guides");
    if (!guideLayer) {
      guideLayer = document.createElement("div");
      guideLayer.className = "snap-edge-guides";
      Object.assign(guideLayer.style, {
        position: "absolute",
        inset: "0",
        pointerEvents: "none",
      });
      this.subtitleTimeline.appendChild(guideLayer);
    }
    guideLayer.innerHTML = "";
    if (!this._lastSnapMeta || !sub) return;
    const { edge, target } = this._lastSnapMeta;
    if (target == null) return;
    const leftPct = (target / totalDuration) * 100;
    const line = document.createElement("div");
    line.className = "snap-edge-line";
    line.style.left = leftPct + "%";
    line.style.transform = "translateX(-1.5px)";
    guideLayer.appendChild(line);
    requestAnimationFrame(() => {
      setTimeout(() => {
        line.style.opacity = "0";
      }, 120);
    });
  };
})();
