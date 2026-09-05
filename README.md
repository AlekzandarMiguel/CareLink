# CareLink

CareLink is a patient referral and hospital matching web application built with Django and an XGBoost machine learning model. This is a personal project I built for fun to experiment with healthcare logistics, clinical triage logic, and routing algorithms.

When a clinic or hospital does not have the right facilities, ICU beds, or specialists for a patient, they need to refer and transfer the patient to a better-equipped hospital. CareLink helps automate this decision by analyzing patient vitals, medical urgency, hospital capacity, and road travel times to suggest the best destination hospitals.

---

## What the Project Is All About

The idea behind CareLink is to make patient transfers faster and smarter instead of relying on phone calls and manual guessing.

The matching system looks at:
- Patient urgency and vitals using automated MEWS (Modified Early Warning Score) calculation.
- Specific emergency conditions (like heart attacks, strokes, or trauma) and their critical time windows (like the 90-minute Door-to-Balloon target for STEMI).
- Real-world road driving distance and travel time with traffic adjustments.
- Net hospital capacity (open general beds and ICU beds, minus incoming ambulances already on the way).
- Active on-call specialist duty status (whether cardiologists, neurologists, or surgeons are on shift).
- A 12-feature XGBoost machine learning model that predicts acceptance likelihood and scores candidates.
- Clear factor breakdowns explaining why a hospital received a certain match score.

---

## What the Project Has

### AI Hospital Matcher
- 12-Feature XGBoost ranking model trained on service matching, bed ratios, travel time, urgency, MEWS scores, specialist availability, and time windows.
- Clinical text parser that scans notes and complaints for key conditions (STEMI, stroke, trauma, sepsis, respiratory distress).
- Road corridor routing that estimates driving times and traffic delays.
- Multi-objective score combining acceptance probability, intake speed, hospital tier, and travel feasibility.
- Explainable score breakdown showing positive and negative points for each hospital.
- Coordinator override system to log when a human picks a different hospital and why (e.g. equipment down or crowded ER).

### Referral Workflow
- 15-stage referral lifecycle tracking: Draft -> Submitted -> Under Review -> Accepted -> Dispatched -> In Transit -> Arrived -> Handed Over -> Completed.
- Case-specific discussion notes and clinical messaging thread.
- Attachment support for medical summaries, lab reports, and imaging docs.
- Full timeline history and audit logging for every status update.

### Role-Based Dashboards
The application has 4 separate roles with their own dashboards:
- Admin: Hospital approvals, user management, audit logs, and AI model status.
- Coordinator: Live unrouted referral queue, interactive AI matching workbench, candidate comparisons, and override routing.
- Dispatcher: Ambulance fleet tracking, assigning vehicles/drivers/paramedics, and advancing transit milestones.
- Hospital Staff: Submitting patient referrals, entering vitals, reviewing incoming transfers, and updating bed/ICU availability.

---

## Tech Stack

- Backend: Python 3.14, Django 6.1, Django REST Framework
- Machine Learning: XGBoost, Scikit-learn, Pandas, NumPy, Joblib
- Frontend: Tailwind CSS, HTML5, Vanilla JavaScript, Chart.js
- Database: SQLite (default) / MySQL compatible

---

## How to Run the Project

1. Clone the repository:
```bash
git clone https://github.com/AlekzandarMiguel/CareLink.git
cd CareLink
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run database migrations and seed sample data:
```bash
cd backend
python manage.py migrate
python seed_data.py
```

5. Start the development server:
```bash
python manage.py runserver
```

6. Open your browser and go to:
```text
http://127.0.0.1:8000
```

---

## Demo Accounts

Sample user accounts are included in the seed data:

| Role | Email | Password | Details |
| :--- | :--- | :--- | :--- |
| Admin | admin@carelink.local | AdminPass123! | System admin dashboard |
| Coordinator | coordinator@carelink.local | CoordPass123! | Referral queue and AI matcher |
| Dispatcher | dispatcher@carelink.local | DispatchPass123! | Ambulance transport board |
| Hospital Staff (BPMC) | staff.bpmc@carelink.local | StaffPass123! | Bukidnon Provincial Medical Center |
| Hospital Staff (Metro Gen) | staff.a1@carelink.local | StaffPass123! | Metro General Hospital |
