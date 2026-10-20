from datetime import date

from app.matcher import Profile, match, rank

TODAY = date(2026, 10, 20)
S = {"name": "X", "deadline": "2026-11-30",
     "eligibility": {"states": ["punjab"], "categories": ["sc", "obc"], "courses": ["all"],
                     "max_income": 250000, "min_percentage": 60, "gender": "all"}}


def test_eligible():
    p = Profile(state="Punjab", category="OBC", annual_income=200000, percentage=70)
    r = match(S, p, TODAY)
    assert r.eligible and r.days_left == 41


def test_income_fail():
    p = Profile(state="Punjab", category="OBC", annual_income=900000, percentage=70)
    assert not match(S, p, TODAY).eligible


def test_wrong_state():
    p = Profile(state="Delhi", category="OBC", annual_income=1, percentage=70)
    assert not match(S, p, TODAY).eligible


def test_unknown_fields_flagged_not_failed():
    r = match(S, Profile(state="Punjab"), TODAY)
    assert r.eligible and {"category", "income", "percentage"} <= set(r.to_verify)


def test_expired_excluded_and_sorted():
    soon = {**S, "name": "soon", "deadline": "2026-10-25"}
    late = {**S, "name": "late", "deadline": "2026-12-01"}
    old = {**S, "name": "old", "deadline": "2026-01-01"}
    p = Profile(state="Punjab", category="SC", annual_income=1, percentage=90)
    names = [r.scheme["name"] for r in rank([late, old, soon], p, TODAY)]
    assert names == ["soon", "late"]
