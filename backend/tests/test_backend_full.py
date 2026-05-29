"""Comprehensive backend tests for StartupInternships.in"""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://internship-hub-63.preview.emergentagent.com").rstrip("/")


# -------------------- PUBLIC --------------------
class TestPublic:
    def test_health(self):
        r = requests.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True

    def test_stats(self):
        r = requests.get(f"{BASE_URL}/api/public/stats", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["verified_startups", "students_registered", "partner_institutions", "live_internships"]:
            assert k in d
        assert d["verified_startups"] >= 1
        assert d["students_registered"] >= 1

    def test_public_internships(self):
        r = requests.get(f"{BASE_URL}/api/public/internships?limit=9", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, list)
        assert len(d) <= 9
        if d:
            assert "title" in d[0]
            assert "startup" in d[0]

    def test_public_institutions(self):
        r = requests.get(f"{BASE_URL}/api/public/institutions", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# -------------------- AUTH --------------------
class TestAuth:
    def test_admin_login(self, admin_session):
        s, u = admin_session
        assert u["role"] == "admin"
        # cookies
        cookies = {c.name for c in s.cookies}
        assert "access_token" in cookies
        assert "refresh_token" in cookies

    def test_student_login(self, student_session):
        _, u = student_session
        assert u["role"] == "student"

    def test_startup_login(self, startup_session):
        _, u = startup_session
        assert u["role"] == "startup"
        assert u["is_verified"] is True

    def test_institution_login(self, institution_session):
        _, u = institution_session
        assert u["role"] == "institution"

    def test_login_invalid(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "noone@demo.com", "password": "wrong"}, timeout=15)
        assert r.status_code == 401

    def test_auth_me_unauthenticated(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 401

    def test_auth_me_authenticated(self, student_session):
        s, _ = student_session
        r = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["user"]["role"] == "student"
        assert d["profile"] is not None

    def test_refresh(self, student_session):
        s, _ = student_session
        r = s.post(f"{BASE_URL}/api/auth/refresh", timeout=15)
        assert r.status_code == 200

    def test_register_weak_password(self):
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"TEST_weak_{uuid.uuid4().hex[:6]}@test.com",
            "password": "weakpass",
            "name": "Weak User",
            "role": "student",
        }, timeout=15)
        assert r.status_code == 400

    def test_register_duplicate(self):
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": "student1@demo.startupinternships.in",
            "password": "Strong@2025",
            "name": "Dup",
            "role": "student",
        }, timeout=15)
        assert r.status_code == 400


# -------------------- INTERNSHIPS --------------------
class TestInternships:
    def test_list(self):
        r = requests.get(f"{BASE_URL}/api/internships", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "total" in d
        assert d["total"] >= 1

    def test_list_with_filters(self):
        r = requests.get(f"{BASE_URL}/api/internships?work_mode=remote", timeout=15)
        assert r.status_code == 200

    def test_list_search(self):
        r = requests.get(f"{BASE_URL}/api/internships?q=engineer", timeout=15)
        assert r.status_code == 200

    def test_get_single(self):
        r = requests.get(f"{BASE_URL}/api/internships", timeout=15)
        lid = r.json()["items"][0]["id"]
        r2 = requests.get(f"{BASE_URL}/api/internships/{lid}", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["id"] == lid

    def test_get_nonexistent(self):
        r = requests.get(f"{BASE_URL}/api/internships/nonexistent-id", timeout=15)
        assert r.status_code == 404


# -------------------- STUDENT FLOW --------------------
class TestStudent:
    def test_recommendations(self, student_session):
        s, _ = student_session
        r = s.get(f"{BASE_URL}/api/student/recommendations", timeout=20)
        assert r.status_code == 200
        recs = r.json()
        assert isinstance(recs, list)
        if recs:
            r0 = recs[0]
            assert "match_score" in r0
            assert 0 <= r0["match_score"] <= 100
            assert "match_tier" in r0

    def test_apply_and_my_applications(self, student_session):
        s, _ = student_session
        # find a listing the student hasn't applied to
        r = s.get(f"{BASE_URL}/api/internships?limit=50", timeout=15)
        listings = r.json()["items"]
        my = s.get(f"{BASE_URL}/api/applications/my", timeout=15).json()
        applied_ids = {a["listing_id"] for a in my}
        target = next((l for l in listings if l["id"] not in applied_ids), None)
        if not target:
            pytest.skip("No fresh listings to apply to")

        r2 = s.post(f"{BASE_URL}/api/applications", json={
            "listing_id": target["id"],
            "cover_message": "I'd love to join your team. TEST_APPLY",
        }, timeout=15)
        assert r2.status_code == 200, r2.text
        d = r2.json()
        assert "match_score" in d
        assert 0 <= d["match_score"] <= 100

        my2 = s.get(f"{BASE_URL}/api/applications/my", timeout=15).json()
        assert any(a["listing_id"] == target["id"] for a in my2)

    def test_apply_duplicate_rejected(self, student_session):
        s, _ = student_session
        my = s.get(f"{BASE_URL}/api/applications/my", timeout=15).json()
        if not my:
            pytest.skip("no apps to test dup with")
        existing = my[0]
        r = s.post(f"{BASE_URL}/api/applications", json={
            "listing_id": existing["listing_id"],
            "cover_message": "dup",
        }, timeout=15)
        assert r.status_code == 400


# -------------------- ROLE ACCESS --------------------
class TestRoleAccess:
    def test_student_cannot_post_internship(self, student_session):
        s, _ = student_session
        r = s.post(f"{BASE_URL}/api/internships", json={
            "title": "Bad", "department": "Engineering", "description": "x" * 50,
            "required_skills": ["x"], "work_mode": "remote", "duration_months": 3,
            "compensation_type": "fixed", "stipend_amount": 1000,
        }, timeout=15)
        assert r.status_code == 403

    def test_startup_cannot_apply(self, startup_session):
        s, _ = startup_session
        r = s.post(f"{BASE_URL}/api/applications", json={"listing_id": "x", "cover_message": "y"}, timeout=15)
        assert r.status_code == 403

    def test_student_cannot_access_admin(self, student_session):
        s, _ = student_session
        r = s.get(f"{BASE_URL}/api/admin/analytics", timeout=15)
        assert r.status_code == 403


# -------------------- STARTUP FLOW --------------------
class TestStartup:
    def test_dashboard(self, startup_session):
        s, _ = startup_session
        r = s.get(f"{BASE_URL}/api/startup/dashboard", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["listings", "applications", "shortlisted", "hired"]:
            assert k in d

    def test_listings(self, startup_session):
        s, _ = startup_session
        r = s.get(f"{BASE_URL}/api/startup/listings", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_candidates(self, startup_session):
        s, _ = startup_session
        r = s.get(f"{BASE_URL}/api/startup/candidates", timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_listing(self, startup_session):
        s, _ = startup_session
        r = s.post(f"{BASE_URL}/api/internships", json={
            "title": "TEST_QA Intern",
            "department": "Engineering",
            "description": "Quality assurance testing role. We're looking for a detail-oriented intern.",
            "required_skills": ["Python", "Testing"],
            "preferred_qualifications": "Selenium experience",
            "work_mode": "remote",
            "city": "Chennai",
            "duration_start": "2026-02-01",
            "duration_end": "2026-05-01",
            "application_deadline": "2026-01-25",
            "compensation_type": "fixed",
            "stipend_fixed_amount": 15000,
        }, timeout=20)
        assert r.status_code == 200, r.text
        lid = r.json()["id"]
        # verify
        r2 = requests.get(f"{BASE_URL}/api/internships/{lid}", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["title"] == "TEST_QA Intern"

    def test_pipeline_status_update(self, startup_session, student_session):
        s_startup, _ = startup_session
        # Get candidates from startup1
        cands = s_startup.get(f"{BASE_URL}/api/startup/candidates", timeout=20).json()
        if not cands:
            pytest.skip("No candidates yet for startup1")
        app = cands[0]
        r = s_startup.patch(f"{BASE_URL}/api/applications/{app['id']}/status", json={"status": "shortlisted", "note": "TEST"}, timeout=15)
        assert r.status_code == 200


# -------------------- INSTITUTION --------------------
class TestInstitution:
    def test_students(self, institution_session):
        s, _ = institution_session
        r = s.get(f"{BASE_URL}/api/institution/students", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_analytics(self, institution_session):
        s, _ = institution_session
        r = s.get(f"{BASE_URL}/api/institution/analytics", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["total_students", "active", "placed", "by_domain"]:
            assert k in d


# -------------------- ADMIN --------------------
class TestAdmin:
    def test_analytics(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/admin/analytics", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["users", "students", "startups", "verified_startups", "live_listings"]:
            assert k in d

    def test_pending_startups(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/admin/verifications/startups", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_pending_institutions(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/admin/verifications/institutions", timeout=15)
        assert r.status_code == 200

    def test_users_list(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/admin/users", timeout=15)
        assert r.status_code == 200
        assert len(r.json()) > 0

    def test_listings_list(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/admin/listings", timeout=15)
        assert r.status_code == 200

    def test_register_and_approve_startup(self, admin_session):
        email = f"test_newstartup_{uuid.uuid4().hex[:6]}@test.com"
        reg = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "Strong@2025",
            "name": "TEST New Startup",
            "role": "startup",
        }, timeout=15)
        assert reg.status_code == 201, reg.text

        s, _ = admin_session
        pending = s.get(f"{BASE_URL}/api/admin/verifications/startups", timeout=15).json()
        target = next((p for p in pending if p.get("user", {}).get("email", "").lower() == email.lower()), None)
        assert target is not None, f"Newly registered startup not in pending queue. Pending emails: {[p.get('user',{}).get('email') for p in pending]}"

        r = s.post(f"{BASE_URL}/api/admin/verifications/startups/{target['id']}", json={"approve": True}, timeout=15)
        assert r.status_code == 200

        # verify it's now verified
        pending2 = s.get(f"{BASE_URL}/api/admin/verifications/startups", timeout=15).json()
        assert not any(p.get("user", {}).get("email", "").lower() == email.lower() for p in pending2)


# -------------------- NOTIFICATIONS --------------------
class TestNotifications:
    def test_list(self, student_session):
        s, _ = student_session
        r = s.get(f"{BASE_URL}/api/notifications", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_read_all(self, student_session):
        s, _ = student_session
        r = s.post(f"{BASE_URL}/api/notifications/read-all", timeout=15)
        assert r.status_code == 200


# -------------------- PROFILE --------------------
class TestProfile:
    def test_student_update(self, student_session):
        s, _ = student_session
        r = s.patch(f"{BASE_URL}/api/profile/student", json={"phone": "+91 9999999999"}, timeout=15)
        assert r.status_code == 200
        assert "profile_completion_score" in r.json()

    def test_startup_update(self, startup_session):
        s, _ = startup_session
        r = s.patch(f"{BASE_URL}/api/profile/startup", json={"tagline": "TEST tagline"}, timeout=15)
        assert r.status_code == 200

    def test_institution_update(self, institution_session):
        s, _ = institution_session
        r = s.patch(f"{BASE_URL}/api/profile/institution", json={"website": "https://test.example.com"}, timeout=15)
        assert r.status_code == 200


# -------------------- MATCH SCORE --------------------
class TestMatchScore:
    def test_score_tiers(self, student_session):
        s, _ = student_session
        r = s.get(f"{BASE_URL}/api/student/recommendations", timeout=20)
        assert r.status_code == 200
        recs = r.json()
        for rec in recs:
            score = rec["match_score"]
            tier = rec["match_tier"]
            assert 0 <= score <= 100
            if score >= 85:
                assert tier == "strong"
            elif score >= 65:
                assert tier == "good"
            elif score >= 45:
                assert tier == "partial"
            else:
                assert tier == "low"
