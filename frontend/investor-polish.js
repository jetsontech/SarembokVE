/* SAREMBOK INVESTOR PRESENTATION POLISH */
(function () {
  "use strict";

  const MODEL_SELECTORS = ["active-model-select", "user-ai-model-select"];
  const THEME_KEY = "sarembok-theme";

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function normalizeMarkdown(value) {
    return String(value || "")
      .replace(/\\([*|_`~\[\]()])/g, "$1")
      .replace(/(^|\n)\s*(\d+)\)\s+/g, "$1$2. ")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  function inlineMarkdown(value) {
    let s = escapeHtml(value);
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/__([^_]+)__/g, "<strong>$1</strong>");
    s = s.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");
    s = s.replace(/_([^_\n]+)_/g, "<em>$1</em>");
    return s;
  }

  function renderReliableMarkdown(source) {
    const md = normalizeMarkdown(source);
    if (!md) return "";
    const lines = md.split("\n");
    const out = [];
    let i = 0;

    function isTableSeparator(line) {
      const cells = line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|");
      return cells.length >= 2 && cells.every(function (cell) {
        return /^\s*:?-{3,}:?\s*$/.test(cell);
      });
    }

    function tableRow(line) {
      return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(function (cell) {
        return cell.trim();
      });
    }

    while (i < lines.length) {
      const line = lines[i].trim();
      if (!line) { i += 1; continue; }

      if (line.startsWith("|") && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
        const header = tableRow(line);
        const rows = [];
        i += 2;
        while (i < lines.length && lines[i].trim().startsWith("|")) {
          rows.push(tableRow(lines[i]));
          i += 1;
        }
        const width = header.length;
        out.push("<div class=\"srbk-md-table-wrap\"><table class=\"srbk-md-table\"><thead><tr>" +
          header.map(function (cell) { return "<th>" + inlineMarkdown(cell) + "</th>"; }).join("") +
          "</tr></thead><tbody>" +
          rows.map(function (row) {
            const cells = row.slice(0, width);
            while (cells.length < width) cells.push("");
            return "<tr>" + cells.map(function (cell) { return "<td>" + inlineMarkdown(cell) + "</td>"; }).join("") + "</tr>";
          }).join("") +
          "</tbody></table></div>");
        continue;
      }

      const heading = line.match(/^(#{1,4})\s+(.+)$/);
      if (heading) {
        const level = Math.min(4, heading[1].length);
        out.push("<h" + level + ">" + inlineMarkdown(heading[2]) + "</h" + level + ">");
        i += 1;
        continue;
      }

      if (/^[-*•]\s+/.test(line)) {
        const items = [];
        while (i < lines.length && /^\s*[-*•]\s+/.test(lines[i])) {
          items.push(lines[i].replace(/^\s*[-*•]\s+/, ""));
          i += 1;
        }
        out.push("<ul>" + items.map(function (item) { return "<li>" + inlineMarkdown(item) + "</li>"; }).join("") + "</ul>");
        continue;
      }

      if (/^\d+[.)]\s+/.test(line)) {
        const items = [];
        while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) {
          items.push(lines[i].replace(/^\s*\d+[.)]\s+/, ""));
          i += 1;
        }
        out.push("<ol>" + items.map(function (item) { return "<li>" + inlineMarkdown(item) + "</li>"; }).join("") + "</ol>");
        continue;
      }

      const paragraph = [line];
      i += 1;
      while (i < lines.length && lines[i].trim() &&
             !/^(#{1,4})\s+/.test(lines[i].trim()) &&
             !/^[-*•]\s+/.test(lines[i].trim()) &&
             !/^\d+[.)]\s+/.test(lines[i].trim()) &&
             !lines[i].trim().startsWith("|")) {
        paragraph.push(lines[i].trim());
        i += 1;
      }
      out.push("<p>" + inlineMarkdown(paragraph.join(" ")) + "</p>");
    }
    return out.join("");
  }

  function likelyAssistant(el) {
    if (!el || el.nodeType !== 1) return false;
    const marker = ((el.className || "") + " " + (el.id || "")).toLowerCase();
    return /assistant|response|bot|sarembok/.test(marker) && !/user|input|prompt/.test(marker);
  }

  function cleanAssistantDom(root) {
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll("[class], [id]").forEach(function (el) {
      if (!likelyAssistant(el)) return;
      if (el.dataset.srbkMarkdownFixed === "1") return;
      if (el.children.length) return;
      const text = el.textContent || "";
      if (!/\\[*|_`~\[\]()]/.test(text) && !/\n\s*\d+[.)]\s+/.test(text) && !/^\s*\|.+\|/m.test(text)) return;
      el.innerHTML = renderReliableMarkdown(text);
      el.dataset.srbkMarkdownFixed = "1";
      el.classList.add("srbk-markdown-rendered");
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

      /* One theme control only: retain the header control and remove the injected fixed duplicate. */
      #srbk-theme-switch { display: none !important; }
      #srbk-theme-toggle { display: inline-flex !important; }
      .hud-badge.health { display: none !important; }

      .srbk-md-table-wrap { width: 100%; overflow-x: auto; margin: 10px 0 14px; }
      .srbk-md-table { width: 100%; border-collapse: collapse; min-width: 420px; font-size: .92em; }
      .srbk-md-table th, .srbk-md-table td { text-align: left; vertical-align: top; padding: 8px 10px; border: 1px solid var(--border-subtle); }
      .srbk-md-table th { color: var(--text-main); font-weight: 600; background: var(--cyan-dim); }
      .srbk-md-table td { color: var(--text-secondary); }
      .srbk-markdown-rendered p { margin: 0 0 9px; line-height: 1.58; }
      .srbk-markdown-rendered h1, .srbk-markdown-rendered h2, .srbk-markdown-rendered h3, .srbk-markdown-rendered h4 { margin: 13px 0 7px; line-height: 1.25; }
      .srbk-markdown-rendered ul, .srbk-markdown-rendered ol { margin: 7px 0 11px 22px; padding: 0; }
      .srbk-markdown-rendered li { margin: 3px 0; line-height: 1.5; }
      .srbk-markdown-rendered code { font-family: var(--font-mono); font-size: .9em; padding: 1px 4px; border-radius: 4px; background: var(--cyan-dim); }

      /* SAREMBOK LIGHT THEME: warm ivory, soft neutral surfaces, graphite text,
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
      html[data-theme="light"] .cyber-header { background: rgba(250,248,244,.97) !important; border-bottom: 1px solid rgba(45,55,65,.10) !important; box-shadow: 0 1px 6px rgba(45,55,65,.05) !important; }
      html[data-theme="light"] .cyber-left-dock { background: #eeeae3 !important; border-right: 1px solid rgba(45,55,65,.09) !important; }
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
      html[data-theme="light"] .content-panel { background: #fbf9f5 !important; color: #2f3438 !important; border-color: rgba(45,55,65,.10) !important; box-shadow: 0 2px 10px rgba(45,55,65,.045) !important; }
      html[data-theme="light"] h1,
      html[data-theme="light"] h2,
      html[data-theme="light"] h3,
      html[data-theme="light"] h4,
      html[data-theme="light"] strong,
      html[data-theme="light"] b,
      html[data-theme="light"] .header-brand-title { color: #2f3438 !important; }
      html[data-theme="light"] p,
      html[data-theme="light"] span,
      html[data-theme="light"] label,
      html[data-theme="light"] .header-brand-subtitle,
      html[data-theme="light"] .status-label,
      html[data-theme="light"] .telemetry-label { color: #68727a; }
      html[data-theme="light"] input,
      html[data-theme="light"] textarea,
      html[data-theme="light"] select { background: #fffdf9 !important; color: #2f3438 !important; border-color: rgba(45,55,65,.14) !important; box-shadow: none !important; }
      html[data-theme="light"] button { box-shadow: none !important; }
      html[data-theme="light"] #global-input-bar { background: linear-gradient(to top, rgba(244,241,235,1), rgba(244,241,235,.96) 72%, rgba(244,241,235,0) 100%) !important; }
      html[data-theme="light"] #global-input-bar-inner { background: #fffdf9 !important; border: 1px solid rgba(45,55,65,.12) !important; box-shadow: 0 5px 18px rgba(45,55,65,.07) !important; }
      html[data-theme="light"] #global-input-field { color: #2f3438 !important; }
      html[data-theme="light"] #global-input-field::placeholder { color: #969da1 !important; }
      html[data-theme="light"] .dock-btn:hover,
      html[data-theme="light"] .dock-btn.active { background: rgba(20,125,146,.07) !important; color: #147d92 !important; }
      html[data-theme="light"] .hud-bracket { opacity: .035 !important; }
      html[data-theme="light"] #srbk-theme-toggle { background: #fffdf9 !important; color: #68727a !important; border-color: rgba(45,55,65,.12) !important; box-shadow: 0 2px 7px rgba(45,55,65,.05) !important; }
      html[data-theme="light"] ::selection { background: rgba(20,125,146,.16) !important; color: #2f3438 !important; }
    `;
    document.head.appendChild(style);
  }

  function extractModels(result) {
    const candidates = [];
    const root = result && (result.authority || result.snapshot || result.data || result.result || result);
    const compute = root && root.compute;
    const provider = root && root.provider;
    (compute && compute.configuredModelProviders || []).forEach(function (entry) { candidates.push(entry); });
    (provider && provider.configuredProviders || []).forEach(function (entry) { candidates.push(entry); });

    const seen = new Set();
    return candidates.map(function (entry) {
      if (typeof entry === "string") return { model: entry, provider: "" };
      return {
        model: entry && (entry.model || entry.modelId || entry.id || ""),
        provider: entry && (entry.name || entry.provider || "")
      };
    }).filter(function (entry) {
      if (!entry.model || seen.has(entry.model)) return false;
      seen.add(entry.model);
      return true;
    });
  }

  function updateModelSelectors(models) {
    const selects = MODEL_SELECTORS.map(function (id) { return document.getElementById(id); }).filter(Boolean);
    if (!selects.length) return;

    if (!models.length) {
      selects.forEach(function (select) {
        select.innerHTML = "";
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "LIVE MODELS UNAVAILABLE";
        select.appendChild(option);
        select.disabled = true;
        select.title = "No model inventory was returned by Runtime Authority.";
      });
      return;
    }

    let saved = "";
    try { saved = localStorage.getItem("srbk_model") || localStorage.getItem("sarembok_user_model") || ""; } catch (_) {}
    const selected = models.some(function (m) { return m.model === saved; }) ? saved : models[0].model;

    selects.forEach(function (select) {
      select.innerHTML = "";
      models.forEach(function (entry) {
        const option = document.createElement("option");
        option.value = entry.model;
        option.textContent = entry.provider ? entry.provider + " · " + entry.model : entry.model;
        select.appendChild(option);
      });
      select.value = selected;
      select.disabled = false;
      select.title = "Live model inventory from Runtime Authority";
    });

    try {
      localStorage.setItem("srbk_model", selected);
      localStorage.setItem("sarembok_user_model", selected);
    } catch (_) {}
    window.activeModel = selected;
  }

  async function refreshLiveModels() {
    if (typeof window.sendRPC !== "function") return false;
    try {
      const result = await window.sendRPC("GetRuntimeAuthority");
      const models = extractModels(result);
      updateModelSelectors(models);
      return models.length > 0;
    } catch (error) {
      console.debug("Live model inventory unavailable:", error);
      return false;
    }
  }

  function normalizeChatResult(result) {
    if (!result || typeof result !== "object") return result;
    const sections = Array.isArray(result.sections) ? result.sections : null;
    if (!sections || !sections.length) return result;
    const rendered = sections.map(function (section) {
      if (!section) return "";
      const title = section.title ? "### " + section.title : "";
      const body = section.body || section.content || "";
      const bullets = Array.isArray(section.bullets) ? section.bullets.map(function (item) { return "- " + item; }).join("\n") : "";
      return [title, body, bullets].filter(Boolean).join("\n\n");
    }).filter(Boolean).join("\n\n");
    if (rendered) result.response = rendered;
    return result;
  }

  function wrapChatRpc() {
    if (typeof window.sendRPC !== "function" || window.sendRPC.__srbkInvestorWrapped) return;
    const original = window.sendRPC;
    async function wrappedSendRPC(method, params, onDelta) {
      const result = await original.apply(this, arguments);
      return method === "SarembokChat" ? normalizeChatResult(result) : result;
    }
    wrappedSendRPC.__srbkInvestorWrapped = true;
    wrappedSendRPC.__srbkOriginal = original;
    window.sendRPC = wrappedSendRPC;
  }

  function syncThemeControl() {
    const root = document.documentElement;
    const header = document.getElementById("srbk-theme-toggle");
    if (!header) return;
    const light = root.dataset.theme === "light";
    const label = document.getElementById("srbk-theme-label");
    const icon = document.getElementById("srbk-theme-icon");
    if (label) label.textContent = light ? "DARK" : "LIGHT";
    header.setAttribute("aria-label", light ? "Switch to dark theme" : "Switch to light theme");
    header.title = light ? "Switch to dark theme" : "Switch to light theme";
    if (icon) icon.innerHTML = light
      ? '<path d="M21 12.8A8.5 8.5 0 0 1 11.2 3a6.8 6.8 0 1 0 9.8 9.8Z"></path>'
      : '<circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42"></path>';
  }

  function bindSingleThemeControl() {
    const duplicate = document.getElementById("srbk-theme-switch");
    if (duplicate) duplicate.remove();
    const header = document.getElementById("srbk-theme-toggle");
    if (!header || header.dataset.srbkBound === "1") { syncThemeControl(); return; }
    header.dataset.srbkBound = "1";
    header.addEventListener("click", function () {
      const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem(THEME_KEY, next); } catch (_) {}
      syncThemeControl();
    });
    syncThemeControl();
  }

  function removeUnsupportedProductNoise() {
    const bad = /Sora-v2|GPT-4o-MoE|WorldBank-DiverseText|IBM Q-AI 2026|Scheduler 2\.0|Sarembok Flux Generator|Community Hub|Compliance Center|instant access to a GPU-backed LLM|15 concurrent tasks/i;
    document.querySelectorAll("body *").forEach(function (el) {
      if (el.children.length) return;
      if (bad.test(el.textContent || "")) el.textContent = "Live capability not verified by Runtime Authority.";
    });
  }

  function removeDecorativeHealthAndVersion() {
    const health = document.querySelector(".hud-badge.health");
    if (health) health.remove();
    document.querySelectorAll("body *").forEach(function (el) {
      if (el.children.length) return;
      const text = el.textContent || "";
      if (/BUILD\s+2\.6\.0/i.test(text)) el.textContent = text.replace(/BUILD\s+2\.6\.0/ig, "LIVE RUNTIME");
      if (/^v2\.6$/i.test(text.trim())) el.textContent = "LIVE";
    });
  }

  function boot() {
    compactUi();
    bindSingleThemeControl();
    wrapChatRpc();
    removeDecorativeHealthAndVersion();
    removeUnsupportedProductNoise();
    cleanAssistantDom(document.body);
    refreshLiveModels();
    setTimeout(refreshLiveModels, 1500);
    setTimeout(refreshLiveModels, 4000);
    setInterval(refreshLiveModels, 30000);

    const observer = new MutationObserver(function () {
      bindSingleThemeControl();
      removeDecorativeHealthAndVersion();
      removeUnsupportedProductNoise();
      cleanAssistantDom(document.body);
      wrapChatRpc();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();