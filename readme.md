# IT Helpdesk & Asset Management System

## Project Overview

A portfolio project designed to simulate IT support ticket management for a small company.

The system helps employees report technical issues and allows IT technicians to track, troubleshoot, and resolve support requests.

## Project Objectives

- Create and manage IT support tickets.
- Assign tickets to IT technicians.
- Track ticket status and priority.
- Record troubleshooting history.
- Develop a web interface using Streamlit.
- Extend the system with asset management and Power BI analytics in future phases.

## Technology Stack

- **Python:** Backend business logic and automated testing
- **SQLite:** Database
- **Streamlit:** Web interface (planned)
- **SQL:** Database operations
- **Git & GitHub:** Version control

## User Roles

- **Employee:** Create and track support tickets.
- **Technician:** Manage assigned tickets and record troubleshooting activities.
- **Admin:** Assign technicians and monitor ticket activities.

## Ticket Workflow

Open → In Progress → Resolved → Closed

A resolved ticket can return to In Progress if the issue persists.

## Database Design

The initial database contains four tables:

1. `USERS`
2. `CATEGORIES`
3. `TICKETS`
4. `TICKET_HISTORY`

## Project Progress

### Week 1 — Planning & Database Design

- [x] Define project requirements.
- [x] Design ticket workflow.
- [x] Create database schema.
- [x] Initialize SQLite database.
- [x] Insert sample data.
- [x] Test ticket lifecycle and history.


### Week 2 — Python & SQL Development

- [x] Connect Python to SQLite.
- [x] Implement ticket creation.
- [x] Implement ticket viewing and searching.
- [x] Filter tickets by status, priority, and category.
- [x] Implement technician assignment.
- [x] Implement ticket status updates.
- [x] Record ticket history.
- [x] Implement role-based business rules.
- [x] Add automated unit tests.
- [x] Test database integrity and transactions.
- [x] Create database initialization script.

### Week 3 — Streamlit Web Interface

- [ ] Build the web interface.
- [ ] Create ticket submission form.
- [ ] Display and search tickets.
- [ ] Implement technician dashboard.
- [ ] Implement admin dashboard.
- [ ] Connect Streamlit to SQLite.

### Week 4 — Final Testing & Portfolio

- [ ] Perform end-to-end testing.
- [ ] Improve error handling and usability.
- [ ] Document screenshots and test results.
- [ ] Finalize README and GitHub portfolio.

## Database Setup

To initialize the database on a new computer:

```powershell
py database/init_db.py
```

The script creates the database schema and initial sample
users and categories if the database file does not exist.

The SQLite database file is excluded from Git.

## Run Backend Tests

```powershell
py -m unittest discover -s tests -p "test_*.py" -v
```

## Current Status

Week 1 and Week 2 development completed.

The project currently supports ticket creation, viewing,
searching, filtering, technician assignment, status updates,
ticket history, and automated backend testing.

Week 3 focuses on building the Streamlit web interface.

Asset Management and Power BI analytics are planned
for future development.
