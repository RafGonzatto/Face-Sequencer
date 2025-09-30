// upload_progress.js - Shared inline upload progress bar utility
(function(){
  function ensureBar(container){
    let bar = document.getElementById('inlineUploadProgress');
    if(!bar){
      const host = container || document.body;
      const wrapper = document.createElement('div');
      wrapper.style.cssText='position:absolute;left:0;right:0;bottom:0;height:4px;background:rgba(255,255,255,0.15);z-index:60;';
      const inner=document.createElement('div');
      inner.id='inlineUploadProgress';
      inner.style.cssText='height:100%;width:0%;background:#3b82f6;transition:width .15s linear;';
      wrapper.appendChild(inner);
      if (getComputedStyle(host).position === 'static') host.style.position='relative';
      host.appendChild(wrapper);
      bar=inner;
    }
    return bar;
  }
  function updateProgress(pct, container){
    const bar=ensureBar(container);
    bar.style.width = pct + '%';
    if(pct>=100){
      setTimeout(()=>{
        const wrap = bar.parentElement; if(wrap && wrap.parentElement){wrap.parentElement.removeChild(wrap);} },750);
    }
  }
  window.UploadProgress = { updateProgress };
})();