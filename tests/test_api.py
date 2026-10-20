import os

from fastapi.testclient import TestClient

os.environ.pop("TINYFISH_API_KEY", None)

from app.main import app  # noqa: E402


def test_offline_mode_returns_sample_matches():
    c = TestClient(app)
    r = c.post("/api/match", json={"state": "Punjab", "category": "SC", "annual_income": 200000,
                                     "course": "B.Tech", "percentage": 75, "gender": "female"})
    assert r.status_code == 200
    body = r.json()
    assert body["stats"]["mode"] == "offline-sample"
    assert len(body["matches"]) >= 2
