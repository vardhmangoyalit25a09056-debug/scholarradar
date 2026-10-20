"""ScholarRadar pipeline: Search (free) -> Fetch gate (free) -> Agent (metered, cached).

Cost idea: a scheme page is extracted ONCE, cached, then matched against every
student's profile for free. Agent spend scales with the number of schemes,
not the number of students."""
import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse

from . import tinyfish
from .matcher import Profile

CACHE = Path(".cache/schemes.json")
SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_schemes.json"
TRUSTED_SUFFIXES = (".gov.in", ".nic.in", ".ac.in", ".edu.in", ".edu")
KEYWORDS = ("scholarship", "eligib", "deadline", "last date", "apply")

AGENT_GOAL = (
    "This page describes a scholarship or government education scheme. Extract it and "
    "return ONLY JSON with keys: name (string), provider (string), amount (string), "
    "deadline (YYYY-MM-DD or null), apply_url (string), "
    "eligibility: {states: [string] or ['all'], categories: [string] or ['all'], "
    "courses: [string] or ['all'], max_income: integer INR or null, "
    "min_percentage: number or null, gender: 'all'|'female'|'male'}. "
    "If the page is not a scholarship/scheme, return {\"name\": null}."
)


def _load_cache() -> dict:
    try:
        return json.loads(CACHE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(c: dict) -> None:
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(c, indent=2))


def _is_trusted(url: str) -> bool:
    return urlparse(url).netloc.lower().endswith(TRUSTED_SUFFIXES)


def build_queries(p: Profile) -> list[str]:
    base = "scholarship India 2026 official"
    qs = [f"{p.course} {base}".strip()]
    if p.category and p.category.lower() != "general":
        qs.append(f"{p.category} {base}")
    if p.state:
        qs.append(f"{p.state} state government {base}")
    return qs


def run(p: Profile) -> dict:
    """Returns {schemes: [...], stats: {...}}."""
    if not os.getenv("TINYFISH_API_KEY"):
        schemes = json.loads(SAMPLE.read_text())
        return {"schemes": schemes, "stats": {"mode": "offline-sample", "agent_runs": 0,
                                                "cache_hits": 0, "est_cost_usd": 0.0}}

    ttl = float(os.getenv("CACHE_TTL_HOURS", "24")) * 3600
    max_agent = int(os.getenv("MAX_AGENT_RUNS_PER_QUERY", "6"))
    cost_per_run = float(os.getenv("AGENT_COST_PER_RUN_USD", "0.05"))
    cache = _load_cache()
    stats = {"mode": "live", "searches": 0, "fetches": 0, "agent_runs": 0,
             "cache_hits": 0, "dropped_by_gate": 0}

    # 1) Discover (FREE)
    urls, seen = [], set()
    for q in build_queries(p):
        stats["searches"] += 1
        try:
            hits = tinyfish.search(q)
        except Exception:
            continue
        for h in hits:
            u = h["url"]
            if u not in seen and _is_trusted(u):
                seen.add(u)
                urls.append(u)

    schemes, to_check = [], []
    for u in urls:
        c = cache.get(u)
        if c and time.time() - c["ts"] < ttl:
            stats["cache_hits"] += 1
            if c["data"].get("name"):
                schemes.append(c["data"])
        else:
            to_check.append(u)

    # 2) Fetch gate (FREE): only spend an Agent run on pages that look like real scheme pages
    if to_check:
        stats["fetches"] += len(to_check)
        try:
            pages = tinyfish.fetch(to_check)
        except Exception:
            pages = {}
        gated = []
        for u in to_check:
            text = (pages.get(u) or "").lower()
            if sum(k in text for k in KEYWORDS) >= 2:
                gated.append(u)
            else:
                stats["dropped_by_gate"] += 1

        # 3) Extract (METERED, capped, cached)
        for u in gated[:max_agent]:
            stats["agent_runs"] += 1
            try:
                data = tinyfish.agent_run(u, AGENT_GOAL) or {"name": None}
            except Exception:
                continue
            data.setdefault("apply_url", u)
            cache[u] = {"ts": time.time(), "data": data}
            if data.get("name"):
                schemes.append(data)
        _save_cache(cache)

    stats["est_cost_usd"] = round(stats["agent_runs"] * cost_per_run, 4)
    return {"schemes": schemes, "stats": stats}
