"""TubiStreamingBridge: Stealth Playwright video streaming bridge for Tubi platform playback.

Architectural Overrides:
1. Stealth Args Injection:
   - "--disable-blink-features=AutomationControlled"
   - "--disable-infobars"
   - Desktop User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
2. Direct Slug Resolution Routing:
   - target_url = f"https://tubitv.com/{movie_title.lower().replace(' ', '-')}"
   - 404/Exception fallback with strict selector "div[data-testid='video-thumbnail'] a"
"""

from __future__ import annotations

import asyncio
import logging
import re
import urllib.parse
from typing import Any, Optional

LOG = logging.getLogger("sarembok.tubi_bridge")

STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

STEALTH_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
]


class TubiStreamingBridge:
    """Playwright video streaming bridge with stealth automation shield and direct slug resolution."""

    def __init__(self, db_connection: Optional[Any] = None) -> None:
        self.db_connection = db_connection
        self.active_page = None
        self.browser_context = None

    def construct_direct_slug_url(self, movie_title: str) -> str:
        """Constructs direct asset URL based on lowercase hyphenated movie title string."""
        clean_title = movie_title.lower().strip()
        slug = clean_title.replace(" ", "-")
        slug = re.sub(r"[^a-z0-9\-]", "", slug)
        return f"https://tubitv.com/{slug}"

    async def launch_stream(self, movie_query: str) -> dict[str, Any]:
        """Launches Playwright Chromium session with stealth shield and resolves target movie."""
        target_slug_url = self.construct_direct_slug_url(movie_query)
        fallback_search_url = f"https://tubitv.com/search/{urllib.parse.quote(movie_query)}"
        strict_selector = "div[data-testid='video-thumbnail'] a"

        print(f"[TubiStreamingBridge] Initiating stealth playback for '{movie_query}'")
        print(f"[TubiStreamingBridge] Primary Direct Slug URL: {target_slug_url}")

        result: dict[str, Any] = {
            "query": movie_query,
            "platform": "tubi",
            "direct_slug_url": target_slug_url,
            "fallback_url": fallback_search_url,
            "selector": strict_selector,
            "stealth_shield": True,
            "user_agent": STEALTH_USER_AGENT,
            "status": "initialized",
        }

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("[TubiStreamingBridge] Playwright module not installed in current Python env; returning resolved routing metadata.")
            result["status"] = "resolved_metadata_only"
            result["stream_url"] = target_slug_url
            return result

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=STEALTH_LAUNCH_ARGS,
                )
                context = await browser.new_context(
                    user_agent=STEALTH_USER_AGENT,
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                )
                page = await context.new_page()

                # Stealth evasion init script
                await page.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )

                resolved_url = target_slug_url
                resolved_method = "direct_slug"

                # Step 1: Direct slug resolution
                try:
                    print(f"[TubiStreamingBridge] Attempting direct slug navigation to {target_slug_url}...")
                    resp = await page.goto(target_slug_url, wait_until="domcontentloaded", timeout=12000)
                    status_code = resp.status if resp else 404

                    if status_code >= 400 or "not-found" in page.url or "404" in page.url:
                        raise ValueError(f"Direct slug 404 (status={status_code}, url={page.url})")

                    print(f"[TubiStreamingBridge] Direct slug resolved successfully: {page.url}")
                    resolved_url = page.url

                except Exception as direct_err:
                    print(f"[TubiStreamingBridge] Direct slug resolution failed: {direct_err}. Initiating fallback search...")
                    resolved_method = "fallback_thumbnail"
                    await page.goto(fallback_search_url, wait_until="domcontentloaded", timeout=15000)

                    try:
                        await page.wait_for_selector(strict_selector, timeout=8000)
                        first_thumb = await page.query_selector(strict_selector)
                        if first_thumb:
                            href = await first_thumb.get_attribute("href")
                            if href:
                                resolved_url = f"https://tubitv.com{href}" if href.startswith("/") else href
                                print(f"[TubiStreamingBridge] Native thumbnail matched via '{strict_selector}': {resolved_url}")
                                await first_thumb.click()
                    except Exception as sel_err:
                        print(f"[TubiStreamingBridge] Selector '{strict_selector}' error: {sel_err}")

                result["status"] = "streaming_active"
                result["resolved_url"] = resolved_url
                result["resolution_method"] = resolved_method

                # Save record if database connection present
                if self.db_connection and hasattr(self.db_connection, "execute"):
                    try:
                        self.db_connection.execute(
                            "INSERT INTO media_playback_events (query, platform, url, timestamp) VALUES (?, ?, ?, datetime('now'))",
                            (movie_query, "tubi", resolved_url),
                        )
                    except Exception as db_err:
                        LOG.debug("DB write deferred: %s", db_err)

                return result

        except Exception as err:
            print(f"[TubiStreamingBridge] Playwright runtime notice: {err}")
            result["status"] = "error"
            result["error"] = str(err)
            return result
