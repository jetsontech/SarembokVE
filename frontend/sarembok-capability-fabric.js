/* Sarembok Capability Fabric UI — runtime-derived, not marketing labels. */
(() => {
    "use strict";

    const LABELS = {
        web: "WEB",
        research: "RESEARCH",
        w3c: "W3C / STANDARDS",
        knowledge: "KNOWLEDGE",
        agents: "AGENTS",
        memory: "MEMORY",
        workers: "WORKERS",
        compute: "COMPUTE",
        browser: "BROWSER",
        apis: "APIs"
    };

    function stateFor(surface, fallback = "UNKNOWN") {
        return String(surface?.state ?? fallback).toUpperCase();
    }

    function ensureFabric() {
        if (document.querySelector(".srbk-fabric")) return document.querySelector(".srbk-fabric");
        const deck = document.querySelector(".interactive-deck");
        if (!deck || !deck.parentElement) return null;
        const fabric = document.createElement("section");
        fabric.className = "srbk-fabric";
        fabric.setAttribute("aria-label", "Sarembok capability fabric");
        fabric.innerHTML = `
            <div class="srbk-fabric-head">
                <div class="srbk-fabric-title">Sarembok Capability Fabric</div>
                <div class="srbk-fabric-subtitle">LIVE RUNTIME AUTHORITY · CAPABILITY ≠ AUTHORIZATION</div>
            </div>
            <div class="srbk-fabric-grid"></div>`;
        deck.parentElement.insertBefore(fabric, deck);
        return fabric;
    }

    function render(snapshot) {
        const fabric = ensureFabric();
        if (!fabric) return;
        const grid = fabric.querySelector(".srbk-fabric-grid");
        const surfaces = snapshot?.capabilityFabric?.surfaces || [];
        const normalized = {};
        surfaces.forEach(surface => normalized[surface.id] = surface);
        if (!normalized.workers && snapshot?.workers) normalized.workers = { state: String(snapshot.workers.online || 0) };

        grid.innerHTML = Object.entries(LABELS).map(([id, label]) => {
            const state = stateFor(normalized[id]);
            return `<div class="srbk-cap" data-state="${state.replace(/[^A-Z0-9_-]/g, "_")}">
                <span class="srbk-cap-label">${label}</span>
                <span class="srbk-cap-state">${state}</span>
            </div>`;
        }).join("");
    }

    function bindRuntimeAuthority() {
        if (typeof window.sendRPC !== "function") return false;
        window.sendRPC("GetRuntimeInfo")
            .then(render)
            .catch(() => {});
        return true;
    }

    function boot() {
        ensureFabric();
        if (!bindRuntimeAuthority()) setTimeout(bindRuntimeAuthority, 1200);
        setTimeout(() => bindRuntimeAuthority(), 8000);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }
})();
