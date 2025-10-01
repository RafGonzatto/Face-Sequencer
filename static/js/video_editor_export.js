// video_editor_export.js
// Export related methods extracted from video_editor.js

(function(){
  if (!window.VideoEditorModule) return;
  const proto = window.VideoEditorModule.prototype;

  proto.exportVideo = async function(){
    if (!this.isVideoLoaded || this.subtitles.length === 0){
      this.safeError('Please load a video and generate subtitles first');
      return;
    }
    try {
      console.log('📤 Exporting video with subtitles...');
      this.safeStatus('Preparing video export with subtitles...');
      const exportData = {
        videoFile: this.videoFile,
        subtitles: this.subtitles,
        style: this.getCurrentStyle(),
        preset: this.currentPreset,
      };
      const result = await this.processVideoExport(exportData);
      if (result.success){
        this.safeStatus('Video exported successfully with subtitles!');
        if (result.downloadUrl){
          const a = document.createElement('a');
            a.href = result.downloadUrl;
            a.download = result.filename || 'video_with_subtitles.mp4';
            a.click();
        }
      } else {
        throw new Error(result.error || 'Export failed');
      }
    } catch(err){
      console.error('❌ Video export failed:', err);
      this.safeError(`Export failed: ${err.message}`);
    }
  };

  proto.processVideoExport = async function(exportData){
    try {
      if (!exportData.videoFile) throw new Error('Missing video file');
      if (!exportData.subtitles || !exportData.subtitles.length) throw new Error('No subtitles');
      const fd = new FormData();
      fd.append('video', exportData.videoFile, exportData.videoFile.name || 'video.mp4');
      const minimalSubs = exportData.subtitles.map(s => ({ text: s.text || '', start_ms: s.start_ms, end_ms: s.end_ms, words: s.words || undefined }));
      if (!exportData.style.effects){
        exportData.style.effects = { fadeInMs:150, fadeOutMs:150, karaoke:false };
      }
      const payload = { subtitles: minimalSubs, style: exportData.style, overlayPosition: this.overlayPosition, precision_mode: this.precisionMode };
      fd.append('payload', JSON.stringify(payload));
      const resp = await fetch('/api/export/video-with-subtitles', { method:'POST', body:fd });
      if (!resp.ok){
        let detail = resp.statusText;
        try { const j = await resp.json(); if (j && (j.error || j.message)) detail = j.error || j.message; } catch(_){ }
        throw new Error('Export failed: ' + detail);
      }
      const json = await resp.json();
      if (!json.success) throw new Error(json.error || json.message || 'Export failed');
      return { success:true, filename: json.export_filename, downloadUrl: json.download_url };
    } catch(e){
      return { success:false, error: e.message };
    }
  };
})();
