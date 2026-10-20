"""Pure-Python eligibility matcher. No API cost: runs for every student, on
scheme data that was extracted ONCE and cached."""
from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class Profile:
    state: str = ""
    category: str = ""                 # General / OBC / SC / ST / EWS
    annual_income: int | None = None   # family income, INR
    course: str = ""                   # e.g. B.Tech
    percentage: float | None = None    # last exam %
    gender: str = ""


@dataclass
class MatchResult:
    scheme: dict
    eligible: bool
    reasons_failed: list = field(default_factory=list)
    to_verify: list = field(default_factory=list)
    days_left: int | None = None


def _norm(x) -> str:
    return str(x or "").strip().lower()


def _list(v) -> list[str]:
    if not v:
        return []
    if isinstance(v, str):
        v = [v]
    return [_norm(i) for i in v if _norm(i)]


def parse_deadline(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(str(s).strip(), fmt).date()
        except ValueError:
            continue
    return None


def match(scheme: dict, p: Profile, today: date | None = None) -> MatchResult:
    today = today or date.today()
    e = scheme.get("eligibility") or {}
    failed, verify = [], []

    states = _list(e.get("states"))
    if states and "all" not in states and "all india" not in states:
        if not p.state:
            verify.append("state")
        elif _norm(p.state) not in states:
            failed.append(f"Only for: {', '.join(states)}")

    cats = _list(e.get("categories"))
    if cats and "all" not in cats:
        if not p.category:
            verify.append("category")
        elif _norm(p.category) not in cats:
            failed.append(f"Category must be one of: {', '.join(cats)}")

    courses = _list(e.get("courses"))
    if courses and "all" not in courses:
        if not p.course:
            verify.append("course")
        elif not any(c in _norm(p.course) or _norm(p.course) in c for c in courses):
            failed.append(f"Course must be one of: {', '.join(courses)}")

    max_inc = e.get("max_income")
    if max_inc:
        if p.annual_income is None:
            verify.append("income")
        elif p.annual_income > max_inc:
            failed.append(f"Family income above limit (INR {max_inc:,})")

    min_pct = e.get("min_percentage")
    if min_pct:
        if p.percentage is None:
            verify.append("percentage")
        elif p.percentage < min_pct:
            failed.append(f"Needs at least {min_pct}%")

    g = _norm(e.get("gender"))
    if g and g not in ("all", "any"):
        if not p.gender:
            verify.append("gender")
        elif _norm(p.gender) != g:
            failed.append(f"Open to {g} applicants only")

    dl = parse_deadline(scheme.get("deadline"))
    days_left = (dl - today).days if dl else None
    if days_left is not None and days_left < 0:
        failed.append("Deadline passed")

    return MatchResult(scheme, not failed, failed, verify, days_left)


def rank(schemes: list[dict], p: Profile, today: date | None = None) -> list[MatchResult]:
    ok = [r for r in (match(s, p, today) for s in schemes) if r.eligible]
    # soonest deadline first; unknown deadlines last
    ok.sort(key=lambda r: (r.days_left is None, r.days_left if r.days_left is not None else 0))
    return ok
