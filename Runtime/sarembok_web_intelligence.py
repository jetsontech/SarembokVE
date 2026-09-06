"""Safe Web intelligence primitives for Sarembok.

This module provides retrieval/discovery primitives, not unrestricted access.
Authorization remains a separate policy decision at the runtime boundary.
"""
from __future__ import annotations

import ipaddress
import re
import socket
import urllib.parse
import urllib.request
from html import unescape
from typing import Any

USER_AGENT = "SarembokVE/2.0 (+https://sarembok.com)"
MAX_BYTES = 2_000_000
W3C_MAX_BYTES = 8_000_000
TIMEOUT_SECONDS = 15


def _validate_url(url: str) -> str:
    parsed = urllib.parse.urlparse(str(url).strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("only_http_https_urls_are_supported")
    host = parsed.hostname
    if host.lower() in {"localhost", "localhost.localdomain"}:
        raise PermissionError("local_hosts_are_not_allowed")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise ValueError(f"dns_resolution_failed:{host}") from exc
    for info in infos:
        addr = ipaddress.ip_address(info[4][0])
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_multicast or addr.is_reserved:
            raise PermissionError("private_or_reserved_network_target")
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", parsed.query, ""))


def _fetch_bounded(
    url: str,
    *,
    max_bytes: int,
) -> dict[str, Any]:
    target = _validate_url(url)

    request = urllib.request.Request(
        target,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/json,text/plain;q=0.9,*/*;q=0.5"
            ),
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=TIMEOUT_SECONDS,
        ) as response:
            raw = response.read(max_bytes + 1)

            if len(raw) > max_bytes:
                raise ValueError("response_too_large")

            content_type = response.headers.get("Content-Type", "")
            charset = (
                response.headers.get_content_charset()
                or "utf-8"
            )
            text = raw.decode(charset, errors="replace")

            return {
                "url": response.geturl(),
                "status": int(response.status),
                "contentType": content_type,
                "bytes": len(raw),
                "text": (
                    _clean_text(text)
                    if "html" in content_type.lower()
                    else text
                ),
            }

    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"http_error:{exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"network_error:{exc.reason}"
        ) from exc


def _fetch_w3c(url: str) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(str(url).strip())

    if parsed.hostname not in {"www.w3.org", "w3.org"}:
        raise PermissionError("w3c_hosts_are_required")

    if not parsed.path.startswith("/TR/"):
        raise PermissionError("w3c_tr_resources_are_required")

    return _fetch_bounded(
        url,
        max_bytes=W3C_MAX_BYTES,
    )


def fetch(url: str) -> dict[str, Any]:
    target = _validate_url(url)
    request = urllib.request.Request(target, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/json,text/plain;q=0.9,*/*;q=0.5"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("response_too_large")
            content_type = response.headers.get("Content-Type", "")
            charset = response.headers.get_content_charset() or "utf-8"
            text = raw.decode(charset, errors="replace")
            return {
                "url": response.geturl(),
                "status": int(response.status),
                "contentType": content_type,
                "bytes": len(raw),
                "text": _clean_text(text) if "html" in content_type.lower() else text,
            }
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"http_error:{exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"network_error:{exc.reason}") from exc


def _clean_text(value: str) -> str:
    value = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", value)
    value = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def search(query: str, limit: int = 8) -> dict[str, Any]:
    q = str(query or "").strip()
    if not q:
        raise ValueError("query_required")
    limit = max(1, min(int(limit), 20))
    endpoint = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": q})
    result = fetch(endpoint)
    html = result["text"]
    # fetch() strips tags, so use a second bounded request only for result-link extraction.
    target = _validate_url(endpoint)
    request = urllib.request.Request(target, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        raw = response.read(MAX_BYTES)
    page = raw.decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    items = []
    pattern = re.compile(r'<a[^>]+class=["\']result__a["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
    for match in pattern.finditer(page):
        href = unescape(re.sub(r"<[^>]+>", "", match.group(1)))
        title = _clean_text(match.group(2))
        if href.startswith("//"):
            href = "https:" + href
        parsed = urllib.parse.urlparse(href)
        if "duckduckgo.com" in (parsed.hostname or "") and "uddg=" in parsed.query:
            href = urllib.parse.parse_qs(parsed.query).get("uddg", [href])[0]
        if title and href.startswith(("http://", "https://")):
            items.append({"title": title, "url": href})
        if len(items) >= limit:
            break
    return {"query": q, "results": items, "source": "duckduckgo-html"}


def w3c_research(topic: str) -> dict[str, Any]:
    q = str(topic or "").strip()
    if not q:
        raise ValueError("topic_required")

    index_url = "https://www.w3.org/TR/"
    index_request = urllib.request.Request(
        index_url,
        headers={"User-Agent": USER_AGENT},
    )

    with urllib.request.urlopen(
        index_request,
        timeout=TIMEOUT_SECONDS,
    ) as response:
        raw = response.read(MAX_BYTES + 1)

        if len(raw) > MAX_BYTES:
            raise ValueError("w3c_index_too_large")

        html = raw.decode(
            response.headers.get_content_charset() or "utf-8",
            errors="replace",
        )

    matches = re.findall(
        r"<a[^>]+href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>",
        html,
        re.IGNORECASE | re.DOTALL,
    )

    # Rank candidates using meaningful topic terms only.
    query_terms = [
        term.lower()
        for term in re.findall(r"[a-z0-9]+", q.lower())
        if len(term) >= 2
        and term.lower() not in {
            "w3c",
            "web",
            "research",
            "standard",
            "standards",
            "spec",
            "specification",
        }
    ]

    if not query_terms:
        query_terms = [
            term.lower()
            for term in re.findall(r"[a-z0-9]+", q.lower())
            if len(term) >= 2
        ]

    candidates = []

    for href, label in matches:
        clean_label = _clean_text(label)

        if not clean_label or not href:
            continue

        absolute = urllib.parse.urljoin(index_url, href)
        parsed = urllib.parse.urlparse(absolute)
        normalized_path = parsed.path.rstrip("/")

        if (
            parsed.scheme != "https"
            or parsed.hostname not in {"www.w3.org", "w3.org"}
            or not normalized_path.startswith("/TR/")
        ):
            continue

        title_text = clean_label.lower()
        path_text = normalized_path.lower()

        matched_terms = [
            term
            for term in query_terms
            if term in title_text or term in path_text
        ]

        if not matched_terms:
            continue

        score = len(matched_terms) * 10

        # Exact title match gets the strongest ranking signal.
        if clean_label.strip().lower() == q.strip().lower():
            score += 100

        # Current canonical /TR/<slug> specifications outrank snapshots.
        if re.fullmatch(r"/TR/[^/]+", normalized_path, re.IGNORECASE):
            score += 20

        # Historical dated snapshots remain useful, but rank lower.
        if re.match(r"^/TR/\d{4}/", normalized_path, re.IGNORECASE):
            score -= 10

        candidates.append(
            {
                "title": clean_label,
                "url": absolute,
                "score": score,
            }
        )

    candidates.sort(
        key=lambda item: (-item["score"], item["title"].lower())
    )

    # Discovery is the ranked set presented to the evidence collector.
    discovery = {
        "query": q,
        "source": "w3c-tr-index",
        "results": candidates[:10],
    }

    # Retrieve only the highest-ranked bounded set.
    evidence = []

    for item in candidates[:5]:
        try:
            page = _fetch_w3c(item["url"])
            text = page.get("text", "")

            evidence.append(
                {
                    "title": item["title"],
                    "url": page.get("url", item["url"]),
                    "status": page.get("status"),
                    "contentType": page.get("contentType"),
                    "excerpt": text[:4000],
                    "score": item["score"],
                }
            )
        except Exception as exc:
            evidence.append(
                {
                    "title": item["title"],
                    "url": item["url"],
                    "error": str(exc),
                    "score": item["score"],
                }
            )

    return {
        "topic": q,
        "scope": "W3C and Web standards",
        "discovery": discovery,
        "evidence": evidence,
        "provenance": (
            "Discovery is performed against the W3C /TR/ index. "
            "Each evidence item records the retrieved W3C URL "
            "and HTTP status."
        ),
    }


def research(query: str, limit: int = 8) -> dict[str, Any]:
    """Run a bounded discovery pass and retrieve evidence from public sources."""
    discovery = search(query, limit=limit)
    evidence = []
    for item in discovery["results"][: min(5, limit)]:
        try:
            page = fetch(item["url"])
            evidence.append({
                "title": item["title"],
                "url": page["url"],
                "status": page["status"],
                "contentType": page["contentType"],
                "excerpt": page["text"][:2500],
            })
        except Exception as exc:
            evidence.append({"title": item["title"], "url": item["url"], "error": type(exc).__name__})
    return {
        "query": query,
        "discovery": discovery,
        "evidence": evidence,
        "verification": {"retrieved": sum(1 for item in evidence if "error" not in item), "failed": sum(1 for item in evidence if "error" in item)},
    }
