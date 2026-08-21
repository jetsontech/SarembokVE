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
        'const url = `${protocol}//${host}/ws`'
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

INDEX.write_text(text, encoding='utf-8')
print('SarembokVE public platform frontend patch applied successfully.')
