"""Thin TinyFish client. All response parsing is isolated here so that if the
API response shape differs from what we assume, only this file needs a tweak.

Endpoints (from the official tinyfish-cookbook README):
  Search : GET  https://api.search.tinyfish.ai?query=...        (free)
  Fetch  : POST https://api.fetch.tinyfish.ai {"urls": [...]}   (free)
  Agent  : POST https://agent.tinyfish.ai/v1/automation/run-sse (metered)
"""
import json
import os

import requests

SEARCH_URL = "https://api.search.tinyfish.ai"
FETCH_URL = "https://api.fetch.tinyfish.ai"
AGENT_URL = "https://agent.tinyfish.ai/v1/automation/run-sse"
TIMEOUT = 60


class TinyFishError(RuntimeError):
    pass


def _headers() -> dict:
    key = os.getenv("TINYFISH_API_KEY")
    if not key:
        raise TinyFishError("TINYFISH_API_KEY not set")
    return {"X-API-Key": key, "Content-Type": "application/json"}


def _first_list(payload, keys=("results", "data", "items")):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in keys:
            if isinstance(payload.get(k), list):
                return payload[k]
    return []


def search(query: str) -> list[dict]:
    """FREE. Returns [{url, title, snippet}]."""
    r = requests.get(SEARCH_URL, params={"query": query}, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    out = []
    for item in _first_list(r.json()):
        url = item.get("url") or item.get("link")
        if url:
            out.append({
                "url": url,
                "title": item.get("title", ""),
                "snippet": item.get("snippet") or item.get("description", ""),
            })
    return out


def fetch(urls: list[str]) -> dict[str, str]:
    """FREE. Returns {url: markdown_text}. Failed URLs are simply absent."""
    r = requests.post(FETCH_URL, json={"urls": urls}, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    out = {}
    for item in _first_list(r.json()):
        url = item.get("url")
        text = item.get("markdown") or item.get("content") or item.get("text") or ""
        if url and text:
            out[url] = text
    return out


def agent_run(url: str, goal: str) -> dict | None:
    """METERED. Natural-language goal on a URL; streams SSE, returns final JSON."""
    r = requests.post(AGENT_URL, json={"url": url, "goal": goal},
                      headers=_headers(), stream=True, timeout=300)
    r.raise_for_status()
    result = None
    for line in r.iter_lines():
        if not line:
            continue
        s = line.decode("utf-8")
        if not s.startswith("data: "):
            continue
        try:
            event = json.loads(s[6:])
        except json.JSONDecodeError:
            continue
        for k in ("resultJson", "result", "output", "data"):
            if isinstance(event, dict) and event.get(k):
                result = event[k]
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            return None
    return result if isinstance(result, dict) else None
