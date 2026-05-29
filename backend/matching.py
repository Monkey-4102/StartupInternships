"""Smart match score calculation engine (MVP - rule-based).

Weights:
- Skills overlap         35%
- Domain interest match  25%
- Availability match     20%
- Work mode match        10%
- Compensation match     10%
"""
from datetime import date, datetime
from typing import Optional


def _parse_date(d) -> Optional[date]:
    if not d:
        return None
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    try:
        return datetime.fromisoformat(str(d).replace("Z", "+00:00")).date()
    except Exception:
        try:
            return datetime.strptime(str(d)[:10], "%Y-%m-%d").date()
        except Exception:
            return None


def _skill_overlap(student_skills, required_skills) -> float:
    s = {x.lower().strip() for x in (student_skills or []) if x}
    r = {x.lower().strip() for x in (required_skills or []) if x}
    if not r:
        return 0.5
    inter = s & r
    return min(1.0, len(inter) / len(r))


def _domain_match(student_domains, listing_department) -> float:
    if not listing_department or not student_domains:
        return 0.0
    dept = listing_department.lower().strip()
    for d in student_domains:
        if not d:
            continue
        d2 = d.lower().strip()
        if d2 == dept or d2 in dept or dept in d2:
            return 1.0
    return 0.0


def _availability_match(student_avail, listing_start) -> float:
    s = _parse_date(student_avail)
    l = _parse_date(listing_start)
    if not s or not l:
        return 0.5
    diff = abs((l - s).days)
    if diff <= 14:
        return 1.0
    if diff <= 30:
        return 0.7
    if diff <= 60:
        return 0.4
    return 0.1


def _work_mode_match(pref, mode) -> float:
    if not pref or pref == "any":
        return 1.0
    return 1.0 if pref == mode else 0.3


def _comp_match(pref, comp_type, listing_min, listing_max, expected_min, expected_max) -> float:
    if not pref or pref == "any":
        return 1.0
    if pref == "paid":
        if comp_type == "unpaid":
            return 0.0
        if expected_min is not None and listing_max is not None and listing_max < expected_min:
            return 0.4
        return 1.0
    if pref == "unpaid":
        return 1.0
    return 0.7


def calculate_match_score(student: dict, listing: dict) -> int:
    """Return a 0-100 integer match score."""
    if not student or not listing:
        return 0
    skills = _skill_overlap(student.get("skills"), listing.get("required_skills")) * 35
    domain = _domain_match(student.get("domain_interests"), listing.get("department")) * 25
    avail = _availability_match(student.get("availability_date"), listing.get("duration_start")) * 20
    mode = _work_mode_match(student.get("work_mode_preference"), listing.get("work_mode")) * 10
    comp = _comp_match(
        student.get("compensation_preference"),
        listing.get("compensation_type"),
        listing.get("stipend_min") or listing.get("stipend_fixed_amount"),
        listing.get("stipend_max") or listing.get("stipend_fixed_amount"),
        student.get("expected_stipend_min"),
        student.get("expected_stipend_max"),
    ) * 10
    total = skills + domain + avail + mode + comp
    return int(round(total))


def match_tier(score: int) -> str:
    if score >= 85:
        return "strong"
    if score >= 65:
        return "good"
    if score >= 45:
        return "partial"
    return "low"
