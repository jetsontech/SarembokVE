/* SAREMBOK_LINK_PASTE_INLINE_20260915
 * Preserve pasted URLs in the primary Message Sarembok field as explicit
 * Markdown links so the submitted prompt retains a clickable inline target.
 */
(function () {
  'use strict';

  const INPUT_ID = 'directive-input';
  const URL_RE = /https?:\/\/[^\s<]+/gi;

  function normalizeUrl(raw) {
    return raw.replace(/[),.;!?]+$/g, '');
  }

  function linkifyPastedText(text) {
    URL_RE.lastIndex = 0;
    return text.replace(URL_RE, function (match) {
      const url = normalizeUrl(match);
      return url ? `[${url}](${url})` : match;
    });
  }

  function install() {
    const input = document.getElementById(INPUT_ID);
    if (!input || input.dataset.srbkLinkPasteInstalled === '1') return;
    input.dataset.srbkLinkPasteInstalled = '1';

    input.addEventListener('paste', function (event) {
      const clipboard = event.clipboardData;
      if (!clipboard) return;
      const text = clipboard.getData('text/plain');
      if (!text) return;
      URL_RE.lastIndex = 0;
      if (!URL_RE.test(text)) return;

      event.preventDefault();
      const normalized = linkifyPastedText(text);
      const start = input.selectionStart ?? input.value.length;
      const end = input.selectionEnd ?? start;
      input.setRangeText(normalized, start, end, 'end');
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, { once: true });
  } else {
    install();
  }
  window.addEventListener('load', install, { once: true });
})();
