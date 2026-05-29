# StartupInternships.in — Test Credentials

All demo accounts use password: **Demo@2025**

## Admin (seeded from env)
- **Email**: admin@startupinternships.in
- **Password**: Admin@2025
- **Role**: admin

## Demo Students (12 total — Tamil Nadu colleges)
- student1@demo.startupinternships.in — Arjun Mehta (IIT Madras)
- student2@demo.startupinternships.in — Divya Sundaram (Anna University)
- student3@demo.startupinternships.in — Karthik Rajan (PSG Tech)
- student4@demo.startupinternships.in — Priya Lakshmi (VIT Vellore)
- student5@demo.startupinternships.in — Suresh Kumar (SSN College)
- ... up to student12@demo.startupinternships.in
- **Password**: Demo@2025
- **Role**: student

## Demo Startups (15 total — Tamil Nadu)
- startup1@demo.startupinternships.in — Freshworks
- startup2@demo.startupinternships.in — Zoho Schools of Learning
- startup3@demo.startupinternships.in — Chargebee
- ... up to startup15@demo.startupinternships.in
- **Password**: Demo@2025
- **Role**: startup
- All seeded as verified

## Demo Institutions (10 total — Tamil Nadu)
- inst1@demo.startupinternships.in — IIT Madras
- inst2@demo.startupinternships.in — Anna University
- ... up to inst10@demo.startupinternships.in
- **Password**: Demo@2025
- **Role**: institution
- All seeded as verified

## Auth Endpoints
- POST /api/auth/register — public
- POST /api/auth/login — public
- POST /api/auth/logout — auth required
- GET  /api/auth/me — auth required
- POST /api/auth/refresh — refresh cookie required

## Key Endpoints
- GET /api/public/stats — landing stats
- GET /api/public/internships — featured landing internships
- GET /api/internships — paginated/filterable
- POST /api/applications — student applies
- GET /api/student/recommendations — match-scored feed
- GET /api/startup/dashboard — startup stats
- GET /api/startup/candidates — kanban pipeline
- POST /api/internships — startup creates listing
- GET /api/admin/analytics — platform stats
- GET /api/admin/verifications/startups — pending queue
