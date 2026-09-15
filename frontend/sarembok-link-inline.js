/* SAREMBOK_LINK_INLINE_20260915_V2
 * URLs are kept as raw user input. Linkification belongs to the response renderer,
 * not the input control. This prevents double Markdown/link transformations.
 */
(function () {
  'use strict';

  const INPUT_ID = 'directive-input';

  function install() {
    const input = document.getElementById(INPUT_ID);
    if (!input || input.dataset.srbkLinkPasteInstalled === '2') return;
    input.dataset.srbkLinkPasteInstalled = '2';

    // Intentionally do not rewrite pasted text. Native paste preserves the exact
    // URL and the renderer is responsible for making it clickable in responses.
    input.addEventListener('paste', function () {
      // Native browser paste path; retained as an explicit listener so older
      // deployments cannot re-register the previous Markdown-mutating handler.
      return true;
    }, { passive: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, { once: true });
  } else {
    install();
  }
  window.addEventListener('load', install, { once: true });
})();
