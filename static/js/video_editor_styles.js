// video_editor_styles.js
// Style and preset related methods extracted from video_editor.js

(function () {
  if (!window.VideoEditorModule) return; // ensure base class loaded
  window.FaceSeqEditorModules = window.FaceSeqEditorModules || {};
  window.FaceSeqEditorModules.styles = true;
  const proto = window.VideoEditorModule.prototype;

  proto.applyPreset = function (presetName) {
    console.log("🎨 Applying preset:", presetName);
    this.presetButtons?.forEach((btn) => btn.classList.remove("active"));
    const selectedBtn = document.querySelector(`[data-preset="${presetName}"]`);
    if (selectedBtn) selectedBtn.classList.add("active");
    this.currentPreset = presetName;
    const presets = {
      "instagram-story": {
        fontSize: 32,
        fontWeight: "bold",
        textColor: "#ffffff",
        backgroundColor: "#000000",
        backgroundOpacity: 60,
        outlineWidth: 2,
        verticalPosition: "bottom",
        horizontalAlign: "center",
        maxWidth: 85,
      },
      "instagram-reel": {
        fontSize: 28,
        fontWeight: "600",
        textColor: "#ffffff",
        backgroundColor: "#000000",
        backgroundOpacity: 70,
        outlineWidth: 2,
        verticalPosition: "bottom",
        horizontalAlign: "center",
        maxWidth: 90,
      },
      tiktok: {
        fontSize: 36,
        fontWeight: "bold",
        textColor: "#ffffff",
        backgroundColor: "#000000",
        backgroundOpacity: 50,
        outlineWidth: 3,
        verticalPosition: "bottom",
        horizontalAlign: "center",
        maxWidth: 80,
      },
      "youtube-shorts": {
        fontSize: 30,
        fontWeight: "bold",
        textColor: "#ffffff",
        backgroundColor: "#000000",
        backgroundOpacity: 65,
        outlineWidth: 2,
        verticalPosition: "bottom",
        horizontalAlign: "center",
        maxWidth: 85,
      },
    };
    const preset = presets[presetName];
    if (preset) {
      if (this.fontSize) {
        this.fontSize.value = preset.fontSize;
        this.fontSize.dispatchEvent(new Event("input"));
      }
      if (this.fontWeight) this.fontWeight.value = preset.fontWeight;
      if (this.textColor) this.textColor.value = preset.textColor;
      if (this.backgroundColor)
        this.backgroundColor.value = preset.backgroundColor;
      if (this.backgroundOpacity) {
        this.backgroundOpacity.value = preset.backgroundOpacity;
        this.backgroundOpacity.dispatchEvent(new Event("input"));
      }
      if (this.outlineWidth) {
        this.outlineWidth.value = preset.outlineWidth;
        this.outlineWidth.dispatchEvent(new Event("input"));
      }
      if (this.verticalPosition)
        this.verticalPosition.value = preset.verticalPosition;
      if (this.horizontalAlign)
        this.horizontalAlign.value = preset.horizontalAlign;
      if (this.maxWidth) {
        this.maxWidth.value = preset.maxWidth;
        this.maxWidth.dispatchEvent(new Event("input"));
      }
      this.updateSubtitleStyle();
      this.safeStatus(`Applied ${presetName.replace("-", " ")} preset`);
    }
  };

  proto.updateSubtitleStyle = function () {
    console.log("🎨 Updating subtitle style");
    const style = this.getCurrentStyle();
    this.applyStyleToPreview(style);
  };

  proto.getCurrentStyle = function () {
    return {
      fontFamily: this.fontFamily?.value || "Arial, sans-serif",
      fontSize: this.fontSize?.value || 24,
      fontWeight: this.fontWeight?.value || "normal",
      textColor: this.textColor?.value || "#ffffff",
      backgroundColor: this.backgroundColor?.value || "#000000",
      backgroundOpacity: this.backgroundOpacity?.value || 70,
      outlineColor: this.outlineColor?.value || "#000000",
      outlineWidth: this.outlineWidth?.value || 2,
      verticalPosition: this.verticalPosition?.value || "bottom",
      horizontalAlign: this.horizontalAlign?.value || "center",
      maxWidth: this.maxWidth?.value || 80,
      effects: {
        fadeInMs: this.fadeInMs ? parseInt(this.fadeInMs.value, 10) : 150,
        fadeOutMs: this.fadeOutMs ? parseInt(this.fadeOutMs.value, 10) : 150,
        karaoke: this.karaokeToggle ? !!this.karaokeToggle.checked : false,
      },
    };
  };

  proto.applyStyleToPreview = function (style) {
    /* no-op placeholder for future preview overlay updates */
  };
})();
