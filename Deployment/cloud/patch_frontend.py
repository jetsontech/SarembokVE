from pathlib import Path

INDEX = Path('/app/frontend/index.html')

text = INDEX.read_text(encoding='utf-8')

# Deterministic, idempotent production patch.
# The frontend source remains the source of truth. Fail loudly if the expected
# structure has drifted instead of silently producing a partially updated site.
if 'document.querySelectorAll(\'.view-section\').forEach(s => s.classList.remove(\'active\'));' not in text:
    raise RuntimeError(
        'Frontend patch refused: expected current view-section navigation source not found'
    )

# Production WebSocket traffic must terminate at the /ws reverse-proxy route.
if 'const url = `${protocol}//${host}`;' in text:
    text = text.replace(
        'const url = `${protocol}//${host}`;',
        'const url = `${protocol}//${host}/ws`;'
    )
elif 'const url = `${protocol}//${host}/ws`;' in text:
    pass
else:
    raise RuntimeError(
        'Frontend patch refused: expected WebSocket URL construction not found'
    )

# SarembokVE public identity: the site must describe the actual platform being
# built, not frame Unreal Engine as the product or a public-user prerequisite.
replacements = [
    (
        '<title>Sarembok VE — Autonomous Digital Human & AI Cloud Platform</title>',
        '<title>SarembokVE — AI-Native Computing Environment</title>',
    ),
    (
        '<meta name="description" content="Sarembok VE is an autonomous digital human and AI runtime platform with real-time WebSocket control plane and Unreal Engine 5.8 integration.">',
        '<meta name="description" content="SarembokVE is an independent AI-native computing platform combining persistent intelligence, agents, memory, perception, execution, security, distributed compute, a native system layer, and high-fidelity digital-human embodiment.">',
    ),
    (
        '<div class="hero-tag">PRODUCTION DEPLOYMENT PLATFORM</div>',
        '<div class="hero-tag">AI-NATIVE COMPUTING ENVIRONMENT</div>',
    ),
    (
        '<h1 class="hero-title">Autonomous Digital Human & Embodied AI Runtime</h1>',
        '<h1 class="hero-title">A New Computing Environment for Autonomous Intelligence</h1>',
    ),
    (
        'Sarembok VE bridges high-performance cloud intelligence with in-engine Unreal Engine 5.8 digital humans, enabling real-time voice, vision, memory, and cognitive task execution.',
        'SarembokVE unifies persistent intelligence, autonomous agents, memory, perception, execution, security, distributed compute, and a high-fidelity digital human into one cloud-first computing environment. The embodiment technology belongs inside the platform; public users do not install Unreal Engine or specialized hardware.',
    ),
    (
        '<button class="btn btn-outline" onclick="switchTab(\'unreal\')">Connect Unreal Client</button>',
        '<button class="btn btn-outline" onclick="switchTab(\'unreal\')">View Embodiment Layer</button>',
    ),
    (
        'MetaHuman ARKit morph target integration with synchronized neural voice profiles and spatial viseme calculation.',
        'High-fidelity digital-human embodiment is a first-class SarembokVE system capability. Rendering technology operates behind the platform rather than becoming a public-user prerequisite.',
    ),
    (
        'Dynamic compute scheduling across GPU worker nodes for low-latency LLM reasoning and real-time avatar rendering.',
        'Distributed compute workers provide scalable execution for intelligence, perception, rendering, and autonomous workloads without requiring specialized hardware on the public client.',
    ),
    (
        '<h3 class="card-title">Unreal Engine 5.8 Bridge</h3>',
        '<h3 class="card-title">High-Fidelity Embodiment Infrastructure</h3>',
    ),
    (
        'Secure bidirectional JSON-RPC WebSocket protocol (`sarembok.v1`) connecting Unreal Engine to the Sarembok cloud.',
        'SarembokVE owns the runtime and protocol boundary. Unreal Engine and comparable rendering systems are infrastructure components used to deliver high-fidelity embodiment, not the definition of the platform.',
    ),
    (
        '<h3 class="card-title">Unreal Engine 5.8 Production Integration</h3>',
        '<h3 class="card-title">High-Fidelity Embodiment Development Layer</h3>',
    ),
    (
        'Connect your Sarembok VE Unreal project to the production cloud endpoint. Copy the initialization configuration below into your project\'s C++ or Blueprint settings.',
        'This development layer provides high-fidelity embodiment integration for the SarembokVE platform. Public users access the resulting system through supported clients and do not install Unreal Engine.',
    ),
]

for old, new in replacements:
    if old not in text:
        raise RuntimeError(f'Frontend patch refused: expected text not found: {old[:100]!r}')
    text = text.replace(old, new)

# ---------------------------------------------------------------------------
# PUBLIC PLATFORM V2
# ---------------------------------------------------------------------------
# This section is deliberately inserted into the generated landing page so
# the public site has a substantial visual/product-identity change instead of
# only metadata or wording changes. It does not alter the runtime controls.
if 'id="sarembok-public-v2"' not in text:
    public_css = r'''<style id="sarembok-public-v2">
.sarembok-about {
    max-width: 1180px;
    margin: 18px auto 56px;
    padding: 34px;
    border: 1px solid rgba(0,255,204,.22);
    border-radius: 22px;
    background:
        radial-gradient(circle at 15% 0%, rgba(0,255,204,.10), transparent 38%),
        radial-gradient(circle at 90% 100%, rgba(255,0,127,.08), transparent 40%),
        rgba(18,21,31,.92);
    box-shadow: 0 24px 80px rgba(0,0,0,.35), 0 0 0 1px rgba(255,255,255,.02) inset;
}
.sarembok-about-kicker {
    color: var(--cyan);
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    margin-bottom: 12px;
}
.sarembok-about h2 {
    max-width: 900px;
    font-size: clamp(30px, 4vw, 48px);
    line-height: 1.08;
    margin-bottom: 16px;
    color: #fff;
}
.sarembok-about-lead {
    max-width: 920px;
    color: var(--text-secondary);
    font-size: 17px;
    line-height: 1.7;
    margin-bottom: 30px;
}
.sarembok-about-lead strong { color: #fff; }
.sarembok-stack {
    display: grid;
    grid-template-columns: repeat(4, minmax(0,1fr));
    gap: 14px;
}
.sarembok-stack-card {
    min-height: 158px;
    padding: 19px;
    border: 1px solid var(--border-color);
    border-radius: 15px;
    background: rgba(7,9,13,.78);
    transition: transform .2s ease, border-color .2s ease, background .2s ease;
}
.sarembok-stack-card:hover {
    transform: translateY(-3px);
    border-color: rgba(0,255,204,.38);
    background: rgba(15,19,27,.92);
}
.sarembok-stack-card .number {
    color: var(--magenta);
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    margin-bottom: 13px;
}
.sarembok-stack-card h3 { color:#fff; font-size:16px; margin-bottom:8px; }
.sarembok-stack-card p { color:var(--text-secondary); font-size:13px; line-height:1.55; }
.sarembok-about-statement {
    margin-top: 26px;
    padding: 18px 20px;
    border-left: 3px solid var(--cyan);
    background: rgba(0,255,204,.045);
    color: #dbeafe;
    line-height: 1.65;
    font-size: 14px;
}
.sarembok-about-statement strong { color:#fff; }
@media (max-width: 900px) { .sarembok-stack { grid-template-columns: repeat(2,1fr); } }
@media (max-width: 600px) {
    .sarembok-about { padding:24px 18px; margin:10px 16px 36px; }
    .sarembok-stack { grid-template-columns:1fr; }
}
</style>'''

    public_about = r'''<section class="sarembok-about" id="about">
    <div class="sarembok-about-kicker">SAREMBOKVE / PLATFORM ARCHITECTURE</div>
    <h2>The runtime, agent fabric, memory, compute, and digital human are one system.</h2>
    <p class="sarembok-about-lead">
        <strong>An advanced Unreal Engine 5.8 digital-human orchestration architecture and AI runtime platform.</strong>
        SarembokVE is being built as an independent AI-native computing environment with its own runtime, agent architecture,
        persistent memory, execution fabric, security model, distributed compute, native system-layer technology, and
        high-fidelity digital-human embodiment.
    </p>

    <div class="sarembok-stack">
        <article class="sarembok-stack-card">
            <div class="number">01 / RUNTIME</div>
            <h3>Autonomous AI Runtime</h3>
            <p>Persistent intelligence, task execution, provider-neutral routing, real-time control, and system orchestration.</p>
        </article>
        <article class="sarembok-stack-card">
            <div class="number">02 / AGENT FABRIC</div>
            <h3>Cooperating Agents</h3>
            <p>Agents with memory, planning, permissions, tools, execution state, and lifecycle control.</p>
        </article>
        <article class="sarembok-stack-card">
            <div class="number">03 / COMPUTE</div>
            <h3>Distributed Intelligence</h3>
            <p>Cloud and worker infrastructure for reasoning, perception, rendering, automation, and autonomous workloads.</p>
        </article>
        <article class="sarembok-stack-card">
            <div class="number">04 / EMBODIMENT</div>
            <h3>Digital Human System</h3>
            <p>High-fidelity embodiment for voice, vision, interaction, presence, and real-time human-facing intelligence.</p>
        </article>
    </div>

    <div class="sarembok-about-statement">
        <strong>SarembokVE owns the platform boundary.</strong>
        Unreal Engine 5.8 is an advanced embodiment and development technology inside that architecture—not the product itself.
        Public users do not need Unreal Engine, a gaming PC, a local GPU, Docker, or local AI infrastructure to use SarembokVE.
    </div>
</section>'''

    if '</head>' not in text:
        raise RuntimeError('Frontend patch refused: </head> anchor not found')
    if '<div class="feature-grid">' not in text:
        raise RuntimeError('Frontend patch refused: feature-grid anchor not found')

    text = text.replace('</head>', public_css + '\n</head>', 1)
    text = text.replace('<div class="feature-grid">', public_about + '\n\n            <div class="feature-grid">', 1)

# Make browser-visible branding match the platform identity.
text = text.replace(
    '<span class="brand-sub">AUTONOMOUS DIGITAL HUMAN RUNTIME</span>',
    '<span class="brand-sub">AI-NATIVE COMPUTING ENVIRONMENT</span>',
    1,
)

# Add a stable marker for deployment verification.
if 'data-sarembok-public-version="2"' not in text:
    text = text.replace(
        '<body>',
        '<body data-sarembok-public-version="2"><!-- SAREMBOK PUBLIC PLATFORM V2 -->',
        1,
    )

INDEX.write_text(text, encoding='utf-8')
print('SarembokVE public platform frontend patch applied successfully: PUBLIC V2')
