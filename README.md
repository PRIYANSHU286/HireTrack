# HireTrack — Job Application Management System

A portfolio/demo full-stack recruitment workflow application built with Flask, SQLite, HTML, CSS and JavaScript.

## Features
- Candidate registration and login (passwords hashed)
- Browse and search job listings
- Apply once per job and track application status
- Admin dashboard with job/candidate/application counts
- Admin can publish jobs and update application statuses
- SQLite database and demo jobs are created automatically

## Run locally (Windows PowerShell)
1. Install Python 3.10+.
2. Open this folder in VS Code.
3. `python -m venv venv`
4. `.\venv\Scripts\Activate.ps1`
5. `pip install -r requirements.txt`
6. `python app.py`
7. Open http://127.0.0.1:5000

## Demo admin account
Email: `admin@hiretrack.demo`  
Password: `Admin123!`

Register a separate candidate account to test applying.

## Suggested test
Register candidate → apply for a job → open My Applications → log out → log in as admin → change application status → log back in as candidate and confirm the status changed.

## Structure
- `app.py` — Flask routes, authentication and database operations
- `templates/` — Jinja HTML pages
- `static/style.css` — responsive styling
- `instance/hiretrack.db` — created automatically on first run

## Scope and security
This is a learning/portfolio project, not a production hiring platform. Before public deployment, add CSRF protection, rate limiting, email verification, password reset, stronger secret management, audit logs and deployment hardening. Change the demo admin password and secret key before public use.
