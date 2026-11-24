# EduHub - Interactive Software Engineering Quiz Platform

A Django e-learning web app built for **UniKL ISB46803 - Selected Topics in Software Engineering**.
Students take interactive, auto-graded quizzes across every core Software Engineering topic;
lecturers author quizzes; and admins monitor the platform from a charts dashboard.

Built with Django's **Model-Template-View (MTV)** architecture on a **SQLite** database.

---

## Features by role

| Role | What they can do |
|------|------------------|
| **Student** | Browse 10 SE topics, take interactive quizzes (live timer, progress bar, one question at a time), get an animated score with full answer explanations, track history, climb the leaderboard |
| **Lecturer** | Create/edit quizzes, add, edit and delete questions with four choices, see attempt counts per quiz |
| **Admin** | Dashboard with Chart.js analytics (attempts per day, attempts per topic), totals, recent activity, and full CRUD via Django admin |

**Question bank:** 10 topics · 10 quizzes · **71 questions**, covering Introduction to SE, Process Models,
Agile & Scrum, Requirements Engineering, Design & Architecture, UML, Testing, Quality & Maintenance,
Project Management & Estimation, and Configuration Management & DevOps.

**Highlights:** server-side authoritative grading, interactive quiz player (timer auto-submit, smooth
navigation, selectable option cards), animated circular score ring, per-question review with explanations,
a leaderboard, and role-based access control.

---

## How to run

> Requires Python 3.10+ (tested on 3.14). Run all commands from this folder.

```powershell
python -m venv venv
venv\Scripts\activate              # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data         # loads all SE topics + questions + demo users
python manage.py runserver
```

Open **http://127.0.0.1:8000/**  (in VS Code, press **F5 → "EduHub: Run server"**).

### Demo login credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Lecturer | `lecturer` | `teach123` |
| Student | `student` | `learn123` |

Extra students (populate the leaderboard): `alice`, `bob`, `carol` - all `learn123`.

Reset demo data anytime: `python manage.py seed_data --fresh`.

---

## Project structure (Model-Template-View)

```
EduHub/
├─ manage.py
├─ requirements.txt
├─ eduhub/                 # project configuration
│  ├─ settings.py          # AUTH_USER_MODEL = quizzes.User, SQLite, timezone
│  └─ urls.py              # routes + built-in login/logout
└─ quizzes/                # the application
   ├─ models.py            # MODEL  -> User, Topic, Quiz, Question, Choice, Attempt, Answer
   ├─ views.py             # VIEW   -> routing, role checks, server-side grading
   ├─ forms.py             # registration / quiz / question forms
   ├─ urls.py              # use-case-to-view routing
   ├─ admin.py             # Django admin (Admin role CRUD)
   ├─ templates/quizzes/   # TEMPLATE -> 16 Bootstrap + custom-CSS pages
   ├─ static/quizzes/      # the EduHub design system (style.css)
   └─ management/commands/seed_data.py   # the Software Engineering question bank
```

## Data model relationships (for the UML class diagram)

- **Inheritance** - `User` extends Django's `AbstractUser`.
- **Aggregation** - `Topic` groups many `Quiz`zes.
- **Composition** - `Quiz` owns `Question`s, `Question` owns `Choice`s, `Attempt` owns `Answer`s.
- **Association** - `Attempt` links a Student (`User`) and a `Quiz`.

---

## Tech stack

Python · Django 6 · SQLite · Bootstrap 5 · custom CSS design system · Chart.js · Bootstrap Icons · Google Fonts
