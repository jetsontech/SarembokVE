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

      /* SAREMBOK LIGHT THEME: a deliberate visual system, not an inversion.
         Warm ivory canvas, soft neutral surfaces, graphite typography,
         muted blue-gray secondary text, restrained cyan accents, subtle depth. */
      html[data-theme="light"] {
        color-scheme: light !important;
        --bg-void: #f4f1eb !important;
        --bg-surface: #faf8f4 !important;
        --bg-card: #fffdf9 !important;
        --border-glass: rgba(45,55,65,.12) !important;
        --border-subtle: rgba(45,55,65,.10) !important;
        --cyan: #147d92 !important;
        --cyan-glow: rgba(20,125,146,.12) !important;
        --cyan-dim: rgba(20,125,146,.07) !important;
        --amber: #9a6414 !important;
        --amber-glow: rgba(154,100,20,.10) !important;
        --emerald: #17745b !important;
        --indigo: #565b88 !important;
        --danger: #a63d3d !important;
        --text-main: #2f3438 !important;
        --text-secondary: #68727a !important;
        --text-muted: #8b949a !important;
      }
      html[data-theme="light"] body,
      html[data-theme="light"] #app,
      html[data-theme="light"] .cyber-main,
      html[data-theme="light"] .main-content,
      html[data-theme="light"] .workspace,
      html[data-theme="light"] .content-area {
        background: #f4f1eb !important;
        color: #2f3438 !important;
      }
      html[data-theme="light"] .cyber-header {
        background: rgba(250,248,244,.97) !important;
        border-bottom: 1px solid rgba(45,55,65,.10) !important;
        box-shadow: 0 1px 6px rgba(45,55,65,.05) !important;
      }
      html[data-theme="light"] .cyber-left-dock {
        background: #eeeae3 !important;
        border-right: 1px solid rgba(45,55,65,.09) !important;
      }
      html[data-theme="light"] .panel,
      html[data-theme="light"] .card,
      html[data-theme="light"] .glass-panel,
      html[data-theme="light"] .cockpit-panel,
      html[data-theme="light"] .agent-panel,
      html[data-theme="light"] .task-panel,
      html[data-theme="light"] .response-panel,
      html[data-theme="light"] .chat-panel,
      html[data-theme="light"] .message,
      html[data-theme="light"] .output-panel,
      html[data-theme="light"] .content-panel {
        background: #fbf9f5 !important;
        color: #2f3438 !important;
        border-color: rgba(45,55,65,.10) !important;
        box-shadow: 0 2px 10px rgba(45,55,65,.045) !important;
      }
      html[data-theme="light"] h1,
      html[data-theme="light"] h2,
      html[data-theme="light"] h3,
      html[data-theme="light"] h4,
      html[data-theme="light"] strong,
      html[data-theme="light"] b,
      html[data-theme="light"] .header-brand-title {
        color: #2f3438 !important;
      }
      html[data-theme="light"] p,
      html[data-theme="light"] span,
      html[data-theme="light"] label,
      html[data-theme="light"] .header-brand-subtitle,
      html[data-theme="light"] .status-label,
      html[data-theme="light"] .telemetry-label {
        color: #68727a;
      }
      html[data-theme="light"] input,
      html[data-theme="light"] textarea,
      html[data-theme="light"] select {
        background: #fffdf9 !important;
        color: #2f3438 !important;
        border-color: rgba(45,55,65,.14) !important;
        box-shadow: none !important;
      }
      html[data-theme="light"] button { box-shadow: none !important; }
      html[data-theme="light"] #global-input-bar {
        background: linear-gradient(to top, rgba(244,241,235,1), rgba(244,241,235,.96) 72%, rgba(244,241,235,0) 100%) !important;
      }
      html[data-theme="light"] #global-input-bar-inner {
        background: #fffdf9 !important;
        border: 1px solid rgba(45,55,65,.12) !important;
        box-shadow: 0 5px 18px rgba(45,55,65,.07) !important;
      }
      html[data-theme="light"] #global-input-field { color: #2f3438 !important; }
      html[data-theme="light"] #global-input-field::placeholder { color: #969da1 !important; }
      html[data-theme="light"] .dock-btn:hover,
      html[data-theme="light"] .dock-btn.active {
        background: rgba(20,125,146,.07) !important;
        color: #147d92 !important;
      }
      html[data-theme="light"] .hud-bracket { opacity: .035 !important; }
      html[data-theme="light"] .srbk-theme-switch,
      html[data-theme="light"] .srbk-theme-toggle {
        background: #fffdf9 !important;
        color: #68727a !important;
        border-color: rgba(45,55,65,.12) !important;
        box-shadow: 0 2px 7px rgba(45,55,65,.05) !important;
      }
      html[data-theme="light"] ::selection {
        background: rgba(20,125,146,.16) !important;
        color: #2f3438 !important;
      }
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