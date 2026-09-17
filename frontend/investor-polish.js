/* SAREMBOK INVESTOR PRESENTATION POLISH */
(function () {
  "use strict";

  function normalizeMarkdown(s) {
    return String(s || "")
      .replace(/\\([*|\[\]()])/g, "$1")
      .replace(/(^|\n)\s*(\d+)\)\s+/g, "$1$2. ")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  function likelyAssistant(el) {
    if (!el || el.nodeType !== 1) return false;
    const marker = ((el.className || "") + " " + (el.id || "")).toLowerCase();
    return /assistant|response|bot|sarembok/.test(marker) && !/user|input|prompt/.test(marker);
  }

  function cleanAssistantDom(root) {
    const nodes = root.querySelectorAll ? root.querySelectorAll("[class], [id]") : [];
    nodes.forEach(function (el) {
      if (!likelyAssistant(el)) return;
      const text = el.textContent || "";
      if (!/\\[*|\[\]()]/.test(text) && !/\n\s*\d+\)\s+/.test(text)) return;
      if (typeof window.renderInlineMarkdown === "function" && el.children.length === 0) {
        const normalized = normalizeMarkdown(text);
        try { el.innerHTML = window.renderInlineMarkdown(normalized); return; } catch (_) {}
      }
      if (el.children.length === 0) el.textContent = normalizeMarkdown(text);
    });
  }

  function compactUi() {
    if (document.getElementById("sarembok-investor-polish-v1")) return;
    const style = document.createElement("style");
    style.id = "sarembok-investor-polish-v1";
    style.textContent = `
      .cyber-header { padding: 7px 18px 6px !important; min-height: 52px !important; }
      .header-hud-group { gap: 12px !important; font-size: 9px !important; }
      .header-brand-wrap { gap: 10px !important; }
      .srbk-reactor { width: 26px !important; height: 26px !important; }
      .header-brand-title { font-size: 17px !important; }
      .header-brand-sub { font-size: 7px !important; }
      .cyber-left-dock { width: 56px !important; padding-top: 64px !important; gap: 8px !important; }
      .dock-btn { width: 38px !important; height: 38px !important; border-radius: 10px !important; }
      #app { padding-left: 58px !important; }
      #global-input-bar { left: 58px !important; padding: 7px 18px calc(9px + env(safe-area-inset-bottom,0px)) !important; }
      #global-input-bar-inner { max-width: 980px !important; padding: 6px 10px !important; }
      #global-mic-btn, #global-send-btn { width: 36px !important; height: 36px !important; }
      #global-input-field { font-size: 14px !important; }
      .assistant-message, .message.assistant, .response-content, .chat-message.assistant { max-width: 900px !important; }
      .chat-container, .messages-container, #chat-container { padding-top: 8px !important; }
      .model-selector, .language-selector, .voice-controls { transform: scale(.92); transform-origin: right center; }
    `;
    document.head.appendChild(style);
  }

  function removeUnsupportedProductNoise() {
    const bad = /Sora-v2|GPT-4o-MoE|WorldBank-DiverseText|IBM Q-AI 2026|Scheduler 2\.0|Sarembok Flux Generator|Community Hub|Compliance Center|instant access to a GPU-backed LLM|15 concurrent tasks/i;
    document.querySelectorAll("body *").forEach(function (el) {
      if (el.children.length) return;
      if (bad.test(el.textContent || "")) el.textContent = "Live capability not verified by Runtime Authority.";
    });
  }

  function boot() {
    compactUi();
    cleanAssistantDom(document.body);
    removeUnsupportedProductNoise();
    const observer = new MutationObserver(function () {
      cleanAssistantDom(document.body);
      removeUnsupportedProductNoise();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
