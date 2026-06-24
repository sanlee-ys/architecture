// Self-hosted, self-driven mermaid rendering — fully offline, no CDN, no Material handoff.
//
// The superfences fence emits <pre class="mermaid-src"><code>…source…</code></pre>.
// We deliberately use class "mermaid-src" (not "mermaid") so Material's built-in
// integration ignores it (it was emptying the block without rendering). We then render
// each block ourselves with the vendored mermaid (loaded just before this file), which is
// the exact mermaid.render() call verified to work with zero network.
(function () {
  function theme() {
    return document.body.getAttribute('data-md-color-scheme') === 'slate' ? 'dark' : 'default';
  }
  function renderAll() {
    if (!window.mermaid || typeof window.mermaid.render !== 'function') return;
    window.mermaid.initialize({ startOnLoad: false, securityLevel: 'loose', theme: theme() });
    document.querySelectorAll('pre.mermaid-src').forEach(function (el, i) {
      var src = el.textContent;
      window.mermaid.render('mmd_' + i, src)
        .then(function (out) {
          var div = document.createElement('div');
          div.className = 'mermaid-rendered';
          div.style.textAlign = 'center';
          div.innerHTML = out.svg;
          el.replaceWith(div);
        })
        .catch(function (e) { console.error('mermaid render failed:', e); });
    });
  }
  if (document.readyState !== 'loading') renderAll();
  else document.addEventListener('DOMContentLoaded', renderAll);
})();
