"""StartupInternships.in — Main FastAPI application."""
from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, Query, status
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    set_auth_cookies, clear_auth_cookies, decode_token,
    get_current_user, require_role,
)
from models import (
    RegisterRequest, LoginRequest, UserPublic,
    StudentProfileUpdate, StartupProfileUpdate, InstitutionProfileUpdate,
    InternshipCreate, InternshipUpdate,
    ApplicationCreate, ApplicationStatusUpdate, ApplicationOfferResponse, ApplicationRating,
    InterviewCreate, InterviewConfirm,
    VerificationDecision,
    new_id, now_utc_iso, clean_doc,
)
from matching import calculate_match_score, match_tier
from seed_data import seed_admin, seed_demo_data

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# ============================== DB ==============================
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

# ============================== APP ==============================
app = FastAPI(title="StartupInternships.in API", version="1.0.0")
api = APIRouter(prefix="/api")


# ============================== STARTUP ==============================
@app.on_event("startup")
async def on_startup():
    # Indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("role")
    await db.student_profiles.create_index("user_id", unique=True)
    await db.startup_profiles.create_index("user_id", unique=True)
    await db.institution_profiles.create_index("user_id", unique=True)
    await db.internship_listings.create_index([("status", 1), ("created_at", -1)])
    await db.internship_listings.create_index("startup_id")
    await db.applications.create_index([("student_id", 1), ("listing_id", 1)], unique=True)
    await db.applications.create_index("listing_id")
    await db.applications.create_index("status")
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    await db.notifications.create_index("is_read")
    await db.interview_schedules.create_index("application_id")
    await db.login_attempts.create_index("identifier")

    await seed_admin(db)
    await seed_demo_data(db)
    logger.info("Startup complete: indexes created, admin + demo data seeded.")


@app.on_event("shutdown")
async def on_shutdown():
    client.close()


# ============================== HELPERS ==============================
async def _notify(user_id: str, ntype: str, title: str, body: str, link: Optional[str] = None):
    await db.notifications.insert_one({
        "id": new_id(), "user_id": user_id, "type": ntype,
        "title": title, "body": body, "link": link,
        "is_read": False, "created_at": now_utc_iso(),
    })


async def _get_profile(user: dict):
    """Return the profile doc associated with the given user."""
    role = user["role"]
    coll = {
        "student": db.student_profiles,
        "startup": db.startup_profiles,
        "institution": db.institution_profiles,
    }.get(role)
    if coll is None:
        return None
    return await coll.find_one({"user_id": user["id"]}, {"_id": 0})


# ============================== AUTH ROUTES ==============================
@api.post("/auth/register", status_code=201)
async def register(payload: RegisterRequest, response: Response):
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Password strength check
    pw = payload.password
    if len(pw) < 8 or not any(c.isupper() for c in pw) or not any(c.isdigit() for c in pw) or not any(not c.isalnum() for c in pw):
        raise HTTPException(status_code=400, detail="Password must be 8+ chars with 1 uppercase, 1 number, 1 special char.")

    uid = new_id()
    pid = new_id()
    now = now_utc_iso()

    user_doc = {
        "id": uid, "email": email, "password_hash": hash_password(pw),
        "name": payload.name, "role": payload.role,
        "is_verified": payload.role == "student",  # Students auto-verified; startups/institutions need admin approval
        "profile_id": pid,
        "created_at": now,
    }
    await db.users.insert_one(user_doc)

    # Create blank profile
    base = {"id": pid, "user_id": uid, "created_at": now, "updated_at": now}
    if payload.role == "student":
        await db.student_profiles.insert_one({
            **base, "full_name": payload.name, "skills": [], "domain_interests": [],
            "is_available": True, "profile_completion_score": 20,
        })
    elif payload.role == "startup":
        await db.startup_profiles.insert_one({
            **base, "company_name": payload.name,
            "is_verified": False, "verification_status": "pending",
        })
    elif payload.role == "institution":
        await db.institution_profiles.insert_one({
            **base, "name": payload.name,
            "is_verified": False, "verification_status": "pending", "state": "Tamil Nadu",
        })

    at = create_access_token(uid, email, payload.role)
    rt = create_refresh_token(uid)
    set_auth_cookies(response, at, rt)

    await _notify(uid, "welcome", "Welcome to StartupInternships.in",
                  f"Your {payload.role} account is ready. Complete your profile to get started.")

    return {
        "id": uid, "email": email, "role": payload.role, "name": payload.name,
        "is_verified": user_doc["is_verified"], "profile_id": pid, "created_at": now,
    }


@api.post("/auth/login")
async def login(payload: LoginRequest, response: Response, request: Request):
    email = payload.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"

    # Brute force check
    attempt_doc = await db.login_attempts.find_one({"identifier": identifier})
    if attempt_doc and attempt_doc.get("count", 0) >= 5:
        locked_until = attempt_doc.get("locked_until")
        if locked_until and datetime.fromisoformat(locked_until) > datetime.now(timezone.utc):
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes.")

    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        # increment attempts
        from datetime import timedelta
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {"$inc": {"count": 1}, "$set": {"locked_until": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()}},
            upsert=True,
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await db.login_attempts.delete_one({"identifier": identifier})
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login_at": now_utc_iso()}})

    at = create_access_token(user["id"], user["email"], user["role"])
    rt = create_refresh_token(user["id"])
    set_auth_cookies(response, at, rt)

    return {
        "id": user["id"], "email": user["email"], "role": user["role"],
        "name": user.get("name"), "is_verified": user.get("is_verified", False),
        "profile_id": user.get("profile_id"),
    }


@api.post("/auth/logout")
async def logout(response: Response, _user: dict = Depends(get_current_user)):
    clear_auth_cookies(response)
    return {"ok": True}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    profile = await _get_profile(user)
    return {"user": user, "profile": profile}


@api.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = await db.users.find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    at = create_access_token(user["id"], user["email"], user["role"])
    rt = create_refresh_token(user["id"])
    set_auth_cookies(response, at, rt)
    return {"ok": True}


# ============================== PUBLIC ROUTES ==============================
@api.get("/public/stats")
async def public_stats():
    startups = await db.startup_profiles.count_documents({"is_verified": True})
    students = await db.student_profiles.count_documents({})
    institutions = await db.institution_profiles.count_documents({"is_verified": True})
    listings = await db.internship_listings.count_documents({"status": "live"})
    placements = await db.applications.count_documents({"status": {"$in": ["accepted", "offered"]}})
    return {
        "verified_startups": startups,
        "students_registered": students,
        "partner_institutions": institutions,
        "live_internships": listings,
        "placements": placements,
    }


@api.get("/public/internships")
async def public_internships(limit: int = 9):
    """Featured live internships for landing page."""
    cursor = db.internship_listings.find(
        {"status": "live"},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit)
    listings = await cursor.to_list(length=limit)
    # Attach startup info
    for l in listings:
        s = await db.startup_profiles.find_one(
            {"id": l["startup_id"]}, {"_id": 0, "company_name": 1, "logo_url": 1, "primary_domain": 1, "is_verified": 1}
        )
        l["startup"] = s
    return listings


@api.get("/public/institutions")
async def public_institutions(limit: int = 20):
    cursor = db.institution_profiles.find(
        {"is_verified": True},
        {"_id": 0, "id": 1, "name": 1, "city": 1, "logo_url": 1, "type": 1, "naac_grade": 1}
    ).limit(limit)
    return await cursor.to_list(length=limit)


# ============================== INTERNSHIPS ==============================
@api.get("/internships")
async def list_internships(
    q: Optional[str] = None,
    domain: Optional[str] = None,
    work_mode: Optional[str] = None,
    compensation_type: Optional[str] = None,
    city: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    filt = {"status": "live"}
    if domain:
        filt["department"] = domain
    if work_mode:
        filt["work_mode"] = work_mode
    if compensation_type:
        filt["compensation_type"] = compensation_type
    if city:
        filt["city"] = city
    if q:
        filt["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"required_skills": {"$elemMatch": {"$regex": q, "$options": "i"}}},
        ]
    cursor = db.internship_listings.find(filt, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    listings = await cursor.to_list(length=limit)
    for l in listings:
        s = await db.startup_profiles.find_one(
            {"id": l["startup_id"]},
            {"_id": 0, "company_name": 1, "logo_url": 1, "primary_domain": 1, "is_verified": 1, "city": 1, "cities": 1}
        )
        l["startup"] = s
    return {"items": listings, "total": await db.internship_listings.count_documents(filt)}


@api.get("/internships/{listing_id}")
async def get_internship(listing_id: str):
    l = await db.internship_listings.find_one({"id": listing_id}, {"_id": 0})
    if not l:
        raise HTTPException(status_code=404, detail="Listing not found")
    s = await db.startup_profiles.find_one({"id": l["startup_id"]}, {"_id": 0})
    l["startup"] = s
    await db.internship_listings.update_one({"id": listing_id}, {"$inc": {"views_count": 1}})
    return l


@api.post("/internships")
async def create_internship(payload: InternshipCreate, user: dict = Depends(require_role("startup"))):
    if not user.get("is_verified"):
        raise HTTPException(status_code=403, detail="Your startup is pending verification. You cannot post listings yet.")
    sp = await db.startup_profiles.find_one({"user_id": user["id"]})
    if not sp:
        raise HTTPException(status_code=400, detail="Complete your company profile first")

    lid = new_id()
    doc = payload.model_dump()
    doc.update({
        "id": lid, "startup_id": sp["id"], "status": "live",
        "applications_count": 0, "views_count": 0, "is_featured": False,
        "created_at": now_utc_iso(), "updated_at": now_utc_iso(),
    })
    await db.internship_listings.insert_one(doc)
    return {"id": lid}


@api.put("/internships/{listing_id}")
async def update_internship(listing_id: str, payload: InternshipUpdate, user: dict = Depends(require_role("startup"))):
    sp = await db.startup_profiles.find_one({"user_id": user["id"]})
    listing = await db.internship_listings.find_one({"id": listing_id})
    if not listing or listing["startup_id"] != sp["id"]:
        raise HTTPException(status_code=404, detail="Listing not found")
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    update["updated_at"] = now_utc_iso()
    await db.internship_listings.update_one({"id": listing_id}, {"$set": update})
    return {"ok": True}


@api.delete("/internships/{listing_id}")
async def delete_internship(listing_id: str, user: dict = Depends(require_role("startup", "admin"))):
    if user["role"] == "startup":
        sp = await db.startup_profiles.find_one({"user_id": user["id"]})
        listing = await db.internship_listings.find_one({"id": listing_id})
        if not listing or listing["startup_id"] != sp["id"]:
            raise HTTPException(status_code=404, detail="Listing not found")
    await db.internship_listings.delete_one({"id": listing_id})
    return {"ok": True}


@api.get("/internships/{listing_id}/applicants")
async def list_applicants(listing_id: str, user: dict = Depends(require_role("startup", "admin"))):
    if user["role"] == "startup":
        sp = await db.startup_profiles.find_one({"user_id": user["id"]})
        listing = await db.internship_listings.find_one({"id": listing_id})
        if not listing or listing["startup_id"] != sp["id"]:
            raise HTTPException(status_code=404, detail="Listing not found")
    apps = await db.applications.find({"listing_id": listing_id}, {"_id": 0}).to_list(length=500)
    for a in apps:
        sp = await db.student_profiles.find_one({"id": a["student_id"]}, {"_id": 0})
        a["student"] = sp
    return apps


# Listings owned by current startup
@api.get("/startup/listings")
async def startup_listings(user: dict = Depends(require_role("startup"))):
    sp = await db.startup_profiles.find_one({"user_id": user["id"]})
    if not sp:
        return []
    cursor = db.internship_listings.find({"startup_id": sp["id"]}, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(length=200)


# ============================== APPLICATIONS ==============================
@api.post("/applications")
async def apply(payload: ApplicationCreate, user: dict = Depends(require_role("student"))):
    sp = await db.student_profiles.find_one({"user_id": user["id"]})
    if not sp:
        raise HTTPException(status_code=400, detail="Complete your student profile first")
    listing = await db.internship_listings.find_one({"id": payload.listing_id})
    if not listing or listing.get("status") != "live":
        raise HTTPException(status_code=404, detail="Listing not available")

    existing = await db.applications.find_one({"listing_id": payload.listing_id, "student_id": sp["id"]})
    if existing:
        raise HTTPException(status_code=400, detail="You've already applied to this listing")

    score = calculate_match_score(sp, listing)
    aid = new_id()
    await db.applications.insert_one({
        "id": aid, "listing_id": payload.listing_id, "student_id": sp["id"],
        "student_user_id": user["id"],
        "cover_message": payload.cover_message,
        "resume_url_at_apply": sp.get("resume_url"),
        "status": "applied", "match_score": score,
        "created_at": now_utc_iso(), "updated_at": now_utc_iso(),
    })
    await db.internship_listings.update_one({"id": payload.listing_id}, {"$inc": {"applications_count": 1}})

    # notify startup
    startup = await db.startup_profiles.find_one({"id": listing["startup_id"]})
    if startup:
        await _notify(
            startup["user_id"], "new_application",
            f"New application: {listing['title']}",
            f"{sp.get('full_name', 'A student')} applied to your {listing['title']} listing.",
            link=f"/startup/candidates?listing={listing['id']}",
        )
    return {"id": aid, "match_score": score}


@api.get("/applications/my")
async def my_applications(user: dict = Depends(require_role("student"))):
    sp = await db.student_profiles.find_one({"user_id": user["id"]})
    if not sp:
        return []
    apps = await db.applications.find({"student_id": sp["id"]}, {"_id": 0}).sort("created_at", -1).to_list(length=500)
    for a in apps:
        l = await db.internship_listings.find_one({"id": a["listing_id"]}, {"_id": 0})
        if l:
            startup = await db.startup_profiles.find_one(
                {"id": l["startup_id"]},
                {"_id": 0, "company_name": 1, "logo_url": 1, "primary_domain": 1, "is_verified": 1}
            )
            l["startup"] = startup
        a["listing"] = l
    return apps


@api.patch("/applications/{app_id}/withdraw")
async def withdraw(app_id: str, user: dict = Depends(require_role("student"))):
    sp = await db.student_profiles.find_one({"user_id": user["id"]})
    a = await db.applications.find_one({"id": app_id})
    if not a or a["student_id"] != sp["id"]:
        raise HTTPException(status_code=404, detail="Application not found")
    if a["status"] in ("interview_scheduled", "offered", "accepted"):
        raise HTTPException(status_code=400, detail="Cannot withdraw at this stage")
    await db.applications.update_one({"id": app_id}, {"$set": {"status": "withdrawn", "updated_at": now_utc_iso()}})
    return {"ok": True}


@api.patch("/applications/{app_id}/status")
async def update_app_status(app_id: str, payload: ApplicationStatusUpdate, user: dict = Depends(require_role("startup"))):
    sp = await db.startup_profiles.find_one({"user_id": user["id"]})
    a = await db.applications.find_one({"id": app_id})
    if not a:
        raise HTTPException(status_code=404, detail="Application not found")
    l = await db.internship_listings.find_one({"id": a["listing_id"]})
    if not l or l["startup_id"] != sp["id"]:
        raise HTTPException(status_code=403, detail="Not your listing")

    await db.applications.update_one(
        {"id": app_id},
        {"$set": {"status": payload.status, "updated_at": now_utc_iso()},
         "$push": {"history": {"status": payload.status, "note": payload.note, "at": now_utc_iso()}}}
    )

    # Notify student
    notif_map = {
        "shortlisted": ("You've been shortlisted!", f"You've been shortlisted for {l['title']}. Stay tuned for next steps."),
        "interview_scheduled": ("Interview scheduled", f"An interview has been set for {l['title']}."),
        "offered": ("Offer received", f"You've received an offer for {l['title']}!"),
        "rejected": ("Application update", f"Your application for {l['title']} was not selected this time."),
        "under_review": ("Application in review", f"Your application for {l['title']} is being reviewed."),
    }
    if payload.status in notif_map:
        title, body = notif_map[payload.status]
        await _notify(a["student_user_id"], f"app_{payload.status}", title, body, link="/student/applications")

    return {"ok": True}


@api.patch("/applications/{app_id}/rating")
async def rate(app_id: str, payload: ApplicationRating, user: dict = Depends(require_role("startup"))):
    sp = await db.startup_profiles.find_one({"user_id": user["id"]})
    a = await db.applications.find_one({"id": app_id})
    if not a:
        raise HTTPException(status_code=404, detail="Application not found")
    l = await db.internship_listings.find_one({"id": a["listing_id"]})
    if not l or l["startup_id"] != sp["id"]:
        raise HTTPException(status_code=403, detail="Not your listing")
    await db.applications.update_one(
        {"id": app_id},
        {"$set": {"startup_rating": payload.rating, "startup_notes": payload.notes, "updated_at": now_utc_iso()}}
    )
    return {"ok": True}


@api.patch("/applications/{app_id}/offer-response")
async def respond_offer(app_id: str, payload: ApplicationOfferResponse, user: dict = Depends(require_role("student"))):
    sp = await db.student_profiles.find_one({"user_id": user["id"]})
    a = await db.applications.find_one({"id": app_id})
    if not a or a["student_id"] != sp["id"]:
        raise HTTPException(status_code=404, detail="Application not found")
    if a["status"] != "offered":
        raise HTTPException(status_code=400, detail="No active offer")
    new_status = "accepted" if payload.accept else "rejected"
    await db.applications.update_one(
        {"id": app_id}, {"$set": {"status": new_status, "updated_at": now_utc_iso()}}
    )
    # notify startup
    l = await db.internship_listings.find_one({"id": a["listing_id"]})
    if l:
        startup = await db.startup_profiles.find_one({"id": l["startup_id"]})
        if startup:
            verb = "accepted" if payload.accept else "declined"
            await _notify(
                startup["user_id"], f"offer_{new_status}",
                f"Offer {verb}",
                f"{sp.get('full_name', 'A student')} {verb} your offer for {l['title']}.",
                link="/startup/candidates",
            )
    return {"ok": True}


# ============================== PROFILES ==============================
@api.patch("/profile/student")
async def update_student(payload: StudentProfileUpdate, user: dict = Depends(require_role("student"))):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    update["updated_at"] = now_utc_iso()
    # Calc completion score
    required_fields = ["full_name", "phone", "college_name", "degree", "branch",
                       "skills", "domain_interests", "availability_date", "work_mode_preference"]
    sp = await db.student_profiles.find_one({"user_id": user["id"]})
    merged = {**(sp or {}), **update}
    filled = sum(1 for f in required_fields if merged.get(f))
    update["profile_completion_score"] = int((filled / len(required_fields)) * 100)
    await db.student_profiles.update_one({"user_id": user["id"]}, {"$set": update})
    return {"ok": True, "profile_completion_score": update["profile_completion_score"]}


@api.patch("/profile/startup")
async def update_startup(payload: StartupProfileUpdate, user: dict = Depends(require_role("startup"))):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    update["updated_at"] = now_utc_iso()
    await db.startup_profiles.update_one({"user_id": user["id"]}, {"$set": update})
    return {"ok": True}


@api.patch("/profile/institution")
async def update_institution(payload: InstitutionProfileUpdate, user: dict = Depends(require_role("institution"))):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    update["updated_at"] = now_utc_iso()
    await db.institution_profiles.update_one({"user_id": user["id"]}, {"$set": update})
    return {"ok": True}


# ============================== INSTITUTION ROUTES ==============================
@api.get("/institution/students")
async def institution_students(user: dict = Depends(require_role("institution"))):
    ip = await db.institution_profiles.find_one({"user_id": user["id"]})
    if not ip:
        return []
    # Students by college name match
    cursor = db.student_profiles.find({"college_name": ip["name"]}, {"_id": 0}).limit(500)
    students = await cursor.to_list(length=500)
    for s in students:
        # latest app
        a = await db.applications.find_one({"student_id": s["id"]}, {"_id": 0}, sort=[("created_at", -1)])
        s["latest_application"] = a
    return students


@api.get("/institution/analytics")
async def institution_analytics(user: dict = Depends(require_role("institution"))):
    ip = await db.institution_profiles.find_one({"user_id": user["id"]})
    if not ip:
        return {"total_students": 0, "active": 0, "placed": 0, "by_domain": []}
    students = await db.student_profiles.find({"college_name": ip["name"]}).to_list(length=1000)
    sids = [s["id"] for s in students]
    total = len(students)
    active = await db.applications.count_documents({"student_id": {"$in": sids}, "status": {"$in": ["applied", "under_review", "shortlisted", "interview_scheduled"]}})
    placed = await db.applications.count_documents({"student_id": {"$in": sids}, "status": {"$in": ["offered", "accepted"]}})
    # by domain
    pipeline = [
        {"$match": {"student_id": {"$in": sids}, "status": {"$in": ["offered", "accepted"]}}},
        {"$lookup": {"from": "internship_listings", "localField": "listing_id", "foreignField": "id", "as": "listing"}},
        {"$unwind": "$listing"},
        {"$group": {"_id": "$listing.department", "count": {"$sum": 1}}},
        {"$project": {"domain": "$_id", "count": 1, "_id": 0}},
    ]
    by_domain = await db.applications.aggregate(pipeline).to_list(length=50)
    return {"total_students": total, "active": active, "placed": placed, "by_domain": by_domain}


# ============================== ADMIN ROUTES ==============================
@api.get("/admin/analytics")
async def admin_analytics(user: dict = Depends(require_role("admin"))):
    return {
        "users": await db.users.count_documents({}),
        "students": await db.users.count_documents({"role": "student"}),
        "startups": await db.startup_profiles.count_documents({}),
        "verified_startups": await db.startup_profiles.count_documents({"is_verified": True}),
        "pending_startups": await db.startup_profiles.count_documents({"verification_status": "pending"}),
        "institutions": await db.institution_profiles.count_documents({}),
        "verified_institutions": await db.institution_profiles.count_documents({"is_verified": True}),
        "pending_institutions": await db.institution_profiles.count_documents({"verification_status": "pending"}),
        "live_listings": await db.internship_listings.count_documents({"status": "live"}),
        "total_applications": await db.applications.count_documents({}),
        "placements": await db.applications.count_documents({"status": {"$in": ["offered", "accepted"]}}),
    }


@api.get("/admin/verifications/startups")
async def pending_startups(user: dict = Depends(require_role("admin"))):
    cursor = db.startup_profiles.find({"verification_status": "pending"}, {"_id": 0}).limit(200)
    items = await cursor.to_list(length=200)
    for it in items:
        u = await db.users.find_one({"id": it["user_id"]}, {"_id": 0, "password_hash": 0})
        it["user"] = u
    return items


@api.post("/admin/verifications/startups/{startup_id}")
async def verify_startup(startup_id: str, payload: VerificationDecision, user: dict = Depends(require_role("admin"))):
    sp = await db.startup_profiles.find_one({"id": startup_id})
    if not sp:
        raise HTTPException(status_code=404, detail="Not found")
    if payload.approve:
        await db.startup_profiles.update_one(
            {"id": startup_id},
            {"$set": {"is_verified": True, "verification_status": "verified",
                      "verified_at": now_utc_iso(), "verified_by": user["id"]}}
        )
        await db.users.update_one({"id": sp["user_id"]}, {"$set": {"is_verified": True}})
        await _notify(sp["user_id"], "verified", "Startup verified", "Your startup has been verified. You can now post listings.")
    else:
        await db.startup_profiles.update_one(
            {"id": startup_id},
            {"$set": {"verification_status": "rejected", "rejection_reason": payload.reason or ""}}
        )
        await _notify(sp["user_id"], "rejected", "Verification rejected", payload.reason or "Please update your details and re-submit.")
    return {"ok": True}


@api.get("/admin/verifications/institutions")
async def pending_institutions(user: dict = Depends(require_role("admin"))):
    cursor = db.institution_profiles.find({"verification_status": "pending"}, {"_id": 0}).limit(200)
    items = await cursor.to_list(length=200)
    for it in items:
        u = await db.users.find_one({"id": it["user_id"]}, {"_id": 0, "password_hash": 0})
        it["user"] = u
    return items


@api.post("/admin/verifications/institutions/{inst_id}")
async def verify_institution(inst_id: str, payload: VerificationDecision, user: dict = Depends(require_role("admin"))):
    ip = await db.institution_profiles.find_one({"id": inst_id})
    if not ip:
        raise HTTPException(status_code=404, detail="Not found")
    if payload.approve:
        await db.institution_profiles.update_one(
            {"id": inst_id},
            {"$set": {"is_verified": True, "verification_status": "verified"}}
        )
        await db.users.update_one({"id": ip["user_id"]}, {"$set": {"is_verified": True}})
        await _notify(ip["user_id"], "verified", "Institution verified", "Your institution profile has been verified.")
    else:
        await db.institution_profiles.update_one(
            {"id": inst_id},
            {"$set": {"verification_status": "rejected"}}
        )
        await _notify(ip["user_id"], "rejected", "Verification rejected", payload.reason or "Please update your details and re-submit.")
    return {"ok": True}


@api.get("/admin/users")
async def admin_users(q: Optional[str] = None, role: Optional[str] = None, user: dict = Depends(require_role("admin"))):
    filt = {}
    if role:
        filt["role"] = role
    if q:
        filt["$or"] = [
            {"email": {"$regex": q, "$options": "i"}},
            {"name": {"$regex": q, "$options": "i"}},
        ]
    cursor = db.users.find(filt, {"_id": 0, "password_hash": 0}).limit(200)
    return await cursor.to_list(length=200)


@api.get("/admin/listings")
async def admin_listings(user: dict = Depends(require_role("admin"))):
    cursor = db.internship_listings.find({}, {"_id": 0}).sort("created_at", -1).limit(200)
    items = await cursor.to_list(length=200)
    for it in items:
        sp = await db.startup_profiles.find_one(
            {"id": it["startup_id"]}, {"_id": 0, "company_name": 1, "logo_url": 1, "is_verified": 1}
        )
        it["startup"] = sp
    return items


# ============================== NOTIFICATIONS ==============================
@api.get("/notifications")
async def list_notifications(user: dict = Depends(get_current_user)):
    cursor = db.notifications.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(50)
    return await cursor.to_list(length=50)


@api.post("/notifications/read-all")
async def read_all_notifications(user: dict = Depends(get_current_user)):
    await db.notifications.update_many({"user_id": user["id"], "is_read": False}, {"$set": {"is_read": True, "read_at": now_utc_iso()}})
    return {"ok": True}


@api.post("/notifications/{notif_id}/read")
async def read_notification(notif_id: str, user: dict = Depends(get_current_user)):
    await db.notifications.update_one({"id": notif_id, "user_id": user["id"]}, {"$set": {"is_read": True, "read_at": now_utc_iso()}})
    return {"ok": True}


# ============================== INTERVIEWS ==============================
@api.post("/interviews")
async def schedule_interview(payload: InterviewCreate, user: dict = Depends(require_role("startup"))):
    a = await db.applications.find_one({"id": payload.application_id})
    if not a:
        raise HTTPException(status_code=404, detail="Application not found")
    sp = await db.startup_profiles.find_one({"user_id": user["id"]})
    l = await db.internship_listings.find_one({"id": a["listing_id"]})
    if not l or l["startup_id"] != sp["id"]:
        raise HTTPException(status_code=403, detail="Not your application")
    iid = new_id()
    doc = payload.model_dump()
    doc.update({
        "id": iid, "status": "awaiting_student",
        "created_at": now_utc_iso(),
    })
    await db.interview_schedules.insert_one(doc)
    await db.applications.update_one(
        {"id": payload.application_id},
        {"$set": {"status": "interview_scheduled", "updated_at": now_utc_iso()}}
    )
    await _notify(
        a["student_user_id"], "interview_scheduled",
        f"Interview scheduled: {l['title']}",
        f"Please confirm one of the proposed slots.",
        link="/student/applications",
    )
    return {"id": iid}


@api.get("/interviews/my")
async def my_interviews(user: dict = Depends(get_current_user)):
    if user["role"] == "student":
        sp = await db.student_profiles.find_one({"user_id": user["id"]})
        if not sp:
            return []
        apps = await db.applications.find({"student_id": sp["id"]}, {"_id": 0}).to_list(length=500)
        app_ids = [a["id"] for a in apps]
        cursor = db.interview_schedules.find({"application_id": {"$in": app_ids}}, {"_id": 0})
    elif user["role"] == "startup":
        sp = await db.startup_profiles.find_one({"user_id": user["id"]})
        if not sp:
            return []
        listings = await db.internship_listings.find({"startup_id": sp["id"]}, {"id": 1, "_id": 0}).to_list(length=200)
        listing_ids = [l["id"] for l in listings]
        apps = await db.applications.find({"listing_id": {"$in": listing_ids}}, {"_id": 0}).to_list(length=1000)
        app_ids = [a["id"] for a in apps]
        cursor = db.interview_schedules.find({"application_id": {"$in": app_ids}}, {"_id": 0})
    else:
        return []
    return await cursor.to_list(length=500)


@api.post("/interviews/{interview_id}/confirm")
async def confirm_interview(interview_id: str, payload: InterviewConfirm, user: dict = Depends(require_role("student"))):
    iv = await db.interview_schedules.find_one({"id": interview_id})
    if not iv:
        raise HTTPException(status_code=404, detail="Interview not found")
    await db.interview_schedules.update_one(
        {"id": interview_id},
        {"$set": {"confirmed_slot": payload.slot, "status": "confirmed"}}
    )
    return {"ok": True}


# ============================== STUDENT DISCOVERY ==============================
@api.get("/student/recommendations")
async def recommendations(user: dict = Depends(require_role("student"))):
    sp = await db.student_profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not sp:
        return []
    cursor = db.internship_listings.find({"status": "live"}, {"_id": 0}).sort("created_at", -1).limit(30)
    listings = await cursor.to_list(length=30)
    for l in listings:
        l["match_score"] = calculate_match_score(sp, l)
        l["match_tier"] = match_tier(l["match_score"])
        startup = await db.startup_profiles.find_one(
            {"id": l["startup_id"]},
            {"_id": 0, "company_name": 1, "logo_url": 1, "primary_domain": 1, "is_verified": 1}
        )
        l["startup"] = startup
    listings.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return listings[:12]


# ============================== STARTUP DASHBOARD ==============================
@api.get("/startup/dashboard")
async def startup_dashboard(user: dict = Depends(require_role("startup"))):
    sp = await db.startup_profiles.find_one({"user_id": user["id"]})
    if not sp:
        return {"listings": 0, "applications": 0, "shortlisted": 0, "hired": 0}
    listings = await db.internship_listings.find({"startup_id": sp["id"]}, {"id": 1, "_id": 0}).to_list(length=200)
    listing_ids = [l["id"] for l in listings]
    return {
        "listings": len(listing_ids),
        "applications": await db.applications.count_documents({"listing_id": {"$in": listing_ids}}),
        "shortlisted": await db.applications.count_documents({"listing_id": {"$in": listing_ids}, "status": "shortlisted"}),
        "hired": await db.applications.count_documents({"listing_id": {"$in": listing_ids}, "status": "accepted"}),
        "interview_scheduled": await db.applications.count_documents({"listing_id": {"$in": listing_ids}, "status": "interview_scheduled"}),
    }


@api.get("/startup/candidates")
async def startup_candidates(listing_id: Optional[str] = None, user: dict = Depends(require_role("startup"))):
    sp = await db.startup_profiles.find_one({"user_id": user["id"]})
    if not sp:
        return []
    if listing_id:
        filt = {"listing_id": listing_id}
    else:
        listings = await db.internship_listings.find({"startup_id": sp["id"]}, {"id": 1, "_id": 0}).to_list(length=200)
        filt = {"listing_id": {"$in": [l["id"] for l in listings]}}
    apps = await db.applications.find(filt, {"_id": 0}).sort("created_at", -1).to_list(length=1000)
    for a in apps:
        st = await db.student_profiles.find_one({"id": a["student_id"]}, {"_id": 0})
        a["student"] = st
        l = await db.internship_listings.find_one({"id": a["listing_id"]}, {"_id": 0, "title": 1, "department": 1})
        a["listing"] = l
    return apps


# ============================== HEALTH ==============================
@api.get("/health")
async def health():
    return {"ok": True, "service": "startupinternships", "timestamp": now_utc_iso()}


# ============================== MOUNT ==============================
app.include_router(api)

frontend_origin = os.environ.get("FRONTEND_URL", "*")
cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
