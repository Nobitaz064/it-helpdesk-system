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

- **Python:** Application logic (planned)
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

### Upcoming Development

- **Week 2:** Python & SQL Development
- **Week 3:** Streamlit Web Interface
- **Week 4:** Testing & Portfolio

## Current Status

Week 1 database prototype completed. The Python application and web interface are planned for the next stages.

Asset management and Power BI analytics are reserved for future development.