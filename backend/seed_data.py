"""Tamil Nadu-focused demo seed data and admin account seeding."""
import os
from datetime import datetime, timezone, timedelta
from auth import hash_password
from models import new_id, now_utc_iso


TN_CITIES = ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Tirunelveli", "Erode", "Vellore"]

INSTITUTIONS = [
    {"name": "Indian Institute of Technology Madras", "type": "engineering", "city": "Chennai", "naac_grade": "A++", "affiliation": "Autonomous", "logo_url": "https://images.unsplash.com/photo-1632988663082-4bac2c1847a0?w=200&q=80"},
    {"name": "Anna University", "type": "engineering", "city": "Chennai", "naac_grade": "A++", "affiliation": "State University", "logo_url": "https://images.unsplash.com/photo-1562774053-701939374585?w=200&q=80"},
    {"name": "PSG College of Technology", "type": "engineering", "city": "Coimbatore", "naac_grade": "A++", "affiliation": "Anna University", "logo_url": "https://images.unsplash.com/photo-1607013251379-e6eecfffe234?w=200&q=80"},
    {"name": "Vellore Institute of Technology", "type": "engineering", "city": "Vellore", "naac_grade": "A++", "affiliation": "Deemed University", "logo_url": "https://images.unsplash.com/photo-1592280771190-3e2e4d571952?w=200&q=80"},
    {"name": "SSN College of Engineering", "type": "engineering", "city": "Chennai", "naac_grade": "A+", "affiliation": "Anna University", "logo_url": "https://images.unsplash.com/photo-1564981797816-1043664bf78d?w=200&q=80"},
    {"name": "Coimbatore Institute of Technology", "type": "engineering", "city": "Coimbatore", "naac_grade": "A+", "affiliation": "Anna University", "logo_url": "https://images.unsplash.com/photo-1541339907198-e08756dedf3f?w=200&q=80"},
    {"name": "Thiagarajar College of Engineering", "type": "engineering", "city": "Madurai", "naac_grade": "A+", "affiliation": "Anna University", "logo_url": "https://images.unsplash.com/photo-1576495199011-eb94736d05d6?w=200&q=80"},
    {"name": "Loyola College", "type": "arts", "city": "Chennai", "naac_grade": "A++", "affiliation": "University of Madras", "logo_url": "https://images.unsplash.com/photo-1498243691581-b145c3f54a5a?w=200&q=80"},
    {"name": "Madras Christian College", "type": "arts", "city": "Chennai", "naac_grade": "A++", "affiliation": "University of Madras", "logo_url": "https://images.unsplash.com/photo-1607237138185-eedd9c632b0b?w=200&q=80"},
    {"name": "Great Lakes Institute of Management", "type": "mba", "city": "Chennai", "naac_grade": "A", "affiliation": "Autonomous", "logo_url": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=200&q=80"},
]

STARTUPS = [
    {"company_name": "Freshworks", "primary_domain": "Software", "company_stage": "series-b-plus", "city": "Chennai", "team_size_range": "200+", "description": "Customer engagement software built for the modern era.", "logo_url": "https://images.unsplash.com/photo-1611605698335-8b1569810432?w=200&q=80"},
    {"company_name": "Zoho Schools of Learning", "primary_domain": "Software", "company_stage": "series-b-plus", "city": "Chennai", "team_size_range": "200+", "description": "SaaS leader from Chennai building over 50 applications.", "logo_url": "https://images.unsplash.com/photo-1572021335469-31706a17aaef?w=200&q=80"},
    {"company_name": "Chargebee", "primary_domain": "Software", "company_stage": "series-b-plus", "city": "Chennai", "team_size_range": "200+", "description": "Subscription billing platform for the recurring revenue economy.", "logo_url": "https://images.unsplash.com/photo-1614036634955-ae5e90f9b9eb?w=200&q=80"},
    {"company_name": "Uniphore", "primary_domain": "AI-ML", "company_stage": "series-b-plus", "city": "Chennai", "team_size_range": "200+", "description": "Conversational AI and automation platform for enterprises.", "logo_url": "https://images.unsplash.com/photo-1535378917042-10a22c95931a?w=200&q=80"},
    {"company_name": "Detect Technologies", "primary_domain": "Hardware", "company_stage": "series-a", "city": "Chennai", "team_size_range": "51-200", "description": "Industrial AI and robotics for asset-heavy industries.", "logo_url": "https://images.unsplash.com/photo-1581092919535-83f1c1c52e83?w=200&q=80"},
    {"company_name": "OrangeScape", "primary_domain": "Software", "company_stage": "series-a", "city": "Chennai", "team_size_range": "51-200", "description": "Low-code platform for enterprise process automation.", "logo_url": "https://images.unsplash.com/photo-1551434678-e076c223a692?w=200&q=80"},
    {"company_name": "Kissflow", "primary_domain": "Software", "company_stage": "series-a", "city": "Chennai", "team_size_range": "51-200", "description": "Unified work platform powering modern digital workplaces.", "logo_url": "https://images.unsplash.com/photo-1607706189992-eae578626c86?w=200&q=80"},
    {"company_name": "Mad Street Den", "primary_domain": "AI-ML", "company_stage": "series-a", "city": "Chennai", "team_size_range": "51-200", "description": "AI for retail and e-commerce personalization.", "logo_url": "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=200&q=80"},
    {"company_name": "Ather Energy", "primary_domain": "Hardware", "company_stage": "series-b-plus", "city": "Chennai", "team_size_range": "200+", "description": "Designing and building intelligent electric vehicles.", "logo_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=200&q=80"},
    {"company_name": "Ninjacart", "primary_domain": "Operations", "company_stage": "series-b-plus", "city": "Coimbatore", "team_size_range": "200+", "description": "Fresh produce supply chain for retailers, restaurants & consumers.", "logo_url": "https://images.unsplash.com/photo-1542838132-92c53300491e?w=200&q=80"},
    {"company_name": "Yubi", "primary_domain": "Finance", "company_stage": "series-b-plus", "city": "Chennai", "team_size_range": "200+", "description": "Discovery to fulfillment for everything credit.", "logo_url": "https://images.unsplash.com/photo-1565514020179-026b92b84bb6?w=200&q=80"},
    {"company_name": "Pixelmate Studio", "primary_domain": "Design", "company_stage": "seed", "city": "Coimbatore", "team_size_range": "11-50", "description": "Design-led product studio for early-stage startups.", "logo_url": "https://images.unsplash.com/photo-1561070791-2526d30994b8?w=200&q=80"},
    {"company_name": "Hyperloop Madurai", "primary_domain": "Hardware", "company_stage": "pre-seed", "city": "Madurai", "team_size_range": "11-50", "description": "Building next-gen sustainable transportation.", "logo_url": "https://images.unsplash.com/photo-1486718448742-163732cd1544?w=200&q=80"},
    {"company_name": "AgriBolt", "primary_domain": "Operations", "company_stage": "seed", "city": "Salem", "team_size_range": "11-50", "description": "Tech-enabled agri supply chain platform.", "logo_url": "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=200&q=80"},
    {"company_name": "Tessolve", "primary_domain": "Hardware", "company_stage": "series-b-plus", "city": "Chennai", "team_size_range": "200+", "description": "Semiconductor engineering services company.", "logo_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=200&q=80"},
]

INTERN_ROLES = [
    ("Software Engineering Intern", "Software", ["Python", "JavaScript", "React", "Node.js", "Git"]),
    ("Frontend Engineering Intern", "Software", ["React", "TypeScript", "CSS", "TailwindCSS", "Git"]),
    ("Backend Engineering Intern", "Software", ["Python", "FastAPI", "MongoDB", "PostgreSQL", "Docker"]),
    ("Data Science Intern", "AI-ML", ["Python", "Pandas", "scikit-learn", "SQL", "Statistics"]),
    ("Machine Learning Intern", "AI-ML", ["Python", "PyTorch", "TensorFlow", "NLP", "Computer Vision"]),
    ("Product Design Intern", "Design", ["Figma", "Prototyping", "UX Research", "Wireframing"]),
    ("Growth Marketing Intern", "Marketing", ["SEO", "Content", "Google Ads", "Analytics", "Copywriting"]),
    ("Content Marketing Intern", "Marketing", ["Writing", "SEO", "Social Media", "WordPress"]),
    ("Operations Intern", "Operations", ["Excel", "Process Design", "Supply Chain", "Logistics"]),
    ("Business Development Intern", "Sales", ["Cold Outreach", "CRM", "Communication", "Negotiation"]),
    ("Finance Intern", "Finance", ["Excel", "Financial Modeling", "Accounting", "Valuation"]),
    ("Hardware Engineering Intern", "Hardware", ["C++", "Embedded Systems", "PCB Design", "FPGA"]),
    ("Product Management Intern", "Product", ["Roadmapping", "User Research", "SQL", "Wireframing"]),
    ("HR Intern", "HR", ["Recruitment", "Communication", "HRMS", "Excel"]),
    ("UI/UX Design Intern", "Design", ["Figma", "Adobe XD", "User Research", "Interaction Design"]),
]

COMP_TYPES = ["fixed", "performance", "unpaid", "hybrid"]
WORK_MODES = ["remote", "onsite", "hybrid"]

STUDENTS = [
    {"full_name": "Arjun Mehta", "college": "Indian Institute of Technology Madras", "branch": "Computer Science", "skills": ["Python", "React", "Node.js", "Git", "MongoDB"], "domains": ["Software", "AI-ML"]},
    {"full_name": "Divya Sundaram", "college": "Anna University", "branch": "Information Technology", "skills": ["JavaScript", "React", "TypeScript", "CSS", "TailwindCSS"], "domains": ["Software", "Design"]},
    {"full_name": "Karthik Rajan", "college": "PSG College of Technology", "branch": "Electronics", "skills": ["C++", "Embedded Systems", "Python", "FPGA"], "domains": ["Hardware", "AI-ML"]},
    {"full_name": "Priya Lakshmi", "college": "Vellore Institute of Technology", "branch": "Computer Science", "skills": ["Python", "PyTorch", "TensorFlow", "SQL", "NLP"], "domains": ["AI-ML", "Software"]},
    {"full_name": "Suresh Kumar", "college": "SSN College of Engineering", "branch": "Mechanical Engineering", "skills": ["AutoCAD", "SolidWorks", "Python", "Project Management"], "domains": ["Hardware", "Operations"]},
    {"full_name": "Meera Iyer", "college": "Loyola College", "branch": "Economics", "skills": ["Excel", "Financial Modeling", "Python", "SQL"], "domains": ["Finance", "Operations"]},
    {"full_name": "Rohit Subramanian", "college": "Madras Christian College", "branch": "English Literature", "skills": ["Writing", "SEO", "Content", "Social Media"], "domains": ["Marketing"]},
    {"full_name": "Ananya Krishnan", "college": "Great Lakes Institute of Management", "branch": "MBA", "skills": ["Strategy", "Excel", "Communication", "Marketing"], "domains": ["Marketing", "Sales"]},
    {"full_name": "Vignesh Pandian", "college": "Coimbatore Institute of Technology", "branch": "Computer Science", "skills": ["Java", "Spring Boot", "MongoDB", "Docker"], "domains": ["Software"]},
    {"full_name": "Lavanya Rajaraman", "college": "Thiagarajar College of Engineering", "branch": "ECE", "skills": ["Figma", "Adobe XD", "User Research", "Prototyping"], "domains": ["Design", "Product"]},
    {"full_name": "Hari Venkatesh", "college": "Anna University", "branch": "Mechanical", "skills": ["AutoCAD", "Supply Chain", "Excel", "Logistics"], "domains": ["Operations"]},
    {"full_name": "Sneha Balachandran", "college": "SSN College of Engineering", "branch": "Information Technology", "skills": ["Python", "Django", "PostgreSQL", "AWS"], "domains": ["Software"]},
]


async def seed_admin(db):
    """Create or update the admin account based on env vars."""
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@startupinternships.in")
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@2025")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "id": new_id(),
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "name": "Platform Admin",
            "role": "admin",
            "is_verified": True,
            "created_at": now_utc_iso(),
        })


async def _create_user(db, email, password, role, name, is_verified=True):
    existing = await db.users.find_one({"email": email})
    if existing:
        return existing["id"]
    uid = new_id()
    await db.users.insert_one({
        "id": uid, "email": email, "password_hash": hash_password(password),
        "name": name, "role": role, "is_verified": is_verified,
        "created_at": now_utc_iso(),
    })
    return uid


async def seed_demo_data(db):
    """Seed Tamil Nadu-focused demo data if empty."""
    # Skip if already seeded
    if await db.startup_profiles.count_documents({}) > 0:
        return

    # Institutions
    inst_ids = []
    for i, ins in enumerate(INSTITUTIONS):
        email = f"inst{i+1}@demo.startupinternships.in"
        uid = await _create_user(db, email, "Demo@2025", "institution", ins["name"])
        pid = new_id()
        inst_ids.append(pid)
        await db.institution_profiles.insert_one({
            "id": pid, "user_id": uid, "name": ins["name"], "type": ins["type"],
            "affiliation": ins["affiliation"], "naac_grade": ins["naac_grade"],
            "city": ins["city"], "state": "Tamil Nadu",
            "placement_head_name": "Dr. Placement Head",
            "contact_email": email, "contact_phone": "+91-9000000000",
            "website_url": f"https://{ins['name'].lower().replace(' ','')}.edu.in",
            "student_count": 2000 + (i * 250),
            "is_verified": True, "verification_status": "verified",
            "logo_url": ins["logo_url"],
            "created_at": now_utc_iso(), "updated_at": now_utc_iso(),
        })
        await db.users.update_one({"id": uid}, {"$set": {"profile_id": pid}})

    # Startups
    startup_ids = []
    for i, s in enumerate(STARTUPS):
        email = f"startup{i+1}@demo.startupinternships.in"
        uid = await _create_user(db, email, "Demo@2025", "startup", s["company_name"])
        pid = new_id()
        startup_ids.append(pid)
        await db.startup_profiles.insert_one({
            "id": pid, "user_id": uid, "company_name": s["company_name"],
            "registered_name": s["company_name"] + " Pvt Ltd",
            "logo_url": s["logo_url"],
            "website_url": f"https://{s['company_name'].lower().replace(' ','')}.com",
            "linkedin_url": f"https://linkedin.com/company/{s['company_name'].lower().replace(' ','-')}",
            "cin_number": f"U72900TN20{15+i%5}PTC0{10000+i}",
            "founding_year": 2010 + (i % 12),
            "company_stage": s["company_stage"],
            "team_size_range": s["team_size_range"],
            "primary_domain": s["primary_domain"],
            "description": s["description"],
            "cities": [s["city"]],
            "is_verified": True, "verification_status": "verified",
            "verified_at": now_utc_iso(),
            "created_at": now_utc_iso(), "updated_at": now_utc_iso(),
        })
        await db.users.update_one({"id": uid}, {"$set": {"profile_id": pid, "is_verified": True}})

    # Students
    student_ids = []
    for i, st in enumerate(STUDENTS):
        email = f"student{i+1}@demo.startupinternships.in"
        uid = await _create_user(db, email, "Demo@2025", "student", st["full_name"])
        pid = new_id()
        student_ids.append((pid, uid))
        avail_date = (datetime.now(timezone.utc).date() + timedelta(days=15 + (i % 30))).isoformat()
        await db.student_profiles.insert_one({
            "id": pid, "user_id": uid, "full_name": st["full_name"],
            "phone": f"+91-90000000{10+i:02d}",
            "college_name": st["college"],
            "degree": "B.Tech" if "Engineering" in st.get("branch", "") or "Tech" in st.get("branch", "") else "Bachelor's",
            "branch": st["branch"],
            "year_of_study": 3 + (i % 2),
            "graduation_year": 2026 + (i % 2),
            "cgpa": round(7.5 + (i % 5) * 0.3, 2),
            "bio": f"Passionate {st['branch']} student excited to contribute to Tamil Nadu's startup ecosystem.",
            "skills": st["skills"],
            "domain_interests": st["domains"],
            "availability_date": avail_date,
            "is_available": True,
            "preferred_duration": ["1 month", "2 months", "3 months", "6 months"][i % 4],
            "work_mode_preference": WORK_MODES[i % 3],
            "compensation_preference": ["paid", "any", "paid", "any"][i % 4],
            "expected_stipend_min": 5000 + (i * 1000) % 10000,
            "expected_stipend_max": 15000 + (i * 1500) % 20000,
            "preferred_cities": [TN_CITIES[i % len(TN_CITIES)], "Chennai"],
            "open_to_relocation": i % 2 == 0,
            "profile_completion_score": 85 + (i % 15),
            "created_at": now_utc_iso(), "updated_at": now_utc_iso(),
        })
        await db.users.update_one({"id": uid}, {"$set": {"profile_id": pid}})

    # Internship listings
    listing_ids = []
    today = datetime.now(timezone.utc).date()
    for i, sid in enumerate(startup_ids):
        # Each startup posts 1-2 listings
        n_posts = 1 + (i % 2)
        for j in range(n_posts):
            role_idx = (i * 2 + j) % len(INTERN_ROLES)
            title, dept, skills = INTERN_ROLES[role_idx]
            comp_type = COMP_TYPES[(i + j) % 4]
            work_mode = WORK_MODES[(i + j) % 3]
            start = today + timedelta(days=15 + (i * 3))
            end = start + timedelta(days=90)
            deadline = today + timedelta(days=10 + (i * 2))
            lid = new_id()
            listing_ids.append(lid)
            doc = {
                "id": lid, "startup_id": sid, "title": title, "department": dept,
                "description": f"Join us as a {title}. You'll work directly with the founding team on real product challenges, get hands-on mentorship, and ship features that customers use daily.",
                "required_skills": skills,
                "preferred_qualifications": "Prior project experience or contributions to open source.",
                "openings": 1 + (i % 3),
                "work_mode": work_mode,
                "city": STARTUPS[i]["city"] if work_mode != "remote" else None,
                "duration_start": start.isoformat(),
                "duration_end": end.isoformat(),
                "application_deadline": deadline.isoformat(),
                "compensation_type": comp_type,
                "stipend_fixed_amount": 15000 + (i % 5) * 5000 if comp_type == "fixed" else None,
                "stipend_min": 5000 + (i % 3) * 2000 if comp_type in ("performance", "hybrid") else None,
                "stipend_max": 20000 + (i % 5) * 3000 if comp_type in ("performance", "hybrid") else None,
                "stipend_conditions": "Bonus based on delivered milestones and KPIs." if comp_type in ("performance", "hybrid") else None,
                "unpaid_learning_outcomes": "Mentorship from founders, exposure to fundraising, real production codebase, weekly 1:1s." if comp_type == "unpaid" else None,
                "perks": "Remote-friendly, swag kit, conference tickets, certificate of completion.",
                "status": "live",
                "applications_count": 0,
                "views_count": 50 + (i * 17) % 500,
                "is_featured": i < 3,
                "created_at": now_utc_iso(),
                "updated_at": now_utc_iso(),
            }
            await db.internship_listings.insert_one(doc)

    # Some applications across multiple students/listings
    statuses = ["applied", "under_review", "shortlisted", "interview_scheduled", "offered", "accepted", "rejected"]
    for i, lid in enumerate(listing_ids[:10]):
        for j, (sp_id, su_id) in enumerate(student_ids[:5]):
            if (i + j) % 3 == 0:
                continue
            status = statuses[(i + j) % len(statuses)]
            await db.applications.insert_one({
                "id": new_id(),
                "listing_id": lid,
                "student_id": sp_id,
                "student_user_id": su_id,
                "cover_message": "Excited to bring my skills to your team and contribute meaningfully.",
                "status": status,
                "match_score": 60 + ((i * 7 + j * 11) % 35),
                "created_at": now_utc_iso(),
                "updated_at": now_utc_iso(),
            })
            await db.internship_listings.update_one(
                {"id": lid}, {"$inc": {"applications_count": 1}}
            )
