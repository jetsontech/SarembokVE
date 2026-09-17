/* SAREMBOK_RUNTIME_UI_VISIBILITY_FIX_V1_20260917 */
(function installSarembokRuntimeUiVisibilityFix() {
    "use strict";

    if (window.__srbkRuntimeUiVisibilityFixV1) return;
    window.__srbkRuntimeUiVisibilityFixV1 = true;

    function forceVisibleControl(el, displayValue) {
        if (!el) return;
        try { el.hidden = false; } catch (_) {}
        el.removeAttribute("hidden");
        el.setAttribute("aria-hidden", "false");
        el.style.setProperty("visibility", "visible", "important");
        el.style.setProperty("opacity", "1", "important");
        el.style.setProperty("pointer-events", "auto", "important");
        el.style.setProperty("display", displayValue, "important");
    }

    function unhideControlAncestors(el) {
        let node = el && el.parentElement;
        let depth = 0;
        while (node && depth < 8 && !node.classList.contains("view-panel") && node.id !== "app") {
            const style = getComputedStyle(node);
            if (node.hidden) node.hidden = false;
            node.removeAttribute("hidden");
            if (style.display === "none") node.style.setProperty("display", "block", "important");
            if (style.visibility === "hidden") node.style.setProperty("visibility", "visible", "important");
            if (parseFloat(style.opacity || "1") === 0) node.style.setProperty("opacity", "1", "important");
            if (style.pointerEvents === "none") node.style.setProperty("pointer-events", "auto", "important");
            node = node.parentElement;
            depth += 1;
        }
    }

    function repairDialogueControls() {
        const view = document.getElementById("view-dialogue");
        if (!view || !view.classList.contains("active")) return;

        const input = document.getElementById("directive-input");
        const execute = document.getElementById("execute-button");

        [input, execute].forEach(unhideControlAncestors);
        forceVisibleControl(input, "block");
        forceVisibleControl(execute, "inline-flex");

        window.__srbkDialogueControlsVisible = !!(
            input && execute &&
            getComputedStyle(input).display !== "none" &&
            getComputedStyle(execute).display !== "none"
        );
    }

    function installNavigationHook() {
        const original = window.switchTab;
        if (typeof original !== "function" || original.__srbkRuntimeUiVisibilityFixV1) return;

        function repairedSwitchTab(...args) {
            const result = original.apply(this, args);
            const tabId = args[0];
            if (tabId === "dialogue") {
                requestAnimationFrame(repairDialogueControls);
                setTimeout(repairDialogueControls, 0);
                setTimeout(repairDialogueControls, 150);
            }
            return result;
        }

        repairedSwitchTab.__srbkRuntimeUiVisibilityFixV1 = true;
        repairedSwitchTab.__srbkOriginal = original;
        window.switchTab = repairedSwitchTab;
    }

    function install() {
        installNavigationHook();
        repairDialogueControls();
        window.addEventListener("load", repairDialogueControls, { once: false, passive: true });
        document.addEventListener("visibilitychange", repairDialogueControls, { passive: true });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", install, { once: true });
    } else {
        install();
    }
})();
