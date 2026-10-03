#!/usr/bin/env bash
set -Eeuo pipefail

BASE_URL="${SAREMBOK_PUBLIC_URL:-https://sarembok.com}"

fetch() {
  curl -fsSL --retry 2 --connect-timeout 8 --max-time 20 \
    -H 'User-Agent: SarembokFrontierVerifier/1.0' "$1"
}

MAIN="$(fetch "$BASE_URL/")"
CSS="$(fetch "$BASE_URL/frontier-chat.css?v=20261002-ui2")"
CONSOLE="$(fetch "$BASE_URL/console")"

grep -q 'frontier-chat.css' <<<"$MAIN"
grep -q 'sarembok_ui_mode_v2' <<<"$MAIN"
grep -q 'id="global-input-field"' <<<"$MAIN"
grep -q 'id="global-send-btn"' <<<"$MAIN"
grep -q 'localStorage.setItem('\''sarembok_ui_mode_v2'\'', '\''simple'\'')' <<<"$MAIN"
grep -q 'void toggleLiveConversation()' <<<"$MAIN"
grep -q 'const data = await sendRPC("ListTasks", {})' <<<"$MAIN"
grep -q 'id="srbk-kokoro-btn"' <<<"$MAIN"
grep -q 'frontier conversation shell' <<<"$CSS"
grep -q 'Sarembok' <<<"$CONSOLE"

printf 'FRONTIER UI: PASS\n'
printf 'MAIN_HTML_BYTES: %s\n' "${#MAIN}"
printf 'UI_CSS_BYTES: %s\n' "${#CSS}"
printf 'CONSOLE_HTML_BYTES: %s\n' "${#CONSOLE}"
