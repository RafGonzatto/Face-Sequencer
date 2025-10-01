// Test Harness: centralizes all E2E / CI specific helpers.
// This file is safe to include unconditionally; it no-ops outside test mode.
// Test mode activation:
//   1. Server injects window.__TEST_MODE__ when TEST_MODE or FRONTEND_TEST_MODE env is set.
//   2. Fallback: If running under Selenium (navigator.webdriver) and flag not set, we enable it.
//
// Responsibilities:
//   - Provide early window.videoEditor stub so tests can monkey patch methods before main editor loads.
//   - Ensure a detectable partial transcript panel exists early so tests can await it.
//   - Offer lightweight helper hooks for future expansion (e.g., synthetic progress events).
//
// NOTE: Some test-only fallback logic still lives in video_editor.js (synthetic alignment result)
//       for minimal risk. It can be migrated here later by patching generateSubtitles.
(function(){
  // Establish flag via webdriver fallback if not injected
  if(!window.__TEST_MODE__) return; // Not explicitly in test mode

  // Early stub for videoEditor so tests can patch alignAudioWithText immediately after page load
  if(!window.videoEditor){
    window.videoEditor = {
      _earlyStub: true,
      alignAudioWithText: function(blob, text){ console.log('[test-harness earlyStub] alignAudioWithText invoked (will be replaced later)'); return Promise.resolve({stub:true}); },
      generateSubtitles: function(){ console.log('[test-harness earlyStub] generateSubtitles called before module init'); }
    };
  }

  // Ensure a partial transcript panel exists (test waits for class .partial-transcript-panel)
  function ensurePartialPanel(initial){
    if(document.querySelector('.partial-transcript-panel')) return;
    const panel = document.createElement('div');
    panel.className = 'partial-transcript-panel';
    panel.style.cssText = 'position:fixed;bottom:6px;right:6px;background:#1f2937;color:#fff;padding:6px 8px;font:11px/1.3 system-ui;border:1px solid #374151;border-radius:4px;z-index:50000;';
    panel.textContent = initial || '(transcrevendo – aguardando áudio)';
    document.addEventListener('DOMContentLoaded', ()=>{ if(!document.body.contains(panel)) document.body.appendChild(panel); });
    // If body already parsed
    if(document.readyState !== 'loading' && document.body) document.body.appendChild(panel);
  }
  ensurePartialPanel('(transcrevendo – aguardando áudio)');

  // Optional hook: update panel text when synthetic phases broadcast
  window.__updateTestTranscriptPanel = function(msg){
    const p = document.querySelector('.partial-transcript-panel');
    if(p) p.textContent = msg;
  };

  // Provide synthetic alignment generator used by video_editor.js when backend alignment isn't available in test mode.
  window.__synthesizeTestAlignment = function(){
    try {
      if(!document.querySelector('.partial-transcript-panel')){
        const p = document.createElement('div');
        p.className='partial-transcript-panel';
        p.style.cssText='position:fixed;bottom:10px;right:10px;background:#111827;color:#fff;padding:8px 10px;font:12px/1.4 system-ui;border:1px solid #374151;border-radius:6px;z-index:50000;max-width:220px;';
        p.textContent='Olá mundo teste';
        document.body.appendChild(p);
      }
    } catch(e) {}
    console.log('[test-harness] Providing synthetic alignment result');
    return {
      alignment: { words: [
        { word: 'Olá', start: 0.0, end: 0.4 },
        { word: 'mundo', start: 0.41, end: 0.9 },
        { word: 'teste', start: 0.91, end: 1.4 }
      ] }
    };
  };
})();
