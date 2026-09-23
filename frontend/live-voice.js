(function () {
    "use strict";

    // Native Gemini Live voice replaces the legacy browser SpeechRecognition ->
    // SarembokChat -> Kokoro chain for the user-facing live conversation path.
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

    var LIVE_TOOLS = {
        get_runtime_info: "GetRuntimeInfo",
        get_provider_metrics: "GetProviderMetrics",
        list_workers: "ListWorkers",
        list_tasks: "ListTasks",
        search_memory: "SearchMemories"
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
        var startAt = Math.max(
            nativeNextAudioTime,
            now + (nativeNextAudioTime > now ? 0.005 : 0.02)
        );

        nativeNextAudioTime = startAt + buffer.duration;
        nativeOutputSources.add(source);

        source.onended = function () {
            nativeOutputSources.delete(source);
            try { source.disconnect(); } catch (_) {}
        };

        source.start(startAt);

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

    function updateNativeAssistantBubble(text) {
        var value = String(text || "").trim();
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
                try {
                    content.innerHTML = typeof md === "function"
                        ? md(value)
                        : value.replace(/</g, "&lt;").replace(/>/g, "&gt;");
                } catch (_) {
                    content.textContent = value;
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

    async function executeNativeToolCall(functionCalls) {
        if (!Array.isArray(functionCalls) || !functionCalls.length) return;

        var responses = [];

        for (var i = 0; i < functionCalls.length; i++) {
            var call = functionCalls[i] || {};
            var name = String(call.name || "").trim();
            var rpcMethod = LIVE_TOOLS[name];
            var args = call.args || call.arguments || {};
            var result;

            if (!rpcMethod) {
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
            var historyMessage = buildInitialHistoryContent();
            if (historyMessage) {
                sendNativeClientJson(historyMessage);
            }

            setNativeLiveStatus(
                "LISTENING (GEMINI LIVE)",
                "Native audio-to-audio conversation · speak naturally"
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
        }

        if (serverContent.interimInputTranscription) {
            var interim = serverContent.interimInputTranscription.text || "";
            setNativeLiveStatus(
                "HEARING YOU",
                interim || nativeTurnUserText || "Listening"
            );
        }

        if (serverContent.outputTranscription) {
            var outputText = serverContent.outputTranscription.text || "";
            nativeTurnAssistantText = mergeTranscript(
                nativeTurnAssistantText,
                outputText
            );
            updateNativeAssistantBubble(nativeTurnAssistantText);
        }

        var modelTurn = serverContent.modelTurn || {};
        var parts = modelTurn.parts || [];
        for (var i = 0; i < parts.length; i++) {
            var part = parts[i] || {};
            var inlineData = part.inlineData || part.inline_data;
            if (inlineData && inlineData.data) {
                try {
                    var audioBytes = bytesFromBase64(inlineData.data);
                    queueNativeOutputPcm(audioBytes);
                } catch (err) {
                    logNativeLive("audio decode error: " + err.message, "amber");
                }
            }
            if (part.text) {
                nativeTurnAssistantText = mergeTranscript(
                    nativeTurnAssistantText,
                    part.text
                );
                updateNativeAssistantBubble(nativeTurnAssistantText);
            }
        }

        if (serverContent.interrupted) {
            clearNativeOutputAudio();
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
            "constructor(){super();this.buffer=[];this.phase=0;this.ratio=sampleRate/16000;}" +
            "process(inputs,outputs,parameters){" +
            "const input=inputs[0]&&inputs[0][0];" +
            "if(!input||!input.length)return true;" +
            "for(let i=0;i<input.length;i++)this.buffer.push(input[i]);" +
            "const out=[];" +
            "while(this.phase+1<this.buffer.length){" +
            "const i=Math.floor(this.phase),f=this.phase-i;" +
            "const a=this.buffer[i]||0,b=this.buffer[i+1]||a;" +
            "out.push(a+(b-a)*f);this.phase+=this.ratio;}" +
            "const consume=Math.floor(this.phase);" +
            "if(consume>0){this.buffer=this.buffer.slice(consume);this.phase-=consume;}" +
            "if(out.length){" +
            "let cursor=0;" +
            "while(cursor+640<=out.length){" +
            "const pcm=new Int16Array(640);" +
            "for(let n=0;n<640;n++){" +
            "let v=Math.max(-1,Math.min(1,out[cursor+n]));" +
            "pcm[n]=v<0?v*32768:v*32767;}" +
            "this.port.postMessage(pcm.buffer,[pcm.buffer]);cursor+=640;}" +
            "}" +
            "return true;}" +
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

    async function connectNativeGemini(tokenData) {
        nativeSetupComplete = false;

        var url = LIVE_WS_BASE + "?access_token=" +
            encodeURIComponent(tokenData.token);

        nativeLiveSocket = new WebSocket(url);
        nativeLiveSocket.binaryType = "arraybuffer";

        nativeLiveSocket.onopen = function () {
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
                    sessionResumption: setup.sessionResumption,
                    historyConfig: setup.historyConfig
                }
            };

            nativeLiveSocket.send(JSON.stringify(setupMessage));
        };

        nativeLiveSocket.onmessage = function (event) {
            if (typeof event.data !== "string") return;
            try {
                handleNativeServerMessage(JSON.parse(event.data));
            } catch (err) {
                logNativeLive("protocol message parse error: " + err.message, "amber");
            }
        };

        nativeLiveSocket.onerror = function () {
            setNativeLiveStatus(
                "LIVE CONNECTION ERROR",
                "Gemini Live connection failed"
            );
        };

        nativeLiveSocket.onclose = function () {
            if (nativeLiveStopping) return;

            nativeSetupComplete = false;
            if (nativeLiveActive && !nativeReconnectTimer) {
                nativeReconnectTimer = setTimeout(function () {
                    nativeReconnectTimer = null;
                    void restartNativeLiveSession();
                }, 750);
            }
        };
    }

    async function startNativeInputCapture() {
        nativeLiveMediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            },
            video: false
        });

        await ensureAudioContexts();

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

            var pcm = new Uint8Array(event.data);
            if (!pcm.length) return;

            nativeLiveSocket.send(JSON.stringify({
                realtimeInput: {
                    audio: {
                        mimeType: "audio/pcm;rate=16000",
                        data: base64FromBytes(pcm)
                    }
                }
            }));
        };

        nativeMicSource.connect(nativeInputWorklet);

        // Keep the worklet alive without routing microphone audio to the speakers.
        var silentGain = nativeInputContext.createGain();
        silentGain.gain.value = 0;
        nativeInputWorklet.connect(silentGain);
        silentGain.connect(nativeInputContext.destination);
    }

    async function startNativeLive(mode) {
        if (nativeLiveActive) return;
        if (nativeStartPromise) return nativeStartPromise;

        nativeStartPromise = (async function () {
            nativeLiveMode = mode === "agentic" ? "agentic" : "conversational";
            nativeLiveStopping = false;
            nativeLiveActive = true;

            try {
                setNativeLiveStatus(
                    "CONNECTING (GEMINI LIVE)",
                    "Opening native real-time audio channel…"
                );

                // Request microphone permission and wake the audio hardware while
                // the token request happens, minimizing perceived startup delay.
                var mediaPromise = navigator.mediaDevices.getUserMedia({
                    audio: {
                        channelCount: 1,
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true
                    },
                    video: false
                });

                var tokenPromise = fetchLiveToken(nativeLiveMode);
                var results = await Promise.all([mediaPromise, tokenPromise]);

                nativeLiveMediaStream = results[0];
                nativeLiveConfig = results[1];

                await ensureAudioContexts();

                nativeOutputContext.resume().catch(function () {});
                nativeInputContext.resume().catch(function () {});

                if (nativeInputWorklet) {
                    try { nativeInputWorklet.disconnect(); } catch (_) {}
                    nativeInputWorklet = null;
                }
                if (nativeMicSource) {
                    try { nativeMicSource.disconnect(); } catch (_) {}
                    nativeMicSource = null;
                }

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

                    var bytes = new Uint8Array(event.data);
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
            setNativeLiveStatus(
                "LIVE RECONNECT FAILED",
                String(err.message || err)
            );
        }
    }

    async function stopNativeLive() {
        nativeLiveStopping = true;
        nativeLiveActive = false;

        if (nativeReconnectTimer) {
            clearTimeout(nativeReconnectTimer);
            nativeReconnectTimer = null;
        }

        if (nativeLiveSocket) {
            try { nativeLiveSocket.close(1000, "user-stop"); } catch (_) {}
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

    function toggleNativeLiveConversation() {
        if (nativeLiveActive) return stopNativeLive();
        return startNativeLive("conversational");
    }

    function handleNativeOrbClick() {
        if (!nativeLiveActive) {
            return startNativeLive("conversational");
        }

        // Gemini Live VAD detects human speech and interrupts model audio. The
        // orb provides an explicit local stop/clear affordance as well.
        clearNativeOutputAudio();
        setNativeLiveStatus(
            "LISTENING (GEMINI LIVE)",
            "Listening for your next word"
        );
    }

    // Public API.
    window.startSarembokLiveVoice = startSarembokLiveVoice;
    window.startSarembokLiveAgent = function () {
        return startSarembokLiveVoice("agentic");
    };
    window.toggleNativeLiveConversation = toggleNativeLiveConversation;

    // Override only the legacy public entry points. The old SpeechRecognition /
    // Kokoro functions remain available as fallback implementation code but are
    // no longer used by the live voice controls.
    window.toggleLiveConversation = toggleNativeLiveConversation;
    window.handleOrbClick = handleNativeOrbClick;

    // Keep the standard "live" controls pointed at the native stack.
    document.addEventListener("DOMContentLoaded", function () {
        var starter = document.querySelector(".simple-starter-card[onclick*='startSimpleVoice']");
        if (starter) starter.setAttribute("onclick", "startSarembokLiveVoice()");

        var mic = document.getElementById("dialogue-mic-btn");
        if (mic) {
            mic.setAttribute("onclick", "toggleLiveConversation()");
            mic.title = "Start native Gemini Live conversation";
        }

        var liveBtn = document.getElementById("hud-live-2way-btn");
        if (liveBtn) {
            liveBtn.setAttribute("onclick", "toggleLiveConversation()");
            var label = liveBtn.querySelector("span");
            if (label) label.textContent = "LIVE VOICE";
        }

        var kokoroBtn = document.getElementById("srbk-kokoro-btn");
        if (kokoroBtn) {
            var spans = kokoroBtn.querySelectorAll("span");
            if (spans.length > 1) spans[1].textContent = "KOKORO FALLBACK";
        }

        var kokoroTitle = document.querySelector(".srbk-kokoro-title");
        if (kokoroTitle) kokoroTitle.textContent = "KOKORO FALLBACK";

        var kokoroStatus = document.getElementById("srbk-kokoro-status");
        if (kokoroStatus) {
            kokoroStatus.textContent =
                "Fallback neural speech only. Live conversation uses native Gemini Live audio.";
        }

        var kokoroState = document.getElementById("srbk-kokoro-state");
        if (kokoroState) kokoroState.textContent = "FALLBACK";

        var kokoroTest = document.getElementById("srbk-kokoro-test");
        if (kokoroTest) kokoroTest.textContent = "▶ TEST FALLBACK VOICE";
    });

    window.addEventListener("pagehide", function () {
        try { void stopNativeLive(); } catch (_) {}
    });
})();