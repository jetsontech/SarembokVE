from __future__ import annotations

import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
CLOUD = ROOT / "Deployment" / "cloud"
FAILURES: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        FAILURES.append(message)


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


compose = read(CLOUD / "compose.frontier_final.yaml")
entrypoint = read(CLOUD / "production_entrypoint_frontier.py")
policy = read(CLOUD / "frontier_runtime_policy.py")
deploy = read(CLOUD / "deploy_frontier_release.sh")

require("production_entrypoint_frontier.py" in compose, "frontier compose does not select v5 boundary")
require("SAREMBOK_WORKER_TOKEN_HASH_SALT" in compose and "SAREMBOK_WORKER_TOKEN_HASH_SALT" in deploy, "worker token salt is not wired")
require("SAREMBOK_ALLOW_ORIGINLESS_LOCAL:-false" in compose, "production originless-local default is not fail-closed")
require("verify_frontier_v2.sh" in deploy and "verify_frontier_e2e.sh" in deploy, "release script missing live verification")
require("ORIGINAL_VALIDATE(request)" not in entrypoint, "frontier validation still depends on legacy authentication")
require("Keep the restricted process_http_request" in entrypoint, "frontier HTTP lockdown is not preserved")
require("runtime.ensure_sovereign_worker = lambda: None" in policy, "synthetic worker bootstrap is not disabled")
require("_purge_synthetic_workers" in policy, "known synthetic worker records are not purged")
require('"hardwareAttestation":"NOT_ATTESTED"' in entrypoint, "hardware attestation state is not explicit")
require("CATALOG_ONLY_NO_COMPUTE_CAPACITY_ASSERTION" in entrypoint, "GPU catalog truth boundary is missing")

for label, source in (("frontier entrypoint", entrypoint), ("frontier policy", policy)):
    require("shell=True" not in source, f"{label} contains shell=True")
    require("eval(" not in source, f"{label} contains eval()")
    require("exec(" not in source, f"{label} contains exec()")

for path in (CLOUD / "production_entrypoint_frontier.py", CLOUD / "frontier_runtime_policy.py", CLOUD / "frontier_release_gate.py"):
    try:
        ast.parse(read(path), filename=str(path))
    except SyntaxError as exc:
        FAILURES.append(f"syntax error in {path}: {exc}")

require('set_if_missing SAREMBOK_ADMIN_PASSCODE "$(passcode)"' in deploy, "admin passcode is not generated at deployment")
require('set_if_missing SAREMBOK_AUTH_TOKEN "$(secret)"' in deploy, "operator secret is not generated at deployment")
require('set_if_missing SAREMBOK_MASTER_TOKEN "$(secret)"' in deploy, "master secret is not generated at deployment")
require(not re.search(r"\b(joc|sarembok2026)\b", entrypoint, re.I), "development credential appears in frontier entrypoint")

if FAILURES:
    print("FRONTIER STATIC GATE: FAIL")
    for failure in FAILURES:
        print(f"FAIL  {failure}")
    raise SystemExit(1)

print("FRONTIER STATIC GATE: PASS")
print("PASS  frontier compose selects production boundary v5")
print("PASS  worker token salt wired")
print("PASS  originless local access disabled by production default")
print("PASS  synthetic worker bootstrap disabled and legacy records purged")
print("PASS  hardware attestation truth explicitly reported")
print("PASS  GPU marketplace capacity claims bounded")
print("PASS  active frontier boundary contains no shell=True/eval/exec")
print("PASS  frontier Python modules parse")
print("PASS  deployment generates fresh secrets")
