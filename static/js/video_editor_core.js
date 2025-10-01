// video_editor_core.js - Core base class extracted from monolithic video_editor.js
// Responsibility: constructor bootstrapping, safe* helpers, basic DOM caching, primitive utilities.
// Higher-level features (generation, styles, timeline, export) live in extension modules.

class VideoEditorCore extends EventTarget {
  constructor(appRef) {
    super();
    // Host app resolution
    this.app = appRef || window.faceSequencerApp || window.app || null;
    if (!this.app) {
      const statusLog = (...m) => console.log("[video-editor status]", ...m);
      const errorLog = (msg) => console.error("[video-editor error]", msg);
      this.app = {
        showStatus: statusLog,
        showError: errorLog,
        reportError: (m) => errorLog(m),
        errorToasts: { show: (m) => errorLog(m) },
        state: {},
      };
      console.warn(
        "[VideoEditorCore] No host app supplied; using internal no-op logger app"
      );
    } else {
      this.app.showStatus =
        this.app.showStatus ||
        function (m) {
          console.log("[video-editor status]", m);
        };
      this.app.showError =
        this.app.showError ||
        function (m) {
          console.error("[video-editor error]", m);
        };
      this.app.errorToasts = this.app.errorToasts || {
        show: (m, o) => console.log("[toast]", m, o || ""),
      };
    }

    // Safe wrappers
    this.safeStatus = (msg) => {
      try {
        this.app?.showStatus?.(msg);
      } catch (e) {
        console.log("[safeStatus]", msg);
      }
    };
    this.safeError = (msg) => {
      try {
        this.app?.showError?.(msg);
      } catch (e) {
        console.error("[safeError]", msg);
      }
    };
    this.safeToast = (msg, opts) => {
      try {
        this.app?.errorToasts?.show?.(msg, opts);
      } catch (e) {
        console.log("[safeToast]", msg, opts || "");
      }
    };

    // Core state
    this.overlayElement = null;
    this.overlayTextElement = null;
    this._overlayDragState = null;
    this._overlayKeyListener = null;
    this.overlayPosition = { xPercent: 50, yPercent: 80, custom: false };
    this.precisionMode = "balanced";
    this.subtitles = [];
    this.isVideoLoaded = false;
    this.subtitleUpdateListener = null;

    // Deferred shortcuts binding hook (implemented in derived class)
    setTimeout(
      () => this.attachUndoRedoShortcuts && this.attachUndoRedoShortcuts(),
      0
    );

    // DOM cache (common elements)
    this.generateSubtitlesBtn = document.getElementById("generateSubtitlesBtn");
    this._generateBtnDuplicates = Array.from(
      document.querySelectorAll("#generateSubtitlesBtn")
    );
    if (this._generateBtnDuplicates.length > 1) {
      this.generateSubtitlesBtn = this._generateBtnDuplicates[0];
    }
    this.clearSubtitlesBtn = document.getElementById("clearSubtitlesBtn");
    this.frameSnapStepSelect = document.getElementById("frameSnapStep");
    this.videoTranscript = document.getElementById("videoTranscript");
    this._altTextInput = document.getElementById("textInput");
    this.subtitleTimeline = document.getElementById("subtitleTimeline");
    this.segmentsList = document.getElementById("segmentsList");
    this.previewSubtitles = document.getElementById("previewSubtitles");
    this.exportVideoWithSubtitles = document.getElementById(
      "exportVideoWithSubtitles"
    );
    this.loadVideoBtn = document.getElementById("loadVideoBtn");
    this.videoPreview = document.getElementById("videoPreview");
    this.videoPlaceholder = document.getElementById("videoPlaceholder");
    this.playPauseBtn = document.getElementById("playPauseBtn");
    this.stopVideoBtn = document.getElementById("stopVideoBtn");
    this.videoEditorInterface = document.getElementById("videoEditorInterface");
    this.faceAnimationInterface = document.getElementById(
      "faceAnimationInterface"
    );
    this.videoEditorMode = document.getElementById("videoEditorMode");
    this.faceAnimationMode = document.getElementById("faceAnimationMode");
    this.externalAudioInput = document.getElementById("externalAudioInput");
    this.precisionModeSelect = document.getElementById("precisionMode");
    if (!this.precisionModeSelect) {
      const hostControls = document.querySelector(
        ".video-editor-controls, .player-controls, .video-controls"
      );
      if (hostControls) {
        const sel = document.createElement("select");
        sel.id = "precisionMode";
        sel.innerHTML = `<option value="fast">Rápido</option><option value="balanced" selected>Balanceado</option><option value="maximum">Máximo</option>`;
        sel.style.marginLeft = "8px";
        sel.title = "Modo de precisão das legendas (velocidade vs sincronia)";
        hostControls.appendChild(sel);
        this.precisionModeSelect = sel;
      }
    }

    // Style inputs (declared; wired in style extension)
    this.presetButtons = document.querySelectorAll(".preset-btn");
    this.fontFamily = document.getElementById("fontFamily");
    this.fontSize = document.getElementById("fontSize");
    this.fontWeight = document.getElementById("fontWeight");
    this.textColor = document.getElementById("textColor");
    this.backgroundColor = document.getElementById("backgroundColor");
    this.backgroundOpacity = document.getElementById("backgroundOpacity");
    this.outlineColor = document.getElementById("outlineColor");
    this.outlineWidth = document.getElementById("outlineWidth");
    this.verticalPosition = document.getElementById("verticalPosition");
    this.horizontalAlign = document.getElementById("horizontalAlign");
    this.maxWidth = document.getElementById("maxWidth");

    this.effectsPanel = document.getElementById("subtitleEffectsPanel");
    if (!this.effectsPanel) {
      const container = document.querySelector(
        "#subtitleStylePanel, .subtitle-style-panel, .style-controls"
      );
      if (container) {
        const panel = document.createElement("div");
        panel.id = "subtitleEffectsPanel";
        Object.assign(panel.style, {
          marginTop: "12px",
          padding: "8px",
          border: "1px solid #333",
          borderRadius: "4px",
          background: "#1e1e1e",
        });
        panel.innerHTML = `<div style="font-weight:600;margin-bottom:6px;display:flex;align-items:center;gap:6px;"><span>Efeitos</span><small style="opacity:0.6;font-weight:400;">fade & karaoke</small></div><div style="display:flex;flex-direction:column;gap:6px;"><label style="display:flex;flex-direction:column;font-size:12px;gap:2px;">Fade In (ms)<input type="range" min="0" max="1000" step="10" value="150" id="fadeInMs" /><span style="font-size:11px;opacity:0.7;" id="fadeInMsValue">150 ms</span></label><label style="display:flex;flex-direction:column;font-size:12px;gap:2px;">Fade Out (ms)<input type="range" min="0" max="1500" step="10" value="150" id="fadeOutMs" /><span style="font-size:11px;opacity:0.7;" id="fadeOutMsValue">150 ms</span></label><label style="display:flex;align-items:center;gap:6px;font-size:12px;"><input type="checkbox" id="karaokeToggle" /> Karaoke (experimental)</label></div>`;
        container.appendChild(panel);
        this.effectsPanel = panel;
      }
    }
    this.fadeInMs = document.getElementById("fadeInMs");
    this.fadeOutMs = document.getElementById("fadeOutMs");
    this.fadeInMsValue = document.getElementById("fadeInMsValue");
    this.fadeOutMsValue = document.getElementById("fadeOutMsValue");
    this.karaokeToggle = document.getElementById("karaokeToggle");

    // Hidden file input
    this.videoInput = document.createElement("input");
    this.videoInput.type = "file";
    this.videoInput.accept = ".mp4,.mov,.mkv,.webm,.avi,.m4v,video/*";
    this.videoInput.style.display = "none";
    document.body.appendChild(this.videoInput);
  }
}

window.VideoEditorCore = VideoEditorCore;
// Global namespace for editor modules to avoid load-order issues
window.FaceSeqEditorModules = window.FaceSeqEditorModules || {};
window.FaceSeqEditorModules.core = VideoEditorCore;
