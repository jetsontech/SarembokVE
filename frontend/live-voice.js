(function () {
    "use strict";

    // Native Gemini Live voice is the unified speech and duplex conversation engine
    // for all audio synthesis and voice interaction across SarembokVE.
    // Sarembok remains the authenticated control plane for tools, identity,
    // memory, persistence, and agent/runtime state.

    var LIVE_WS_BASE =
        "wss://generativelanguage.googleapis.com/ws/" +
        "google.ai.generativelanguage.v1beta.GenerativeService." +
        "BidiGenerateContentConstrained";

    var nativeLiveSocket = null;
    var nativeLiveActive = false;
    var nativeLiveStopping = false;
    var nativeLiveMode = "conversational";
    var nativeLiveReconnecting = false;
    var nativeLiveConfig = null;
    var nativeLiveMediaStream = null;
    var nativeInputContext = null;
    var nativeOutputContext = null;
    var nativeMicSource = null;
    var nativeInputWorklet = null;
    var nativeWorkletUrl = null;
    var nativeWorkletLoaded = false;
    var nativeOutputSources = new Set();
    var nativeNextAudioTime = 0;
    var nativeSetupComplete = false;
    var nativeTurnUserText = "";
    var nativeTurnAssistantText = "";
    var nativeUserBubble = null;
    var nativeAssistantBubble = null;
    var nativeHistory = [];
    var nativeReconnectTimer = null;
    var nativeStartPromise = null;
    var nativeConnectionGeneration = 0;

    var LIVE_TOOLS = {
        get_runtime_info: "GetRuntimeInfo",
        get_provider_metrics: "GetProviderMetrics",
        list_workers: "ListWorkers",
        list_tasks: "ListTasks",
        search_memory: "SearchMemories",
        browser_session_open: "BrowserSessionOpen",
        browser_inspect: "BrowserSessionInspect",
        browser_action: "BrowserAction",
        browser_session_close: "BrowserSessionClose",
        mcp_list_servers: "ListMcpServers",
        mcp_call: "CallMcpTool",
        play_media: "ResolveMediaStream",
        popout_media: "PopoutMedia",
        stop_media: "StopMedia",
        generate_flyer: "GenerateFlyer"
    };

    function srbkSendRPC(method, params, onDelta) {
        if (typeof window.sendRPC === "function") {
            return window.sendRPC(method, params || {}, onDelta || null);
        }
        if (typeof sendRPC === "function") {
            return sendRPC(method, params || {}, onDelta || null);
        }
        return Promise.reject(new Error("Sarembok RPC client is unavailable"));
    }

    async function ensureBrowserSession() {
        if (window.browserSessionToken) return window.browserSessionToken;

        if (typeof window.initSession === "function") {
            var sessionToken = await window.initSession();
            if (sessionToken) return sessionToken;
        }
        if (typeof initSession === "function") {
            var fallbackToken = await initSession();
            if (fallbackToken) return fallbackToken;
        }

        var response = await fetch("/api/session", {
            method: "GET",
            cache: "no-store",
            headers: { "Accept": "application/json" }
        });
        if (!response.ok) throw new Error("Sarembok session HTTP " + response.status);
        var data = await response.json();
        var token = String(data.sessionToken || "").trim();
        if (!token) throw new Error("Sarembok session token was not returned");
        window.browserSessionToken = token;
        return token;
    }

    async function fetchLiveToken(mode) {
        var lastError = null;
        for (var attempt = 1; attempt <= 3; attempt++) {
            try {
                var sessionToken = await ensureBrowserSession();
        var response = await fetch(
            "/api/live/token?mode=" + encodeURIComponent(mode),
            {
                method: "GET",
                cache: "no-store",
                headers: {
                    "Accept": "application/json",
                    "Authorization": "Bearer " + sessionToken
                }
            }
        );

        if (response.status === 401) {
            window.browserSessionToken = "";
            sessionToken = await ensureBrowserSession();
            response = await fetch(
                "/api/live/token?mode=" + encodeURIComponent(mode),
                {
                    method: "GET",
                    cache: "no-store",
                    headers: {
                        "Accept": "application/json",
                        "Authorization": "Bearer " + sessionToken
                    }
                }
            );
        }

        var bodyText = await response.text();
        var data = {};
        try { data = JSON.parse(bodyText || "{}"); } catch (_) {}

        if (!response.ok) {
            throw new Error(String(
                data.detail || data.error || "Gemini Live token HTTP " + response.status
            ));
        }
        if (!data.token || !data.setup || !data.model) {
            throw new Error("Gemini Live token response is incomplete");
        }
                return data;
            } catch (err) {
                lastError = err;
                if (attempt < 3) {
                    await new Promise(function(resolve) {
                        setTimeout(resolve, 350 * attempt);
                    });
                }
            }
        }
        throw new Error("Live token request failed after 3 attempts: " + String(lastError && lastError.message || lastError || "network error"));
    }

    function setNativeLiveStatus(state, hint) {
        try {
            if (typeof setLiveConvUI === "function") setLiveConvUI(state, hint);
        } catch (_) {}

        var btn = document.getElementById("hud-live-2way-btn");
        if (btn) {
            btn.classList.toggle("active", nativeLiveActive);
            var label = btn.querySelector("span");
            if (label) label.textContent = nativeLiveActive ? "LIVE VOICE: ACTIVE" : "LIVE VOICE";
        }

        var liveConvBtn = document.getElementById("live-conv-btn");
        if (liveConvBtn) {
            liveConvBtn.classList.toggle("active", nativeLiveActive);
            var liveConvText = document.getElementById("live-conv-btn-text");
            if (liveConvText) {
                liveConvText.textContent = nativeLiveActive
                    ? "LIVE CONVERSATION: ACTIVE"
                    : "LIVE CONVERSATION";
            }
        }

        var liveConvHud = document.getElementById("live-conv-hud");
        if (liveConvHud) {
            liveConvHud.classList.toggle("active", nativeLiveActive);
        }

        var modeButton = document.getElementById("live-mode-toggle-btn");
        if (modeButton) {
            modeButton.textContent =
                nativeLiveMode === "agentic" ? "LIVE MODE: DEEP" : "LIVE MODE: FAST";
            modeButton.title =
                nativeLiveMode === "agentic"
                    ? "Deep agentic Live is active. Tap to return to Fast."
                    : "Fast conversational Live is active. Tap for Deep agentic Live.";
        }

        var mic = document.getElementById("dialogue-mic-btn");
        if (mic) {
            mic.classList.toggle("active", nativeLiveActive);
            mic.title = nativeLiveActive
                ? "Stop native Gemini Live conversation"
                : "Start native Gemini Live conversation";
        }

        try {
            if (typeof setAvatarSignal === "function") {
                if (state.indexOf("SPEAKING") >= 0) setAvatarSignal("SPEAKING");
                else if (state.indexOf("LISTENING") >= 0 || state.indexOf("HEARING") >= 0) setAvatarSignal("LISTENING");
                else if (state.indexOf("CONNECTING") >= 0) setAvatarSignal("ATTENTION");
            }
        } catch (_) {}

        window.liveConversationActive = nativeLiveActive;
        try {
            if (typeof liveConversationActive !== "undefined") {
                liveConversationActive = nativeLiveActive;
            }
        } catch (_) {}

        var input = document.getElementById("directive-input");
        if (input) {
            if (nativeLiveActive) {
                var voiceName = (nativeLiveConfig && nativeLiveConfig.setup && nativeLiveConfig.setup.generationConfig && nativeLiveConfig.setup.generationConfig.speechConfig && nativeLiveConfig.setup.generationConfig.speechConfig.voiceConfig && nativeLiveConfig.setup.generationConfig.speechConfig.voiceConfig.prebuiltVoiceConfig && nativeLiveConfig.setup.generationConfig.speechConfig.voiceConfig.prebuiltVoiceConfig.voiceName) || "Kore";
                input.placeholder = "Message Sarembok (Live Voice Active · " + voiceName + ")...";
                input.classList.add("live-active");
            } else {
                input.placeholder = "Message Sarembok V E, attach files, or tap mic...";
                input.classList.remove("live-active");
            }
        }
    }

    function logNativeLive(message, level) {
        try {
            if (typeof addTerminalLine === "function") {
                addTerminalLine("[live] " + message, level || "cyan");
            }
        } catch (_) {}
    }

    function base64FromBytes(bytes) {
        var binary = "";
        var step = 0x8000;
        for (var i = 0; i < bytes.length; i += step) {
            var slice = bytes.subarray(i, Math.min(i + step, bytes.length));
            binary += String.fromCharCode.apply(null, slice);
        }
        return btoa(binary);
    }

    function bytesFromBase64(value) {
        var raw = atob(String(value || ""));
        var out = new Uint8Array(raw.length);
        for (var i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
        return out;
    }

    function clearNativeOutputAudio() {
        // Gemini Live is the sole voice authority. Browser SpeechSynthesis is disabled.
        nativeNextAudioTime = nativeOutputContext
            ? nativeOutputContext.currentTime
            : 0;

        nativeOutputSources.forEach(function (source) {
            try {
                source.onended = null;
                source.stop(0);
            } catch (_) {}
            try { source.disconnect(); } catch (_) {}
        });
        nativeOutputSources.clear();
    }

    function queueNativeOutputPcm(bytes) {
        if (!bytes || bytes.byteLength < 2) return;
        if (!nativeOutputContext) return;

        // Privacy & Mute check: if user turned VOICE: OFF, NEVER play audio
        if (typeof window.voiceEnabled !== "undefined" && !window.voiceEnabled) {
            return;
        }

        // Resume audio context if suspended (browser autoplay policy unlock)
        if (nativeOutputContext.state === "suspended") {
            nativeOutputContext.resume().catch(function () {});
        }

        // Silence any lingering background media or previous audio elements
        try {
            if (window.activeNeuralAudio && typeof window.activeNeuralAudio.pause === "function") {
                window.activeNeuralAudio.pause();
                window.activeNeuralAudio = null;
            }
        } catch (_) {}

        var usable = bytes.byteLength - (bytes.byteLength % 2);
        var pcm = new Int16Array(bytes.buffer, bytes.byteOffset, usable / 2);
        if (!pcm.length) return;

        var samples = new Float32Array(pcm.length);
        for (var i = 0; i < pcm.length; i++) {
            samples[i] = pcm[i] / 32768;
        }

        var buffer = nativeOutputContext.createBuffer(
            1,
            samples.length,
            24000
        );
        buffer.copyToChannel(samples, 0);

        var source = nativeOutputContext.createBufferSource();
        source.buffer = buffer;
        source.connect(nativeOutputContext.destination);

        var now = nativeOutputContext.currentTime;
        if (nativeNextAudioTime < now || nativeNextAudioTime > now + 2.0) {
            nativeNextAudioTime = now;
        }
        var startAt = Math.max(
            nativeNextAudioTime,
            now + (nativeNextAudioTime > now ? 0.005 : 0.02)
        );

        nativeNextAudioTime = startAt + buffer.duration;
        nativeOutputSources.add(source);

        source.onended = function () {
            nativeOutputSources.delete(source);
            try { source.disconnect(); } catch (_) {}
            if (nativeOutputSources.size === 0) {
                if (typeof window.finishSpeakingTurn === "function") {
                    try { window.finishSpeakingTurn(); } catch (_) {}
                }
                if (nativeLiveActive) {
                    setNativeLiveStatus(
                        "LISTENING (GEMINI LIVE)",
                        "Native Gemini Live active · speak naturally"
                    );
                }
            }
        };

        source.start(startAt);

        if (typeof window.setAvatarSignal === "function") {
            try { window.setAvatarSignal("SPEAKING"); } catch (_) {}
        }
        if (nativeLiveActive) {
            setNativeLiveStatus(
                "SPEAKING (GEMINI LIVE)",
                "Native Gemini Live audio · interrupt anytime"
            );
        }
    }

    function mergeTranscript(previous, incoming) {
        var next = String(incoming || "").replace(/\s+/g, " ").trim();
        var prev = String(previous || "").replace(/\s+/g, " ").trim();
        if (!next) return prev;
        if (!prev) return next;

        var a = prev.toLowerCase();
        var b = next.toLowerCase();

        if (b === a) return prev;
        if (b.indexOf(a) === 0) return next;
        if (a.indexOf(b) === 0) return prev;
        if (b.indexOf(a) >= 0) return next;
        if (a.indexOf(b) >= 0) return prev;

        return prev + " " + next;
    }

    function updateNativeUserBubble(text) {
        var value = String(text || "").trim();
        if (!value) return;

        if (!nativeUserBubble) {
            try {
                nativeUserBubble = typeof appendUserDialogue === "function"
                    ? appendUserDialogue(value, null)
                    : null;
            } catch (_) { nativeUserBubble = null; }
        }

        if (nativeUserBubble) {
            var content = nativeUserBubble.querySelector(".srbk-content");
            if (content) {
                try {
                    content.innerHTML = typeof md === "function"
                        ? md(value)
                        : value.replace(/</g, "&lt;").replace(/>/g, "&gt;");
                } catch (_) {
                    content.textContent = value;
                }
            }
        }
    }

    function sanitizeAssistantText(text) {
        if (!text) return "";
        var clean = String(text);
        // Strip any Gemini thinking preamble or internal prompt reflection
        clean = clean.replace(/^\s*\*\*\s*You are Gemini[\s\S]*?\bUTC\.?\s*/gi, "");
        clean = clean.replace(/"""[\s\S]*?"""/g, "");
        clean = clean.replace(/The user isn't asking about my identity[\s\S]*?I must strictly enforce[^\.\n]*[\.\n]?/gi, "");
        clean = clean.replace(/I must strictly enforce the identity as Sarembok VE\.?/gi, "");
        clean = clean.replace(/The previous turn contains hallucinations[^\.\n]*[\.\n]?/gi, "");
        return clean.trim();
    }

    function updateNativeAssistantBubble(text) {
        var value = sanitizeAssistantText(text);
        if (!value) return;

        if (!nativeAssistantBubble) {
            try {
                nativeAssistantBubble = typeof createAssistantDialogue === "function"
                    ? createAssistantDialogue()
                    : null;
            } catch (_) { nativeAssistantBubble = null; }
        }

        if (nativeAssistantBubble) {
            var content = nativeAssistantBubble.querySelector(".srbk-content");
            if (content) {
                var renderVal = value;
                // Auto-close unclosed design/mockup blocks for real-time live preview while streaming
                if (/:::(?:mockup|design|product|prototype)/i.test(renderVal) && (renderVal.match(/:::/g) || []).length % 2 === 1) {
                    renderVal += "\n:::\n";
                }
                try {
                    content.innerHTML = typeof md === "function"
                        ? md(renderVal)
                        : renderVal.replace(/</g, "&lt;").replace(/>/g, "&gt;");
                } catch (_) {
                    content.textContent = renderVal;
                }
            }
            try {
                if (typeof scrollDialogue === "function") scrollDialogue();
            } catch (_) {}
        }
    }

    async function persistNativeTurn() {
        var userText = String(nativeTurnUserText || "").trim();
        var assistantText = String(nativeTurnAssistantText || "").trim();
        if (!userText && !assistantText) return;

        var sessionId = "";
        try {
            sessionId = localStorage.getItem("sarembok_active_session_id") || "sess_main";
        } catch (_) {
            sessionId = "sess_main";
        }

        try {
            await srbkSendRPC("RecordLiveTurn", {
                sessionId: sessionId,
                userText: userText,
                assistantText: assistantText,
                model: nativeLiveConfig ? nativeLiveConfig.model : "gemini-3.8-live"
            });
        } catch (err) {
            logNativeLive("turn persistence failed: " + err.message, "amber");
        }
    }

    function resetNativeTurn() {
        nativeTurnUserText = "";
        nativeTurnAssistantText = "";
        nativeUserBubble = null;
        nativeAssistantBubble = null;
    }

    function buildInitialHistoryContent() {
        if (!nativeHistory.length) return null;

        var turns = [];
        nativeHistory.slice(-8).forEach(function (item) {
            if (item.user) {
                turns.push({
                    role: "user",
                    parts: [{ text: item.user }]
                });
            }
            if (item.assistant) {
                turns.push({
                    role: "model",
                    parts: [{ text: item.assistant }]
                });
            }
        });

        if (!turns.length) return null;

        return {
            clientContent: {
                turns: turns,
                turnComplete: true
            }
        };
    }

    function sendNativeClientJson(payload) {
        if (
            !nativeLiveSocket ||
            nativeLiveSocket.readyState !== WebSocket.OPEN
        ) {
            return false;
        }
        nativeLiveSocket.send(JSON.stringify(payload));
        return true;
    }

    function isNativeLiveActive() {
        return Boolean(nativeLiveActive && (nativeLiveSocket && (nativeLiveSocket.readyState === WebSocket.OPEN || nativeLiveSocket.readyState === WebSocket.CONNECTING)));
    }

    function populateHistoryFromDialogue() {
        if (nativeHistory.length > 0) return;
        try {
            var dialogueContainer = document.getElementById("dialogue-history");
            if (!dialogueContainer) return;
            var bubbles = dialogueContainer.querySelectorAll(".srbk-bubble");
            var currentPair = {};
            for (var i = 0; i < bubbles.length; i++) {
                var b = bubbles[i];
                var content = b.querySelector(".srbk-content");
                var text = content ? content.textContent.trim() : "";
                if (!text || text === "Computing..." || text.startsWith("Execution notice:")) continue;
                if (b.classList.contains("user")) {
                    if (currentPair.user && currentPair.assistant) {
                        nativeHistory.push(currentPair);
                        currentPair = {};
                    }
                    currentPair.user = text;
                } else if (b.classList.contains("assistant")) {
                    if (currentPair.user) {
                        currentPair.assistant = text;
                        nativeHistory.push(currentPair);
                        currentPair = {};
                    }
                }
            }
            if (currentPair.user && currentPair.assistant) {
                nativeHistory.push(currentPair);
            }
            if (nativeHistory.length > 8) {
                nativeHistory = nativeHistory.slice(-8);
            }
        } catch (e) {
            console.warn("[LiveVoice] Error loading initial dialogue history:", e);
        }
    }

    async function sendNativeLiveText(text, attachments, imageFrame, options) {
        var rawText = String(text || "").trim();
        var opts = options && typeof options === "object" ? options : {};
        var isNarrationOnly = Boolean(opts.narrationOnly);
        if (!rawText && (!attachments || !attachments.length) && !imageFrame) return false;
        if (!nativeLiveActive) return false;
        if (nativeLiveSocket && nativeLiveSocket.readyState === WebSocket.CONNECTING) {
            for (var waitIter = 0; waitIter < 30; waitIter++) {
                await new Promise(function (r) { setTimeout(r, 100); });
                if (nativeLiveSocket && nativeLiveSocket.readyState === WebSocket.OPEN) break;
            }
        }
        if (!nativeLiveSocket || nativeLiveSocket.readyState !== WebSocket.OPEN) return false;
        clearNativeOutputAudio();
        resetNativeTurn();
        nativeTurnUserText = rawText;
        if (!isNarrationOnly) {
            try { if (typeof appendUserDialogue === "function") nativeUserBubble = appendUserDialogue(rawText, imageFrame, attachments); } catch (_) {}
            try { if (typeof createAssistantDialogue === "function") nativeAssistantBubble = createAssistantDialogue(); } catch (_) {}
        }
        var fileContext = "";
        if (Array.isArray(attachments)) attachments.forEach(function(att) {
            if (att && att.content && !String(att.content).startsWith("data:image")) {
                fileContext += "[ATTACHED FILE: " + (att.filename || att.name || "file") + "]\n" + att.content + "\n[END ATTACHED FILE]\n\n";
            }
        });
        var fullText = (fileContext + rawText).trim();
        var spokenText = isNarrationOnly
            ? "Please read aloud this response verbatim with natural speech inflection and clear pronunciation:\n" + rawText
            : rawText;
        var parts = [];
        if (fullText) parts.push({text: isNarrationOnly ? "Please read aloud this response verbatim with natural speech inflection and clear pronunciation:\n" + fullText : fullText});
        if (imageFrame) {
            var cleanBase64 = String(imageFrame).replace(/^data:image\/[a-z]+;base64,/, "");
            if (cleanBase64) parts.push({inlineData:{mimeType:"image/jpeg",data:cleanBase64}});
        }
        setNativeLiveStatus("WORKING (GEMINI LIVE)", "Generating Live voice response...");
        var sent;
        if (!attachments?.length && !imageFrame && fullText) {
            sent = sendNativeClientJson({realtimeInput:{text:spokenText}});
        } else {
            sent = sendNativeClientJson({clientContent:{turns:[{role:"user",parts:parts}],turnComplete:true}});
        }
        if (!sent) return false;
        detectAndTriggerLiveMediaIntent(rawText);
        return true;
    }

    var lastLiveMediaTrigger = "";
    var lastLiveMediaTriggerTime = 0;

    function detectAndTriggerLiveMediaIntent(rawText) {
        if (!rawText) return;
        var text = String(rawText).trim();
        if (text.length < 4) return;

        // Check for pop out commands
        if (/\b(?:pop(?:\s+it)?\s+out|popout|float(?:\s+the)?\s+video|picture\s+in\s+picture|pip)\b/i.test(text)) {
            var now = Date.now();
            if (now - lastLiveMediaTriggerTime > 2000) {
                lastLiveMediaTriggerTime = now;
                console.log("[LiveVoice] Spoken intent: pop out video");
                var popTarget = lastLiveMediaTrigger;
                if (window.lastActiveInlineMedia && (window.lastActiveInlineMedia.ytId || window.lastActiveInlineMedia.raw)) {
                    popTarget = window.lastActiveInlineMedia.ytId || window.lastActiveInlineMedia.raw;
                }
                if (typeof window.popOutFloatingVideo === "function") {
                    window.popOutFloatingVideo(popTarget || "video", popTarget || "Video");
                }
            }
            return;
        }

        // Check for stop media commands
        if (/\b(?:stop|close|dismiss|turn off)\s+(?:the\s+)?(?:video|pip|media|stream|music|song|player)\b/i.test(text)) {
            var now = Date.now();
            if (now - lastLiveMediaTriggerTime > 2500) {
                lastLiveMediaTriggerTime = now;
                console.log("[LiveVoice] Spoken intent: stop media");
                if (typeof window.closeFloatingPip === "function") {
                    window.closeFloatingPip();
                }
            }
            return;
        }

        // Match phrases like:
        // "play bbc news"
        // "play a glorilla video"
        // "play glorilla"
        // "play some lofi"
        // "watch a video about quantum computing"
        var match = text.match(/(?:^|\b)(?:please\s+)?(?:can you\s+)?(?:could you\s+)?(?:play|stream|watch|put on)\s+(?:a\s+|the\s+|some\s+)?(?:video\s+(?:of|for|about)\s+|song\s+(?:of|for|by)\s+|music\s+(?:by|from)\s+)?([^,.;?!]+)/i);
        if (!match || !match[1]) return;

        var candidate = match[1].replace(/\b(?:video|song|track|audio|on youtube|in video|please|for me|now)\b/gi, "").trim();
        if (!candidate || candidate.length < 2) return;
        if (/^(?:chess|a game|games|role|roles|dumb|dead|around|along|with|fair|nice|hard|tag)$/i.test(candidate)) return;

        var now = Date.now();
        if (candidate.toLowerCase() === lastLiveMediaTrigger.toLowerCase() && (now - lastLiveMediaTriggerTime < 8000)) {
            return;
        }

        lastLiveMediaTrigger = candidate;
        lastLiveMediaTriggerTime = now;
        console.log("[LiveVoice] Spoken media playback intent recognized (inline):", candidate);
        // Play INLINE in the conversation stream by default
        if (typeof window.playVideoInline === "function") {
            try {
                window.playVideoInline(candidate, candidate);
            } catch (err) {
                console.warn("[LiveVoice] playVideoInline invocation failed:", err);
            }
        }
    }

    async function executeNativeToolCall(functionCalls) {
        if (!Array.isArray(functionCalls) || !functionCalls.length) return;

        var responses = [];

        for (var i = 0; i < functionCalls.length; i++) {
            var call = functionCalls[i] || {};
            var name = String(call.name || "").trim();
            var rpcMethod = LIVE_TOOLS[name];
            var args = call.args || call.arguments || {};
            var result;

            if (name === "stop_media") {
                try {
                    if (typeof window.closeFloatingPip === "function") {
                        window.closeFloatingPip();
                    }
                    result = {
                        status: "stopped",
                        message: "Video playback stopped and floating picture-in-picture player closed."
                    };
                } catch (err) {
                    result = { error: String(err.message || err) };
                }
            } else if (name === "popout_media" || name === "pop_out_media") {
                var popQuery = String(args.query || lastLiveMediaTrigger || "").trim();
                if (window.lastActiveInlineMedia && (window.lastActiveInlineMedia.ytId || window.lastActiveInlineMedia.raw)) {
                    popQuery = window.lastActiveInlineMedia.ytId || window.lastActiveInlineMedia.raw;
                }
                if (typeof window.popOutFloatingVideo === "function") {
                    try {
                        window.popOutFloatingVideo(popQuery, popQuery);
                    } catch (e) {
                        console.warn("[LiveVoice] popOutFloatingVideo invocation failed:", e);
                    }
                }
                result = {
                    status: "popped_out",
                    message: "The video has popped out into the resizable floating player sitting on top of all windows."
                };
            } else if (name === "play_media") {
                var mediaQuery = String(args.query || args.topic || "").trim();
                var mediaType = String(args.media_type || "video").trim();
                lastLiveMediaTrigger = mediaQuery;
                lastLiveMediaTriggerTime = Date.now();
                // Play INLINE in the conversation bubble by default
                if (typeof window.playVideoInline === "function") {
                    try {
                        window.playVideoInline(mediaQuery, mediaQuery);
                    } catch (e) {
                        console.warn("[LiveVoice] playVideoInline invocation failed:", e);
                    }
                }
                try {
                    result = await srbkSendRPC("ResolveMediaStream", { query: mediaQuery, media_type: mediaType });
                    if (!result || !result.url) {
                        result = {
                            status: "playing_inline",
                            query: mediaQuery,
                            player: "inline_chat",
                            message: "Media is now playing inline in the conversation chat. The user can watch inline or click 'Pop Out' to float it over all windows."
                        };
                    } else {
                        result.status = "playing_inline";
                        result.player = "inline_chat";
                        result.message = "Media is now playing inline in the conversation chat. The user can watch inline or click 'Pop Out' to float it over all windows.";
                    }
                } catch (_) {
                    result = {
                        status: "playing_inline",
                        query: mediaQuery,
                        player: "inline_chat",
                        message: "Media is now playing inline in the conversation chat."
                    };
                }
            } else if (name === "generate_flyer") {
                var flyerTitle = String(args.title || "Promotional Flyer").trim();
                var flyerHtml = String(args.html || "").trim();
                var flyerSummary = String(args.summary || ("Here is the visual promotional flyer for " + flyerTitle + ".")).trim();

                var mockupBlock = "\n\n:::mockup " + flyerTitle + "\n```html\n" + flyerHtml + "\n```\n:::\n";
                nativeTurnAssistantText = (nativeTurnAssistantText ? nativeTurnAssistantText + "\n" : "") + mockupBlock;
                updateNativeAssistantBubble(nativeTurnAssistantText);

                result = {
                    status: "rendered",
                    title: flyerTitle,
                    summary: flyerSummary,
                    message: "The visual flyer for " + flyerTitle + " has been rendered interactively on screen in the design studio."
                };
            } else if (!rpcMethod) {
                result = { error: "unregistered_live_tool", tool: name };
            } else {
                try {
                    var rpcParams = {};
                    Object.keys(args || {}).forEach(function (key) {
                        rpcParams[key] = args[key];
                    });

                    if (name === "search_memory") {
                        rpcParams.limit = Math.min(
                            20,
                            Math.max(1, Number(rpcParams.limit || 10))
                        );
                    }

                    result = await srbkSendRPC(rpcMethod, rpcParams);
                } catch (err) {
                    result = { error: String(err.message || err) };
                }
            }

            var responseBody = { result: result };
            if (nativeLiveMode !== "agentic") {
                responseBody.scheduling = "WHEN_IDLE";
            }

            responses.push({
                id: String(call.id || ""),
                name: name,
                response: responseBody
            });
        }

        if (responses.length) {
            sendNativeClientJson({
                toolResponse: {
                    functionResponses: responses
                }
            });
        }
    }

    function handleNativeServerMessage(message) {
        var serverContent = message.serverContent || {};
        var setupComplete = message.setupComplete;
        var toolCall = message.toolCall || {};
        var toolCancellation = message.toolCallCancellation;
        var goAway = message.goAway;

        if (setupComplete) {
            nativeSetupComplete = true;
            // DO NOT inject history with turnComplete: true!
            // Injecting turnComplete: true causes Gemini Live to generate speech immediately upon
            // connecting without any user input. Session must remain in silence until user speaks.
            setNativeLiveStatus(
                "LISTENING (GEMINI LIVE)",
                nativeLiveMediaStream
                    ? "Native audio-to-audio conversation · speak or type naturally"
                    : "Native Gemini Live audio active · type message to converse"
            );
            logNativeLive("native audio session established", "emerald");
            return;
        }

        var interactionStatus =
            message.interactionStatus ||
            serverContent.interactionStatus ||
            "";

        if (interactionStatus === "IN_PROGRESS") {
            setNativeLiveStatus(
                "WORKING (GEMINI LIVE)",
                "Sarembok is working in the background"
            );
        } else if (interactionStatus === "IDLE") {
            setNativeLiveStatus(
                "LISTENING (GEMINI LIVE)",
                "Native audio-to-audio conversation · speak naturally"
            );
        }

        if (toolCall.functionCalls && toolCall.functionCalls.length) {
            setNativeLiveStatus(
                "WORKING (GEMINI LIVE)",
                "Sarembok is checking the live runtime"
            );
            void executeNativeToolCall(toolCall.functionCalls);
        }

        if (toolCancellation) {
            logNativeLive("live tool call cancelled", "amber");
        }

        if (serverContent.inputTranscription) {
            var inputText = serverContent.inputTranscription.text || "";
            nativeTurnUserText = mergeTranscript(
                nativeTurnUserText,
                inputText
            );
            updateNativeUserBubble(nativeTurnUserText);
            setNativeLiveStatus(
                "HEARING YOU",
                nativeTurnUserText || "Listening"
            );
            detectAndTriggerLiveMediaIntent(nativeTurnUserText);
        }

        if (serverContent.interimInputTranscription) {
            var interim = serverContent.interimInputTranscription.text || "";
            setNativeLiveStatus(
                "HEARING YOU",
                interim || nativeTurnUserText || "Listening"
            );
        }

        if (serverContent.outputTranscription) {
            var outputText = sanitizeAssistantText(serverContent.outputTranscription.text || "");
            if (outputText) {
                nativeTurnAssistantText = mergeTranscript(
                    nativeTurnAssistantText,
                    outputText
                );
                updateNativeAssistantBubble(nativeTurnAssistantText);
            }
        }

        var modelTurn = serverContent.modelTurn || {};
        var parts = modelTurn.parts || [];
        for (var i = 0; i < parts.length; i++) {
            var part = parts[i] || {};
            // Strict filter: internal reasoning / chain-of-thought parts must NEVER be shown or spoken
            if (part.thought) continue;

            var inlineData = part.inlineData || part.inline_data;
            if (inlineData && inlineData.data) {
                try {
                    var audioBytes = bytesFromBase64(inlineData.data);
                    var audioNow = performance.now();

                    if (!window.__sarembokFirstAudioTime) {
                        window.__sarembokFirstAudioTime = audioNow;
                        console.log(
                            "[GEMINI-LIVE AUDIO] FIRST AUDIO",
                            audioNow.toFixed(1),
                            "bytes=" + audioBytes.byteLength
                        );
                    } else {
                        var delta =
                            audioNow - window.__sarembokLastAudioTime;

                        console.log(
                            "[GEMINI-LIVE AUDIO] CHUNK",
                            audioNow.toFixed(1),
                            "delta=" + delta.toFixed(1) + "ms",
                            "bytes=" + audioBytes.byteLength
                        );
                    }

                    window.__sarembokLastAudioTime = audioNow;

                    queueNativeOutputPcm(audioBytes);
                } catch (err) {
                    logNativeLive("audio decode error: " + err.message, "amber");
                }
            }
            if (part.text && !serverContent.outputTranscription) {
                var cleanPart = sanitizeAssistantText(part.text);
                if (cleanPart) {
                    nativeTurnAssistantText = mergeTranscript(
                        nativeTurnAssistantText,
                        cleanPart
                    );
                    updateNativeAssistantBubble(nativeTurnAssistantText);
                }
            }
        }

        if (serverContent.interrupted) {
            clearNativeOutputAudio();
            resetNativeTurn();
            setNativeLiveStatus(
                "LISTENING (INTERRUPTED)",
                "Listening · the assistant was interrupted"
            );
            try {
                if (typeof setAvatarSignal === "function") setAvatarSignal("LISTENING");
            } catch (_) {}
        }

        if (serverContent.turnComplete) {
            // Standard Live uses turnComplete as the idle boundary. Extended
            // Thinking can emit turnComplete while interactionStatus remains
            // IN_PROGRESS because background reasoning/tool work continues.
            var extendedStillWorking =
                nativeLiveMode === "agentic" &&
                interactionStatus &&
                interactionStatus !== "IDLE";

            if (!extendedStillWorking) {
                var completedUser = nativeTurnUserText;
                var completedAssistant = nativeTurnAssistantText;
                detectAndTriggerLiveMediaIntent(completedUser);

                if (completedUser || completedAssistant) {
                    nativeHistory.push({
                        user: completedUser,
                        assistant: completedAssistant
                    });
                    if (nativeHistory.length > 8) nativeHistory.shift();
                }

                void persistNativeTurn();

                resetNativeTurn();
                setNativeLiveStatus(
                    "LISTENING (GEMINI LIVE)",
                    "Native audio-to-audio conversation · speak naturally"
                );
                try {
                    if (typeof setAudioDucking === "function") setAudioDucking(false);
                } catch (_) {}
            }
        }

        if (goAway && nativeLiveActive) {
            logNativeLive(
                "Gemini Live requested session rotation",
                "amber"
            );
        }
    }

    function makeInputWorkletSource() {
        return (
            "class SarembokLiveInput extends AudioWorkletProcessor {" +
            "constructor(){" +
                "super();" +
                "this.buffer=[];" +
                "this.phase=0;" +
                "this.ratio=sampleRate/16000;" +
                "this.out=[];" +
                "this.speechSeen=false;" +
                "this.silenceMs=0;" +
                "this.vadThreshold=0.015;" +
                "this.consecutiveSpeechFrames=0;" +
            "}" +
            "process(inputs,outputs,parameters){" +
                "const input=inputs[0]&&inputs[0][0];" +
                "if(!input||!input.length)return true;" +
                "for(let i=0;i<input.length;i++)this.buffer.push(input[i]);" +
                "while(this.phase+1<this.buffer.length){" +
                    "const i=Math.floor(this.phase),f=this.phase-i;" +
                    "const a=this.buffer[i]||0,b=this.buffer[i+1]||a;" +
                    "this.out.push(a+(b-a)*f);this.phase+=this.ratio;" +
                "}" +
                "const consume=Math.floor(this.phase);" +
                "if(consume>0){this.buffer=this.buffer.slice(consume);this.phase-=consume;}" +
                "while(this.out.length>=640){" +
                    "const chunk=this.out.slice(0,640);" +
                    "this.out=this.out.slice(640);" +
                    "const pcm=new Int16Array(640);" +
                    "let sum=0;" +
                    "for(let n=0;n<640;n++){" +
                        "let v=Math.max(-1,Math.min(1,chunk[n]));" +
                        "pcm[n]=v<0?v*32768:v*32767;" +
                        "sum+=v*v;" +
                    "}" +
                    "const rms=Math.sqrt(sum/640);" +
                    "const speechEnergy=rms>=this.vadThreshold;" +
                    "if(speechEnergy){this.consecutiveSpeechFrames++;}else{this.consecutiveSpeechFrames=0;}" +
                    "const speech=speechEnergy&&(this.consecutiveSpeechFrames>=2||this.speechSeen);" +
                    "if(speech){" +
                        "this.speechSeen=true;" +
                        "this.silenceMs=0;" +
                    "}else if(this.speechSeen){" +
                        "this.silenceMs+=40;" +
                    "}" +
                    "const shouldSend=speech||(this.speechSeen&&this.silenceMs<=1200);" +
                    "this.port.postMessage({" +
                        "pcm:shouldSend?pcm.buffer:null," +
                        "speech:speech," +
                        "rms:rms" +
                    "},shouldSend?[pcm.buffer]:[]);" +
                    "if(this.speechSeen&&this.silenceMs>=1600){" +
                        "this.speechSeen=false;" +
                        "this.silenceMs=0;" +
                    "}" +
                "}" +
                "return true;" +
            "}" +
            "}" +
            "registerProcessor('sarembok-live-input',SarembokLiveInput);"
        );
    }

    async function ensureAudioContexts() {
        if (!nativeOutputContext) {
            nativeOutputContext = new AudioContext({
                latencyHint: "interactive"
            });
        }
        if (nativeOutputContext.state !== "running") {
            await nativeOutputContext.resume();
        }

        if (nativeLiveMediaStream) {
            if (!nativeInputContext) {
                nativeInputContext = new AudioContext({
                    latencyHint: "interactive"
                });
            }
            if (nativeInputContext.state !== "running") {
                await nativeInputContext.resume();
            }

            if (!nativeWorkletUrl) {
                var blob = new Blob(
                    [makeInputWorkletSource()],
                    { type: "application/javascript" }
                );
                nativeWorkletUrl = URL.createObjectURL(blob);
            }

            if (!nativeWorkletLoaded) {
                await nativeInputContext.audioWorklet.addModule(nativeWorkletUrl);
                nativeWorkletLoaded = true;
            }
        }
    }

    async function connectNativeGemini(tokenData) {
        var connectionGeneration = ++nativeConnectionGeneration;
        if (nativeLiveSocket) {
            try {
                nativeLiveSocket.onopen = null;
                nativeLiveSocket.onmessage = null;
                nativeLiveSocket.onerror = null;
                nativeLiveSocket.onclose = null;
                nativeLiveSocket.close();
            } catch (_) {}
            nativeLiveSocket = null;
        }
        nativeSetupComplete = false;
        clearNativeOutputAudio();

        var url = LIVE_WS_BASE + "?access_token=" +
            encodeURIComponent(tokenData.token);

        var socket = new WebSocket(url);
        nativeLiveSocket = socket;
        socket.binaryType = "arraybuffer";

        socket.onopen = function () {
            if (socket !== nativeLiveSocket || connectionGeneration !== nativeConnectionGeneration || nativeLiveStopping) return;
            var setup = tokenData.setup || {};
            var generationConfig = Object.assign(
                {},
                setup.generationConfig || {}
            );
            if (setup.thinkingConfig) {
                generationConfig.thinkingConfig = setup.thinkingConfig;
            }

            var setupMessage = {
                setup: {
                    model: "models/" + tokenData.model,
                    generationConfig: generationConfig,
                    systemInstruction: setup.systemInstruction,
                    tools: setup.tools,
                    realtimeInputConfig: setup.realtimeInputConfig,
                    inputAudioTranscription: setup.inputAudioTranscription,
                    outputAudioTranscription: setup.outputAudioTranscription,
                    sessionResumption: setup.sessionResumption
                }
            };
            if (setup.historyConfig) {
                setupMessage.setup.historyConfig = setup.historyConfig;
            }

            socket.send(JSON.stringify(setupMessage));
        };

        socket.onmessage = async function (event) {
            if (socket !== nativeLiveSocket || connectionGeneration !== nativeConnectionGeneration) return;
            try {
                var text = null;

                if (typeof event.data === "string") {
                    text = event.data;
                } else if (event.data instanceof ArrayBuffer) {
                    text = new TextDecoder("utf-8").decode(
                        new Uint8Array(event.data)
                    );
                } else if (event.data instanceof Blob) {
                    text = await event.data.text();
                }

                if (!text) return;

                handleNativeServerMessage(JSON.parse(text));
            } catch (err) {
                logNativeLive(
                    "protocol message parse error: " + err.message,
                    "amber"
                );
            }
        };

        socket.onerror = function () {
            if (socket !== nativeLiveSocket || connectionGeneration !== nativeConnectionGeneration) return;
            setNativeLiveStatus(
                "LIVE CONNECTION ERROR",
                "Gemini Live connection failed"
            );
        };

        socket.onclose = function (event) {
            if (socket !== nativeLiveSocket || connectionGeneration !== nativeConnectionGeneration || nativeLiveStopping) return;
            logNativeLive("Gemini Live socket closed code=" + String(event && event.code || "") + " reason=" + String(event && event.reason || ""), "amber");

            nativeSetupComplete = false;
            if (nativeLiveActive && !nativeLiveReconnecting && !nativeReconnectTimer) {
                nativeReconnectTimer = setTimeout(function () {
                    nativeReconnectTimer = null;
                    void restartNativeLiveSession();
                }, 750);
            }
        };
    }

    async function startNativeLive(mode) {
        if (nativeLiveActive) return;
        if (nativeStartPromise) return nativeStartPromise;

        nativeStartPromise = (async function () {
            nativeLiveMode = mode === "agentic" ? "agentic" : "conversational";
            nativeLiveStopping = false;

            try {
                // Native Gemini Live owns the microphone and speaker. Stop any
                // lingering speech turn before taking control.
                try {
                    if (typeof interruptSpeech === "function") interruptSpeech();
                } catch (_) {}

                nativeLiveActive = true;
                window.nativeLiveActive = true;
                window.liveConversationActive = true;
                window.voiceEnabled = true;
                try {
                    if (typeof voiceEnabled !== "undefined") voiceEnabled = true;
                    var voiceLabel = document.getElementById("hud-voice-label");
                    if (voiceLabel) voiceLabel.textContent = "VOICE: ON";
                    var voiceBtn = document.getElementById("hud-voice-toggle");
                    if (voiceBtn) voiceBtn.classList.remove("muted");
                    var voiceChip = document.getElementById("dialogue-voice-toggle-chip");
                    if (voiceChip) voiceChip.classList.remove("muted");
                    var voiceChipText = document.getElementById("dialogue-voice-chip-text");
                    if (voiceChipText) voiceChipText.textContent = "VOICE: ON";
                    var inp = document.getElementById("directive-input");
                    if (inp) {
                        inp.classList.add("live-active");
                        if (!inp.dataset.normalPlaceholder) inp.dataset.normalPlaceholder = inp.placeholder;
                        inp.placeholder = "Talk or type directive to Gemini Live (Unified Engine)...";
                    }
                } catch (_) {}
                setNativeLiveStatus(
                    "CONNECTING (GEMINI LIVE)",
                    "Opening native real-time audio channel…"
                );

                // Request microphone permission and wake the audio hardware while
                // the token request happens, minimizing perceived startup delay.
                // If microphone is unavailable or denied, operate gracefully in Text & Spoken Audio mode.
                var mediaPromise = (navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
                    ? navigator.mediaDevices.getUserMedia({
                        audio: {
                            channelCount: 1,
                            echoCancellation: true,
                            noiseSuppression: true,
                            autoGainControl: true
                        },
                        video: false
                    }).catch(function (micErr) {
                        console.warn("[LiveVoice] Microphone capture unavailable, operating in Text & Spoken Audio mode:", micErr);
                        return null;
                    })
                    : Promise.resolve(null);

                var tokenPromise = fetchLiveToken(nativeLiveMode);

                // Unlock/initialize the browser audio pipeline while this call still
                // originates from the user's gesture. Do not wait for the token
                // network round-trip before starting the audio contexts.
                nativeLiveMediaStream = await mediaPromise;
                await ensureAudioContexts();
                nativeLiveConfig = await tokenPromise;

                if (nativeOutputContext) nativeOutputContext.resume().catch(function () {});
                if (nativeInputContext) nativeInputContext.resume().catch(function () {});

                if (nativeInputWorklet) {
                    try { nativeInputWorklet.disconnect(); } catch (_) {}
                    nativeInputWorklet = null;
                }
                if (nativeMicSource) {
                    try { nativeMicSource.disconnect(); } catch (_) {}
                    nativeMicSource = null;
                }

                if (nativeLiveMediaStream && nativeInputContext) {
                    nativeMicSource = nativeInputContext.createMediaStreamSource(
                        nativeLiveMediaStream
                    );

                    nativeInputWorklet = new AudioWorkletNode(
                        nativeInputContext,
                        "sarembok-live-input",
                        { numberOfInputs: 1, numberOfOutputs: 1, channelCount: 1 }
                    );

                    nativeInputWorklet.port.onmessage = function (event) {
                        if (!nativeSetupComplete) return;
                        if (
                            !nativeLiveSocket ||
                            nativeLiveSocket.readyState !== WebSocket.OPEN
                        ) return;

                        var payload = event.data || {};

                        // Keystroke Noise Rejection: suppress mic streaming ONLY while keys are actively being typed
                        // to avoid keyboard clatter interrupting Gemini Live. Does NOT mute when input is merely focused.
                        var now = Date.now();
                        if (window.__lastDirectiveInputTime && (now - window.__lastDirectiveInputTime < 700)) {
                            return;
                        }

                        // Acoustic echo gating: when Sarembok is actively speaking audio,
                        // do not stream mic bleed back into Gemini Live unless user is deliberately interrupting.
                        if (nativeOutputSources.size > 0 && (payload.rms || 0) < 0.08) {
                            return;
                        }

                        var pcmBuffer = payload.pcm;
                        if (!pcmBuffer) return;

                        var bytes = new Uint8Array(pcmBuffer);
                        if (!bytes.length) return;

                        nativeLiveSocket.send(JSON.stringify({
                            realtimeInput: {
                                audio: {
                                    mimeType: "audio/pcm;rate=16000",
                                    data: base64FromBytes(bytes)
                                }
                            }
                        }));
                    };

                    nativeMicSource.connect(nativeInputWorklet);

                    var silentGain = nativeInputContext.createGain();
                    silentGain.gain.value = 0;
                    nativeInputWorklet.connect(silentGain);
                    silentGain.connect(nativeInputContext.destination);
                }

                clearNativeOutputAudio();
                await connectNativeGemini(nativeLiveConfig);

                try {
                    if (typeof window.pauseRecognitionForSpeech === "function") {
                        // Native Live owns the microphone. Prevent the legacy
                        // SpeechRecognition loop from competing for it.
                        window.pauseRecognitionForSpeech();
                    }
                } catch (_) {}

                setNativeLiveStatus(
                    "CONNECTING (GEMINI LIVE)",
                    "Native audio session negotiating…"
                );
            } catch (err) {
                nativeLiveActive = false;
                nativeLiveStopping = true;

                if (nativeLiveMediaStream) {
                    nativeLiveMediaStream.getTracks().forEach(function (track) {
                        try { track.stop(); } catch (_) {}
                    });
                }
                nativeLiveMediaStream = null;

                setNativeLiveStatus(
                    "LIVE VOICE UNAVAILABLE",
                    String(err.message || err)
                );
                logNativeLive("startup failed: " + String(err.message || err), "amber");
            } finally {
                nativeStartPromise = null;
            }
        })();

        return nativeStartPromise;
    }

    async function restartNativeLiveSession() {
        if (!nativeLiveActive) return;

        nativeLiveReconnecting = true;
        try {
            if (nativeLiveSocket) {
                try {
                    nativeLiveSocket.close(1000, "session-refresh");
                } catch (_) {}
            }

            clearNativeOutputAudio();

            var tokenData = await fetchLiveToken(nativeLiveMode);
            nativeLiveConfig = tokenData;
            await connectNativeGemini(tokenData);

            setNativeLiveStatus(
                "CONNECTING (GEMINI LIVE)",
                "Refreshing native audio session…"
            );
        } catch (err) {
            nativeLiveReconnecting = false;
            setNativeLiveStatus(
                "LIVE RECONNECT FAILED",
                "The live session could not be refreshed: " + String(err.message || err)
            );
        } finally {
            nativeLiveReconnecting = false;
        }
    }

    async function stopNativeLive() {
        nativeLiveStopping = true;
        nativeLiveActive = false;
        window.nativeLiveActive = false;
        window.liveConversationActive = false;
        try {
            var inp = document.getElementById("directive-input");
            if (inp) {
                inp.classList.remove("live-active");
                if (inp.dataset.normalPlaceholder) {
                    inp.placeholder = inp.dataset.normalPlaceholder;
                }
            }
        } catch (_) {}

        if (nativeReconnectTimer) {
            clearTimeout(nativeReconnectTimer);
            nativeReconnectTimer = null;
        }

        if (nativeLiveSocket) {
            try {
                if (nativeLiveSocket.readyState === WebSocket.OPEN) {
                    nativeLiveSocket.send(JSON.stringify({
                        realtimeInput: { audioStreamEnd: true }
                    }));
                }
            } catch (_) {}
            try {
                nativeLiveSocket.onopen = null;
                nativeLiveSocket.onmessage = null;
                nativeLiveSocket.onerror = null;
                nativeLiveSocket.onclose = null;
                nativeLiveSocket.close(1000, "user-stop");
            } catch (_) {}
            nativeLiveSocket = null;
        }

        clearNativeOutputAudio();

        if (nativeInputWorklet) {
            try { nativeInputWorklet.disconnect(); } catch (_) {}
            nativeInputWorklet = null;
        }
        if (nativeMicSource) {
            try { nativeMicSource.disconnect(); } catch (_) {}
            nativeMicSource = null;
        }

        if (nativeLiveMediaStream) {
            nativeLiveMediaStream.getTracks().forEach(function (track) {
                try { track.stop(); } catch (_) {}
            });
            nativeLiveMediaStream = null;
        }

        if (nativeInputContext && nativeInputContext.state === "running") {
            try { await nativeInputContext.suspend(); } catch (_) {}
        }

        setNativeLiveStatus(
            "LIVE VOICE",
            "Native Gemini Live is ready"
        );
        try {
            if (typeof setAudioDucking === "function") setAudioDucking(false);
            if (typeof setAvatarSignal === "function") setAvatarSignal("IDLE");
        } catch (_) {}
        resetNativeTurn();
    }

    function startSarembokLiveVoice(mode) {
        var selectedMode = mode === "agentic" ? "agentic" : "conversational";
        if (nativeLiveActive) {
            return stopNativeLive();
        }

        try {
            if (typeof switchTab === "function") switchTab("dialogue");
        } catch (_) {}

        return startNativeLive(selectedMode);
    }

    async function toggleSarembokLiveMode() {
        var nextMode =
            nativeLiveMode === "agentic" ? "conversational" : "agentic";
        nativeLiveMode = nextMode;

        var modeButton = document.getElementById("live-mode-toggle-btn");
        if (modeButton) {
            modeButton.textContent =
                nextMode === "agentic" ? "LIVE MODE: DEEP" : "LIVE MODE: FAST";
        }

        if (nativeLiveActive) {
            await stopNativeLive();
            return startNativeLive(nextMode);
        }

        setNativeLiveStatus(
            "LIVE VOICE",
            nextMode === "agentic"
                ? "Deep agentic Live selected · background reasoning"
                : "Fast conversational Live selected · lowest-latency dialogue"
        );
    }

    function toggleNativeLiveConversation() {
        if (nativeLiveActive) return stopNativeLive();
        try {
            if (typeof switchTab === "function") switchTab("dialogue");
        } catch (_) {}
        return startNativeLive(nativeLiveMode);
    }

    function handleNativeOrbClick() {
        if (!nativeLiveActive) {
            return startNativeLive(nativeLiveMode);
        }

        // Gemini Live VAD detects human speech and interrupts model audio. The
        // orb provides an explicit local stop/clear affordance as well.
        clearNativeOutputAudio();
        setNativeLiveStatus(
            "LISTENING (GEMINI LIVE)",
            "Listening for your next word"
        );
    }

    async function ensureNativeLiveSession(mode) {
        if (isNativeLiveActive()) return true;
        if (!nativeLiveActive) {
            await startNativeLive(mode || nativeLiveMode || "conversational");
        } else if (nativeStartPromise) {
            await nativeStartPromise;
        }
        for (var i = 0; i < 50; i++) {
            if (nativeLiveSocket && nativeLiveSocket.readyState === WebSocket.OPEN) return true;
            await new Promise(function (r) { setTimeout(r, 100); });
        }
        return Boolean(nativeLiveSocket && nativeLiveSocket.readyState === WebSocket.OPEN);
    }

    // Public API.
    window.startSarembokLiveVoice = startSarembokLiveVoice;
    window.startSarembokLiveAgent = function () {
        return startSarembokLiveVoice("agentic");
    };
    window.toggleNativeLiveConversation = toggleNativeLiveConversation;
    window.toggleSarembokLiveMode = toggleSarembokLiveMode;
    window.nativeLiveActive = false;
    window.isNativeLiveActive = isNativeLiveActive;
    window.ensureNativeLiveSession = ensureNativeLiveSession;
    window.sendNativeLiveText = sendNativeLiveText;
    window.clearNativeOutputAudio = clearNativeOutputAudio;

    // Public API entry points for unified Gemini Live audio.
    window.toggleLiveConversation = toggleNativeLiveConversation;
    window.handleOrbClick = handleNativeOrbClick;

    function initLiveVoiceControls() {
        var starter = document.querySelector(".simple-starter-card[onclick*='startSimpleVoice']");
        if (starter) starter.setAttribute("onclick", "startSarembokLiveVoice()");

        var mic = document.getElementById("dialogue-mic-btn");
        if (mic) {
            mic.setAttribute("onclick", "toggleLiveConversation()");
            mic.title = "Start native Gemini Live conversation";
        }

        var globalMic = document.getElementById("global-mic-btn");
        if (globalMic) {
            globalMic.setAttribute("onclick", "toggleLiveConversation()");
            globalMic.title = "Start native Gemini Live conversation";
        }

        var liveBtn = document.getElementById("hud-live-2way-btn");
        if (liveBtn) {
            liveBtn.setAttribute("onclick", "toggleLiveConversation()");
            var label = liveBtn.querySelector("span");
            if (label) label.textContent = "LIVE VOICE";
        }

        var liveConvBtn = document.getElementById("live-conv-btn");
        if (liveConvBtn) {
            liveConvBtn.setAttribute("onclick", "toggleLiveConversation()");
        }

        var orb = document.getElementById("live-conv-orb");
        if (orb) {
            orb.setAttribute("onclick", "handleOrbClick()");
        }
        var legacyWakeWord = document.getElementById("wake-word-toggle-btn");
        if (legacyWakeWord) legacyWakeWord.style.display = "none";
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initLiveVoiceControls);
    } else {
        initLiveVoiceControls();
    }

    window.addEventListener("pagehide", function () {
        try { void stopNativeLive(); } catch (_) {}
    });
})();