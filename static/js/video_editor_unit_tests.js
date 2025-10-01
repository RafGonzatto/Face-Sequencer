// video_editor_unit_tests.js
// Minimal in-browser unit test harness for decomposed editor modules.
// Runs automatically in FRONTEND_TEST_MODE or with ?UNIT_TESTS=1 or #unit-tests
(function(){
  const q = window.location.search;
  const h = window.location.hash;
  const enabled = (window.__FRONTEND_TEST_MODE__ || /[?&]UNIT_TESTS=1/.test(q) || h.includes('unit-tests'));
  if(!enabled) return;
  if (window.__VIDEO_EDITOR_UNIT_TESTS_RAN__) return; // idempotent
  window.__VIDEO_EDITOR_UNIT_TESTS_RAN__ = true;

  const results = [];
  const assert = (name, cond, info) => {
    results.push({ name, pass: !!cond, info: info || '' });
    if(!cond) console.error('[test fail]', name, info||''); else console.log('[test pass]', name);
  };

  function summary(){
    const passCount = results.filter(r=>r.pass).length;
    const failCount = results.length - passCount;
    const panel = document.createElement('div');
    panel.style.cssText='position:fixed;bottom:10px;right:10px;background:#111;color:#eee;font:12px monospace;padding:10px 14px;border:1px solid #333;border-radius:6px;z-index:99999;max-width:300px;';
    panel.innerHTML = `<strong>Editor Unit Tests</strong><br>${passCount} passed / ${failCount} failed <button id="closeUnitPanel" style="float:right;background:#222;color:#eee;border:1px solid #444;border-radius:4px;cursor:pointer;">x</button>`;
    const list = document.createElement('ul');
    list.style.margin='8px 0 0'; list.style.padding='0 0 0 16px';
    results.forEach(r=>{
      const li = document.createElement('li');
      li.style.color = r.pass ? '#22c55e' : '#ef4444';
      li.textContent = (r.pass ? '✓ ' : '✗ ') + r.name + (r.info ? ' - ' + r.info : '');
      list.appendChild(li);
    });
    panel.appendChild(list);
    document.body.appendChild(panel);
    panel.querySelector('#closeUnitPanel').onclick=()=>panel.remove();
  }

  try {
    console.log('[unit] Starting VideoEditorModule unit tests');
    const editor = new VideoEditorModule(null);
    assert('instance created', !!editor && editor instanceof VideoEditorModule);
    assert('safeStatus defined', typeof editor.safeStatus === 'function');
    assert('safeError defined', typeof editor.safeError === 'function');
    assert('style getter exists', typeof editor.getCurrentStyle === 'function');

    // Inject a fake subtitle and test history snapshot push
    editor.subtitles = [{ id: 's1', text: 'Hello world line', start_ms:0, end_ms:1500 }];
    editor._undoStack = []; editor._redoStack = []; editor._maxHistory = 10;
    if (editor._pushHistory) editor._pushHistory();
    assert('undo stack after push', editor._undoStack.length === 1, 'length=' + editor._undoStack.length);

    // Apply a preset (if styles module loaded)
    if (window.FaceSeqEditorModules?.styles){
      try { editor.applyPreset('tiktok'); assert('preset application updates currentPreset', editor.currentPreset === 'tiktok'); } catch(e){ assert('preset application did not throw', false, e.message); }
    }

    // Export methods presence (non-executed to avoid network)
    assert('exportVideo present (export module)', typeof editor.exportVideo === 'function');

    // Timeline formatting util moved to timeline module
    if (window.FaceSeqEditorModules?.timeline){
      const style = editor.getCurrentStyle();
      const formatted = editor._formatSubtitleLines('one two three four five six seven', style);
      assert('format splits long lines', formatted.includes('<br/>'));
    }

    summary();
  } catch(err){
    assert('harness initialization', false, err.message);
    summary();
  }
})();
