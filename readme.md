# IT Helpdesk & Asset Management System

A portfolio project that simulates IT support for a small company. The current application manages support tickets from submission through assignment, troubleshooting, and closure. It uses Python for business rules, SQLite for storage, and Streamlit for the interface.

## Run locally on Windows

Use Python 3.11 or later. Run the following commands from the repository folder in PowerShell.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe database/init_db.py
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local URL printed by Streamlit. The setup script creates `database/helpdesk.db` with demo users and ticket categories when the file is missing. Create a ticket from the dashboard to start the demo. Git ignores the local database file.

## Try the ticket workflow

The pages use fixed demo identities. Use the Streamlit sidebar to navigate between dashboards.

| Step | Dashboard | Action | Result |
| --- | --- | --- | --- |
| 1 | Employee (An) | Create a ticket for a Wi-Fi issue. | Status is `open`. |
| 2 | Admin (Chi) | Assign the ticket to Binh. | Status is `in_progress`. |
| 3 | Technician (Binh) | Add troubleshooting notes and select **Mark as Resolved**. | Status is `resolved`. |
| 4 | Employee (An) | Select **Reopen Ticket** and describe the remaining issue. | Status returns to `in_progress`. Binh keeps the assignment. |
| 5 | Technician (Binh) | Fix the remaining issue and mark the ticket resolved again. | Status is `resolved`. |
| 6 | Employee (An) | Select **Close Ticket** and confirm the fix. | Status is `closed`. |

The Admin dashboard also displays totals by status and offers search and filters. The Technician dashboard shows assigned tickets. Users can follow the full state transitions in the [ticket workflow](docs/ticket_workflow.md).

## How the system works

1. The [Employee Dashboard](app.py), [Technician Dashboard](pages/1_Technician_Dashboard.py), and [Admin Dashboard](pages/2_Admin_Dashboard.py) collect input and display the latest ticket data.
2. The [ticket service](src/ticket_service.py) validates input, checks role and ownership rules, and applies allowed status transitions.
3. SQLite stores the current record in `TICKETS` and logs the actor, status, and note in `TICKET_HISTORY`. A transaction commits each ticket update together with its history entry.

The [database design](docs/erd.md) describes the relationships between `USERS`, `CATEGORIES`, `TICKETS`, and `TICKET_HISTORY`. See the [requirements](docs/requirement.md) for the project scope.

## Run the tests

Run the following command after installing the dependencies.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests initialize temporary SQLite databases, so you can run them before creating the app's database. They cover input validation, role and ownership checks, transaction rollback, and stale forms. The [workflow test](tests/test_ticket_workflow.py) uses Streamlit `AppTest` to simulate the six steps above across three dashboards and check all six history entries in order.

All 11 automated tests passed with Python 3.14.10 and Streamlit 1.67.0.

## Project progress

- [x] Week 1 — Requirements, database design, and SQLite schema.
- [x] Week 2 — Python ticket service, role checks, and transaction tests.
- [x] Week 3 — Streamlit dashboards, assignment, resolution, and close or reopen.
- [x] Week 4 — Automated workflow testing and local setup documentation.
- [ ] Week 4 — Usability review, screenshots, and GitHub portfolio.

Asset management and Power BI analytics are planned for future phases.
