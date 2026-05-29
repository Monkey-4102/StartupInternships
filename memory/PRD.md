# StartupInternships.in — Product Requirements Document

## Original Problem Statement
Build a highly premium, scalable, enterprise-grade MVP web application called "StartupInternships.in" — a Startup Workforce Infrastructure Platform connecting Startups, Students, and Educational Institutions through a centralized internship and workforce collaboration ecosystem. Tamil Nadu-focused demo data.

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn UI + Lucide icons + sonner toasts
- **Backend**: FastAPI + Motor (async MongoDB driver)
- **Database**: MongoDB with collections — users, student_profiles, startup_profiles, institution_profiles, internship_listings, applications, notifications, interview_schedules, login_attempts
- **Auth**: JWT (HS256) with HttpOnly cookies (access 15min + refresh 7days), bcrypt password hashing (cost 12), brute-force lockout
- **Design**: Inter (body) + DM Sans (headings), white/black/zinc palette, blue accent — Stripe/Linear/Notion-inspired enterprise SaaS aesthetic

## User Personas
1. **Student** — College student seeking internship; needs personalized discovery, applications tracker, profile management
2. **Startup** — Founder/HR hiring talent; needs listing creation, Kanban candidate pipeline, match scoring
3. **Institution** — Placement cell at college/university; needs roster view + placement analytics
4. **Admin** — Platform operator; needs verification queue, user management, content moderation

## Core Requirements (Static)
- Multi-role auth with role-based dashboards & route guards
- 4 internship compensation types (Fixed / Performance / Unpaid / Hybrid)
- 11 domain coverage (Software, Hardware, AI-ML, Marketing, Operations, Sales, Finance, Design, Product, HR, Legal)
- Smart match scoring (skills 35% + domain 25% + availability 20% + work mode 10% + compensation 10%)
- 7-stage application pipeline (Applied → Under Review → Shortlisted → Interview → Offered → Hired/Rejected)
- Live ecosystem stats on landing page
- Tamil Nadu localization

## Implemented (Feb 2026)
### Frontend
- Premium landing page with live stats counter, internship feed, institution marquee, domain grid, how-it-works toggle
- Auth: Login + Register with 3-role selector + demo quick-fill buttons
- AppShell with sidebar navigation, glass topbar, notification bell, user dropdown
- Student: Dashboard (recommendations), Discover (search+filters), Applications tracker (status tabs, withdraw, offer accept/decline), Profile (10+ fields, domain chips)
- Startup: Dashboard, Post Internship (conditional fields per comp type), My Listings (pause/resume), Candidates Kanban (7 columns, drag-via-dialog stage moves), Company Profile
- Institution: Dashboard (placement stats by domain), Students roster, Profile
- Admin: Dashboard (8 KPIs), Verifications (startups + institutions tabs with approve/reject), Users (search+filter), Listings table
- Internship Detail public page with apply CTA

### Backend
- 35+ REST API endpoints organized into auth, public, internships, applications, profiles, startup, institution, admin, notifications, interviews
- Smart match scoring engine (matching.py)
- Tamil Nadu seed data: 10 institutions, 15 startups (Freshworks, Zoho, Chargebee, Uniphore, etc.), 12 students, 22 live internships
- Cookie-based JWT with auto-refresh interceptor on the frontend
- Brute-force lockout after 5 failed login attempts (15 min)

### Testing
- 44 backend pytest tests — 100% passing
- All frontend critical flows verified by testing agent
- 1 HIGH bug found & fixed (Motor collection truthiness on `_get_profile`)

## Deferred to Next Iteration (Backlog)
### P0
- [ ] PDF offer letter generation (with watermark + dual sign)
- [ ] Email & SMS notifications via SendGrid + Twilio
- [ ] CSV bulk student upload for institutions (current API placeholder only)

### P1
- [ ] Interview scheduling UI (backend endpoints already wired)
- [ ] Razorpay integration for premium startup features
- [ ] In-app chat between startup ↔ shortlisted student
- [ ] Analytics charts depth (Recharts) on Institution dashboard
- [ ] Resume parser (extract skills/education automatically)
- [ ] Real-time updates via WebSocket / polling for landing stats

### P2
- [ ] AI-powered smart match (currently rule-based, ready for ML upgrade)
- [ ] Mobile app (React Native)
- [ ] Hindi / Tamil language support
- [ ] Bulk listing import for startups
- [ ] WhatsApp Business API notifications

## Tech Decisions Log
- Chose React + FastAPI + MongoDB over Next.js + Node + Postgres (aligned with platform infra). Schema-flexibility of Mongo serves the rapidly-evolving MVP well.
- Same-origin httpOnly cookies preferred over Bearer tokens in localStorage (XSS-safer).
- Rule-based match scoring for MVP; matching.py is structured for easy ML drop-in later.
- Single server.py (~700 lines) for MVP velocity — split into routers/ once we hit P0 items.

## Test Credentials
See `/app/memory/test_credentials.md`
