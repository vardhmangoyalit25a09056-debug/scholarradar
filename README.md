# ScholarRadar

Tell it your state, category, course, income and marks. TinyFish agents read official
scholarship/scheme portals (mostly PDFs, JS-heavy pages, no APIs) and you get only the
schemes you qualify for, soonest deadline first.

Built for **Kritical Hacks '26** (online round). TinyFish is the core of the pipeline.

## How TinyFish is used (and why it's cheap)

```
Profile ──> Search (FREE)  find official pages (.gov.in / .nic.in / .ac.in only)
        ──> Fetch  (FREE)  gate: drop dead / irrelevant pages BEFORE spending anything
        ──> Agent  (metered) extract name, amount, deadline, eligibility as JSON  -- once per page
        ──> cache (24h)    every later student reuses the extracted scheme
        ──> matcher.py     pure Python eligibility + deadline ranking, zero API cost
```

Agent spend scales with the **number of schemes**, not the number of **students**.
Every response reports `agent_runs`, `cache_hits`, `dropped_by_gate` and `est_cost_usd`.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # add TINYFISH_API_KEY (https://agent.tinyfish.ai/)
uvicorn app.main:app --reload   # open http://localhost:8000
pytest                          # 6 tests
```

With no API key the app runs in **offline-sample mode** on fictional schemes in
`data/sample_schemes.json`, so you can demo the UI and matcher anywhere.

## Honest status

- Matcher, ranking, caching, gate and API are tested (`pytest`).
- The TinyFish calls follow the endpoints in the official cookbook README, but the
  exact JSON response field names are **assumed** (`app/tinyfish.py` parses defensively).
  Run once with a real key and adjust `tinyfish.py` if a field name differs.
- Extracted eligibility comes from an agent reading a web page. Always verify on the
  official page before applying (the UI links to it).

## Layout

```
app/tinyfish.py   TinyFish Search / Fetch / Agent client
app/pipeline.py   discover -> gate -> extract -> cache
app/matcher.py    eligibility + deadline ranking
app/main.py       FastAPI (POST /api/match)
static/index.html single-page UI
```

## Roadmap

Deadline alerts (WhatsApp/email), Hindi/Punjabi UI, state-portal coverage, B2B dashboard for colleges.
