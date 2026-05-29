"""Pydantic models for the StartupInternships platform."""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime, timezone, date
import uuid


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


# ============================== AUTH ==============================
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["student", "startup", "institution"]
    name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: str
    email: str
    role: str
    name: str
    is_verified: bool = False
    profile_id: Optional[str] = None
    created_at: str


# ============================== STUDENT PROFILE ==============================
class StudentProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    full_name: Optional[str] = None
    phone: Optional[str] = None
    college_name: Optional[str] = None
    degree: Optional[str] = None
    branch: Optional[str] = None
    year_of_study: Optional[int] = Field(default=None, ge=1, le=6)
    graduation_year: Optional[int] = None
    cgpa: Optional[float] = None
    bio: Optional[str] = Field(default=None, max_length=280)
    resume_url: Optional[str] = None
    profile_photo_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    skills: Optional[List[str]] = None
    domain_interests: Optional[List[str]] = None
    availability_date: Optional[str] = None
    is_available: Optional[bool] = None
    preferred_duration: Optional[str] = None
    work_mode_preference: Optional[Literal["remote", "onsite", "hybrid", "any"]] = None
    compensation_preference: Optional[Literal["paid", "unpaid", "any"]] = None
    expected_stipend_min: Optional[int] = None
    expected_stipend_max: Optional[int] = None
    preferred_cities: Optional[List[str]] = None
    open_to_relocation: Optional[bool] = None


# ============================== STARTUP PROFILE ==============================
class StartupProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    company_name: Optional[str] = None
    registered_name: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    cin_number: Optional[str] = None
    dpiit_number: Optional[str] = None
    founding_year: Optional[int] = None
    company_stage: Optional[Literal["idea", "pre-seed", "seed", "series-a", "series-b-plus"]] = None
    team_size_range: Optional[str] = None
    primary_domain: Optional[str] = None
    description: Optional[str] = None
    cities: Optional[List[str]] = None
    total_funding: Optional[int] = None


# ============================== INSTITUTION PROFILE ==============================
class InstitutionProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = None
    type: Optional[Literal["engineering", "mba", "arts", "polytechnic", "university", "deemed", "other"]] = None
    affiliation: Optional[str] = None
    naac_grade: Optional[str] = None
    aicte_approval_number: Optional[str] = None
    placement_head_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website_url: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    student_count: Optional[int] = None
    logo_url: Optional[str] = None


# ============================== INTERNSHIP ==============================
class InternshipCreate(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    department: str
    description: str
    required_skills: List[str] = []
    preferred_qualifications: Optional[str] = None
    openings: int = Field(default=1, ge=1, le=50)
    work_mode: Literal["remote", "onsite", "hybrid"]
    city: Optional[str] = None
    duration_start: str  # ISO date
    duration_end: str
    application_deadline: str
    compensation_type: Literal["fixed", "performance", "unpaid", "hybrid"]
    stipend_fixed_amount: Optional[int] = None
    stipend_min: Optional[int] = None
    stipend_max: Optional[int] = None
    stipend_conditions: Optional[str] = None
    unpaid_learning_outcomes: Optional[str] = None
    perks: Optional[str] = None


class InternshipUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[List[str]] = None
    openings: Optional[int] = None
    application_deadline: Optional[str] = None
    status: Optional[Literal["draft", "live", "paused", "closed", "expired"]] = None


# ============================== APPLICATIONS ==============================
class ApplicationCreate(BaseModel):
    listing_id: str
    cover_message: Optional[str] = Field(default=None, max_length=300)


class ApplicationStatusUpdate(BaseModel):
    status: Literal[
        "applied", "under_review", "shortlisted", "interview_scheduled",
        "offered", "accepted", "rejected", "withdrawn"
    ]
    note: Optional[str] = None


class ApplicationOfferResponse(BaseModel):
    accept: bool


class ApplicationRating(BaseModel):
    rating: int = Field(ge=1, le=5)
    notes: Optional[str] = None


# ============================== INTERVIEW ==============================
class InterviewCreate(BaseModel):
    application_id: str
    proposed_slots: List[dict]  # [{date, time, timezone}]
    mode: Literal["video", "phone", "in_person"]
    video_link: Optional[str] = None
    location: Optional[str] = None
    interviewer_name: str


class InterviewConfirm(BaseModel):
    slot: dict  # {date, time, timezone}


# ============================== ADMIN ==============================
class VerificationDecision(BaseModel):
    approve: bool
    reason: Optional[str] = None


# ============================== UTILS ==============================
def clean_doc(doc: dict) -> dict:
    if doc is None:
        return doc
    doc.pop("_id", None)
    return doc
