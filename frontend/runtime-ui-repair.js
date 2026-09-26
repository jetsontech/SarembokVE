/* SAREMBOK_RUNTIME_UI_REPAIR_V1_20260917 */
(function installSarembokRuntimeUiRepair() {
    "use strict";

    if (window.__srbkRuntimeUiRepairV1) return;
    window.__srbkRuntimeUiRepairV1 = true;

    const nativeFetch = window.fetch.bind(window);

    function clearBrowserSession() {
        window.browserSessionToken = null;
        try { sessionStorage.removeItem("srbk_browser_session_token"); } catch (_) {}
    }

    async function freshBrowserSession() {
        clearBrowserSession();
        const resp = await nativeFetch("/api/session", {
            cache: "no-store",
            headers: { "Accept": "application/json" }
        });
        if (!resp.ok) throw new Error(`Session request failed (${resp.status})`);
        const data = await resp.json();
        const token = data && (data.sessionToken || data.token || data.browserSessionToken);
        if (!token) throw new Error("Session endpoint returned no browser session token");
        window.browserSessionToken = token;
        try { sessionStorage.setItem("srbk_browser_session_token", token); } catch (_) {}
        return token;
    }

    function isAuthFailure(err) {
        const code = Number(err && err.code);
        const message = String((err && err.message) || "").toLowerCase();
        return code === -32001 || message.includes("authentication_required") || message.includes("browser session") || message.includes("session token");
    }

    function isTransportFailure(err) {
        const message = String((err && err.message) || "").toLowerCase();
        return message.includes("websocket") || message.includes("runtime connection") || message.includes("runtime transport");
    }

    function readyResponse(data, status = 200) {
        return new Response(JSON.stringify(data), {
            status,
            headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" }
        });
    }

    async function callRuntime(method, params = {}, attempt = 0) {
        if (typeof window.sendRPC !== "function") {
            throw new Error("Canonical sendRPC is not available");
        }
        try {
            return await window.sendRPC(method, params);
        } catch (err) {
            if (attempt === 0 && isAuthFailure(err)) {
                await freshBrowserSession();
                return callRuntime(method, params, 1);
            }
            if (attempt === 0 && isTransportFailure(err) && typeof window.ensureConnected === "function") {
                const connected = await window.ensureConnected(6000);
                if (connected) return callRuntime(method, params, 1);
            }
            throw err;
        }
    }

    function installCanonicalRpcRecovery() {
        const original = window.sendRPC;
        if (typeof original !== "function" || original.__srbkRuntimeUiRepairV1) return;

        async function repairedSendRPC(...args) {
            try {
                return await original.apply(this, args);
            } catch (err) {
                if (!isAuthFailure(err)) throw err;
                await freshBrowserSession();
                return original.apply(this, args);
            }
        }

        repairedSendRPC.__srbkRuntimeUiRepairV1 = true;
        repairedSendRPC.__srbkOriginal = original;
        window.sendRPC = repairedSendRPC;

        if (typeof window.sendRpc !== "function") {
            window.sendRpc = repairedSendRPC;
        }
    }

    function installNavigationGuard() {
        const original = window.switchTab;
        if (typeof original !== "function" || original.__srbkRuntimeUiRepairV1) return;

        function repairedSwitchTab(tabId) {
            const target = document.getElementById(`view-${tabId}`);
            if (!target) {
                console.warn(`[sarembok] Unknown UI tab: ${tabId}`);
                return false;
            }
            const result = original.call(this, tabId);
            if (!target.classList.contains("active")) {
                document.querySelectorAll(".view-panel").forEach(panel => panel.classList.remove("active"));
                target.classList.add("active");
            }
            const activeBtn = document.getElementById(`dock-btn-${tabId}`);
            if (activeBtn) {
                document.querySelectorAll(".dock-btn").forEach(btn => btn.classList.remove("active"));
                activeBtn.classList.add("active");
            }
            return result === undefined ? true : result;
        }

        repairedSwitchTab.__srbkRuntimeUiRepairV1 = true;
        repairedSwitchTab.__srbkOriginal = original;
        window.switchTab = repairedSwitchTab;
    }

    function installTruthfulTelemetry() {
        const original = window.updateTelemetryUI;
        if (typeof original !== "function" || original.__srbkRuntimeUiRepairV1) return;

        function repairedTelemetry(info) {
            const data = info && typeof info === "object" ? info : {};
            if (typeof original === "function") {
                try { original.call(this, info); } catch (err) { console.debug("[sarembok] native telemetry updater notice:", err); }
            }

            const runtime = data.runtime || {};
            const memory = data.memory || {};
            const agents = data.agents || {};
            const scheduler = data.scheduler || {};

            const memCount = memory.entries ?? data.totalMemories ?? data.memoryCount ?? 0;
            const agentsCount = agents.online ?? data.activeAgents ?? data.agentCount ?? 0;
            const queueDepth = scheduler.queueDepth ?? data.queueDepth ?? 0;
            const status = runtime.status ?? data.status ?? "UNKNOWN";

            const memEl = document.getElementById("deck-mem-entries");
            const agentsEl = document.getElementById("deck-agents-online");
            const queueEl = document.getElementById("deck-queue-depth");
            const sysEl = document.getElementById("hud-system-status");
            if (memEl) memEl.textContent = `${memCount} STORED`;
            if (agentsEl) agentsEl.textContent = `${agentsCount} ONLINE`;
            if (queueEl) queueEl.textContent = `${queueDepth} QUEUED`;
            if (sysEl) sysEl.textContent = status;
        }
        repairedTelemetry.__srbkRuntimeUiRepairV1 = true;
        repairedTelemetry.__srbkOriginal = original;
        window.updateTelemetryUI = repairedTelemetry;
    }

    function installLegacyApiBridge() {
        if (window.fetch.__srbkRuntimeUiRepairV1) return;

        const bridgeFetch = async function(input, init = {}) {
            const rawUrl = typeof input === "string" ? input : (input && input.url) || "";
            const url = new URL(rawUrl, window.location.href);
            if (url.origin !== window.location.origin) {
                return nativeFetch(input, init);
            }

            try {
                /*
                 * TTS compatibility repair:
                 * The canonical production /api/tts endpoint accepts POST.
                 * The legacy browser voice client calls it with GET.  Allow the
                 * existing client to remain backward-compatible by normalizing
                 * only this same-origin TTS request to POST before it reaches
                 * Caddy/Cloudflare.  This prevents the edge from returning an
                 * HTML 502 for voice profiles such as am_adam.
                 */
                if (url.pathname === "/api/tts" && String(init.method || "GET").toUpperCase() === "GET") {
                    const postInit = { ...init, method: "POST" };
                    return nativeFetch(input, postInit);
                }

                if (url.pathname === "/api/background-tasks") {
                    const data = await callRuntime("ListTasks");
                    const tasks = Array.isArray(data?.tasks) ? data.tasks : [];
                    return readyResponse({
                        tasks: tasks.map(task => ({
                            task_id: task.taskId,
                            payload: typeof task.payload === "string" ? task.payload : JSON.stringify(task.payload || {}),
                            status: task.status,
                            created_at: task.createdAt,
                            sender_agent_id: task.assignedWorkerId || "RUNTIME",
                            tokens_consumed: 0,
                            committed: task.status === "COMPLETED" ? 1 : 0
                        }))
                    });
                }

                if (url.pathname === "/api/execute-task") {
                    let body = {};
                    try { body = JSON.parse(init.body || "{}"); } catch (_) {}
                    const data = await callRuntime("ScheduleCompute", {
                        taskType: "background_directive",
                        requiredCapability: "compute",
                        payload: { prompt: body.task || "", source: "background-ui" }
                    });
                    return readyResponse(data);
                }

                if (url.pathname === "/api/chat-sessions") {
                    const data = await callRuntime("ListUserChatSessions");
                    return readyResponse(data);
                }

                if (url.pathname === "/api/auth/master" && String(init.method || "GET").toUpperCase() === "POST") {
                    let body = {};
                    try { body = JSON.parse(init.body || "{}"); } catch (_) {}
                    const data = await callRuntime("AuthenticateMaster", { passcode: body.passcode || "" });
                    return readyResponse(data);
                }

                if (url.pathname === "/api/auth/social" && String(init.method || "GET").toUpperCase() === "POST") {
                    let body = {};
                    try { body = JSON.parse(init.body || "{}"); } catch (_) {}
                    const data = await callRuntime("AuthenticateSocialUser", body);
                    return readyResponse(data);
                }
            } catch (err) {
                return readyResponse({ error: String(err.message || err) }, 500);
            }

            return nativeFetch(input, init);
        };

        bridgeFetch.__srbkRuntimeUiRepairV1 = true;
        bridgeFetch.__srbkOriginal = nativeFetch;
        window.fetch = bridgeFetch;
    }

    function installTaskUiBridge() {
        const originalDispatch = window.dispatchBackgroundTask;
        if (typeof originalDispatch === "function" && !originalDispatch.__srbkRuntimeUiRepairV1) {
            async function repairedDispatch(prompt) {
                if (!prompt) return;
                if (typeof window.interruptSpeech === "function") window.interruptSpeech();
                if (typeof window.appendUserDialogue === "function") window.appendUserDialogue(`[BACKGROUND DIRECTIVE] ${prompt}`);
                const history = document.getElementById("dialogue-history");
                if (!history) return;

                const cardId = `task-card-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
                const card = document.createElement("div");
                card.id = cardId;
                card.className = "srbk-bubble assistant task-bubble";
                card.innerHTML = `
                    <div class="srbk-bubble-sender">
                        <span>BACKGROUND TASK</span>
                        <span class="drawer-badge running" id="task-status-${cardId}">SUBMITTING</span>
                    </div>
                    <div class="srbk-content">
                        <p style="font-weight:600; color:#fff; margin-bottom:6px;">${escapeHtml(String(prompt))}</p>
                        <div id="task-output-${cardId}" style="font-family:var(--font-mono); font-size:11px; color:var(--text-secondary);">Submitting task to the runtime scheduler…</div>
                    </div>`;
                history.appendChild(card);
                if (typeof window.scrollDialogue === "function") window.scrollDialogue();

                try {
                    const data = await callRuntime("ScheduleCompute", {
                        taskType: "background_directive",
                        requiredCapability: "compute",
                        payload: { prompt: String(prompt), source: "background-ui" }
                    });
                    const taskId = data?.taskId || "UNKNOWN";
                    const state = String(data?.status || "UNKNOWN").toUpperCase();
                    const statusEl = document.getElementById(`task-status-${cardId}`);
                    const outEl = document.getElementById(`task-output-${cardId}`);
                    if (statusEl) {
                        statusEl.className = `drawer-badge ${state === "COMPLETED" ? "good" : "running"}`;
                        statusEl.textContent = state;
                    }
                    if (outEl) {
                        outEl.innerHTML = `Runtime task <strong>${escapeHtml(taskId)}</strong> is ${escapeHtml(state)}${data?.assignedWorkerId ? ` on ${escapeHtml(data.assignedWorkerId)}` : " with no worker assigned yet"}.`;
                    }
                    if (typeof window.saveCurrentChatSession === "function") window.saveCurrentChatSession();
                    if (typeof window.showToast === "function") window.showToast(`BACKGROUND TASK ${taskId} · ${state}`);
                } catch (err) {
                    const statusEl = document.getElementById(`task-status-${cardId}`);
                    const outEl = document.getElementById(`task-output-${cardId}`);
                    if (statusEl) { statusEl.className = "drawer-badge warn"; statusEl.textContent = "FAILED"; }
                    if (outEl) outEl.textContent = `Task submission failed: ${err.message}`;
                }
            }
            repairedDispatch.__srbkRuntimeUiRepairV1 = true;
            repairedDispatch.__srbkOriginal = originalDispatch;
            window.dispatchBackgroundTask = repairedDispatch;
        }
    }

    function installTaskListBridge() {
        const original = window.loadBackgroundTasksList;
        if (typeof original !== "function" || original.__srbkRuntimeUiRepairV1) return;

        async function repairedList() {
            const listEl = document.getElementById("drawer-tasks-list");
            const countEl = document.getElementById("drawer-task-count");
            if (!listEl) return;
            try {
                const data = await callRuntime("ListTasks");
                const tasks = Array.isArray(data?.tasks) ? data.tasks : [];
                if (countEl) countEl.textContent = tasks.length;
                if (!tasks.length) {
                    listEl.innerHTML = `<div style="color:var(--text-muted);font-size:11px;font-family:var(--font-mono);text-align:center;padding:24px;">No runtime tasks recorded yet.</div>`;
                    return;
                }
                listEl.innerHTML = tasks.map(task => {
                    const state = String(task.status || "UNKNOWN").toUpperCase();
                    const badgeClass = state === "COMPLETED" ? "good" : (["FAILED", "CANCELLED"].includes(state) ? "warn" : "running");
                    let payload = task.payload;
                    if (typeof payload !== "string") {
                        try { payload = JSON.stringify(payload || {}); } catch (_) { payload = ""; }
                    }
                    return `<div class="drawer-card">
                        <div class="drawer-card-header"><span style="font-weight:700;color:var(--cyan);">${escapeHtml(task.taskId || "")}</span><span class="drawer-badge ${badgeClass}">${escapeHtml(state)}</span></div>
                        <div style="font-size:11px;color:#fff;word-break:break-word;">${escapeHtml(payload)}</div>
                        <div style="font-family:var(--font-mono);font-size:9.5px;color:var(--text-muted);">${escapeHtml(task.assignedWorkerId || "UNASSIGNED")} · ${escapeHtml(task.requiredCapability || "")} · ${escapeHtml(task.createdAt || "")}</div>
                    </div>`;
                }).join("");
            } catch (err) {
                listEl.innerHTML = `<div style="color:var(--amber);font-size:11px;font-family:var(--font-mono);text-align:center;padding:16px;">Failed to query runtime tasks: ${escapeHtml(err.message)}</div>`;
            }
        }
        repairedList.__srbkRuntimeUiRepairV1 = true;
        repairedList.__srbkOriginal = original;
        window.loadBackgroundTasksList = repairedList;
    }

    function installLedgerExportBridge() {
        const original = window.exportWalLedgerJson;
        if (typeof original !== "function" || original.__srbkRuntimeUiRepairV1) return;

        async function repairedExport() {
            try {
                const data = await callRuntime("ListTasks");
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `sarembok_runtime_tasks_${Date.now()}.json`;
                a.click();
                URL.revokeObjectURL(url);
                if (typeof window.showToast === "function") window.showToast("EXPORTED RUNTIME TASK LEDGER (.JSON)");
            } catch (_) {
                if (typeof window.showToast === "function") window.showToast("Failed to export runtime task ledger.");
            }
        }
        repairedExport.__srbkRuntimeUiRepairV1 = true;
        repairedExport.__srbkOriginal = original;
        window.exportWalLedgerJson = repairedExport;
    }

    function healthSnapshot() {
        const views = Array.from(document.querySelectorAll(".view-panel")).map(el => el.id.replace(/^view-/, ""));
        const dockButtons = Array.from(document.querySelectorAll(".dock-btn")).map(el => el.id.replace(/^dock-btn-/, ""));
        const themeButton = document.getElementById("srbk-theme-toggle");
        const mdRenderer = typeof window.md === "function";
        let markdownTest = false;
        if (mdRenderer) {
            try {
                const rendered = window.md("\\*\\*SAREMBOK\\*\\*\n\n- one\n- two");
                markdownTest = /<strong>SAREMBOK<\/strong>/.test(rendered) && /<li/.test(rendered);
            } catch (_) {}
        }
        window.__srbkRuntimeUiHealth = {
            runtimeRepair: true,
            rpcRecovery: typeof window.sendRPC === "function",
            navigation: views.length > 0 && dockButtons.every(id => views.includes(id)),
            views,
            dockButtons,
            markdownRenderer: mdRenderer && markdownTest,
            themeControl: !!themeButton,
            timestamp: new Date().toISOString()
        };
        console.info("[Sarembok] runtime UI health", window.__srbkRuntimeUiHealth);
    }

    function installMobileConsoleRepair() {
        if (document.getElementById("srbk-mobile-console-repair")) return;

        const style = document.createElement("style");
        style.id = "srbk-mobile-console-repair";
        style.textContent = `
            @media (max-width: 768px) {
                /* Keep the console composer visible above the mobile dock and keyboard. */
                /* Restore the mobile navigation dock above all page content. */
                .cyber-left-dock {
                    display: flex !important;
                    position: fixed !important;
                    top: auto !important;
                    left: 0 !important;
                    right: 0 !important;
                    bottom: 0 !important;
                    width: 100% !important;
                    height: 52px !important;
                    z-index: 10060 !important;
                    visibility: visible !important;
                    opacity: 1 !important;
                }
                .cyber-left-dock .dock-btn {
                    display: flex !important;
                    visibility: visible !important;
                    opacity: 1 !important;
                }
                #global-input-bar {
                    display: flex !important;
                    position: fixed !important;
                    left: 0 !important;
                    right: 0 !important;
                    bottom: 52px !important;
                    width: 100% !important;
                    z-index: 10050 !important;
                    visibility: visible !important;
                    opacity: 1 !important;
                    padding: 8px 10px calc(8px + env(safe-area-inset-bottom, 0px)) !important;
                    pointer-events: none !important;
                }
                #global-input-bar-inner {
                    display: flex !important;
                    width: 100% !important;
                    min-height: 54px !important;
                    visibility: visible !important;
                    pointer-events: auto !important;
                }
                #global-input-field {
                    display: block !important;
                    visibility: visible !important;
                    opacity: 1 !important;
                    min-width: 0 !important;
                    min-height: 40px !important;
                    flex: 1 1 auto !important;
                    font-size: 16px !important;
                    line-height: 1.35 !important;
                    -webkit-user-select: text !important;
                    user-select: text !important;
                }
                #global-send-btn,
                #global-mic-btn,
                #global-vision-btn {
                    flex: 0 0 auto !important;
                }
                #global-bg-btn {
                    display: none !important;
                }
                /* Prevent the active view from scrolling the composer underneath content. */
                .view-panel.active {
                    padding-bottom: 150px !important;
                }
                #srbk-mobile-main-site {
                    display: flex !important;
                }
            }
            @media (min-width: 769px) {
                #srbk-mobile-main-site { display: none !important; }
            }
        `;
        document.head.appendChild(style);

        const back = document.createElement("button");
        back.id = "srbk-mobile-main-site";
        back.type = "button";
        back.setAttribute("aria-label", "Return to Sarembok main site");
        back.title = "Return to main site";
        back.innerHTML = '<span aria-hidden="true">‹</span><span>MAIN SITE</span>';
        back.style.cssText = [
            "position:fixed",
            "top:calc(10px + env(safe-area-inset-top, 0px))",
            "left:10px",
            "z-index:10060",
            "display:none",
            "align-items:center",
            "gap:6px",
            "height:36px",
            "padding:0 11px 0 8px",
            "border:1px solid rgba(0,240,255,.32)",
            "border-radius:18px",
            "background:rgba(3,8,16,.92)",
            "backdrop-filter:blur(14px)",
            "-webkit-backdrop-filter:blur(14px)",
            "color:#00f0ff",
            "font:700 9px/1 JetBrains Mono,monospace",
            "letter-spacing:.08em",
            "box-shadow:0 6px 24px rgba(0,0,0,.45)"
        ].join(";");
        back.addEventListener("click", function () {
            try { window.location.assign("/"); } catch (_) { window.location.href = "/"; }
        });
        document.body.appendChild(back);

        function refreshMobileLayout() {
            const bar = document.getElementById("global-input-bar");
            const field = document.getElementById("global-input-field");
            if (!bar || !field) return;
            const mobile = window.matchMedia("(max-width: 768px)").matches;
            back.style.display = mobile ? "flex" : "none";
            if (mobile) {
                bar.style.display = "flex";
                bar.style.left = "0";
                bar.style.right = "0";
                bar.style.bottom = "0";
                field.style.display = "block";
                field.style.visibility = "visible";
                field.style.opacity = "1";
            }
        }

        refreshMobileLayout();
        window.addEventListener("resize", refreshMobileLayout, { passive: true });
        if (window.visualViewport) {
            window.visualViewport.addEventListener("resize", refreshMobileLayout, { passive: true });
        }
    }

    function install() {
        installCanonicalRpcRecovery();
        installMobileConsoleRepair();
        installNavigationGuard();
        installTruthfulTelemetry();
        installLegacyApiBridge();
        installTaskUiBridge();
        installTaskListBridge();
        installLedgerExportBridge();
        healthSnapshot();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", install, { once: true });
    } else {
        install();
    }
    window.addEventListener("load", healthSnapshot, { once: true });
})();
