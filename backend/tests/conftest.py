import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://internship-hub-63.preview.emergentagent.com").rstrip("/")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return s, r.json()


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def admin_session():
    s, u = _login("admin@startupinternships.in", "Admin@2025")
    return s, u


@pytest.fixture(scope="session")
def student_session():
    s, u = _login("student1@demo.startupinternships.in", "Demo@2025")
    return s, u


@pytest.fixture(scope="session")
def startup_session():
    s, u = _login("startup1@demo.startupinternships.in", "Demo@2025")
    return s, u


@pytest.fixture(scope="session")
def institution_session():
    s, u = _login("inst1@demo.startupinternships.in", "Demo@2025")
    return s, u
