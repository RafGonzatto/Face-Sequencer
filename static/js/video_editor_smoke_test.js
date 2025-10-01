// video_editor_smoke_test.js
// Lightweight dev-only / test harness smoke check for VideoEditorModule when no host app is provided.
// Injects after video_editor.js. Safe to include conditionally (not loaded in production unless explicitly enabled).
(function(){
  if (window.__VIDEO_EDITOR_SMOKE_RAN__) return; // prevent duplicates
  window.__VIDEO_EDITOR_SMOKE_RAN__ = true;

  // Only run in explicit FRONTEND_TEST_MODE or when hash includes smoke
  const envFlag = (window.__TEST_MODE__ || window.__FRONTEND_TEST_MODE__);
  const hashFlag = window.location.hash.includes('smoke');
  if(!envFlag && !hashFlag) return; // gated

  try {
    console.log('[smoke] Starting VideoEditorModule headless instantiation test');
    const mod = new VideoEditorModule(null); // no host app

    // Simulate minimal transcript to exercise generate button logic
    if (mod.videoTranscript) {
      mod.videoTranscript.value = 'Hello world test transcript';
    } else if (mod._altTextInput) {
      mod._altTextInput.value = 'Hello world test transcript';
    }
    // Force UI update paths that are safe without loaded video
    try { mod.updateGenerateButton && mod.updateGenerateButton(); } catch(e){ console.warn('[smoke] updateGenerateButton error', e); }

    // Call a couple of safeStatus / safeError
    mod.safeStatus('[smoke] status path works');
    mod.safeError('[smoke] error path works');

    // Intentionally call preview (should short-circuit gracefully)
    try { mod.previewWithSubtitles(); } catch(e){ console.error('[smoke] previewWithSubtitles threw', e); }

    console.log('[smoke] VideoEditorModule basic methods executed without fatal errors');
  } catch (err) {
    console.error('[smoke] Failure constructing VideoEditorModule without host app', err);
  }
})();
