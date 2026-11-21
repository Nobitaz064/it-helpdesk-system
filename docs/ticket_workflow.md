
# Ticket Workflow

## 1. Overview

This document describes the lifecycle of IT support
tickets from creation to closure.

## 2. Ticket Status

- Open — A new ticket waiting for support.
- In Progress — A technician is working on the issue.
- Resolved — The technician has marked the issue fixed.
- Closed — The reporting employee has confirmed the resolution.

## 3. Status Transitions

- Open -> In Progress
- In Progress -> Resolved
- Resolved -> Closed
- Resolved -> In Progress (Reopen)

## 4. Business Rules

- A new ticket starts with Open status.
- An admin assigns an open, unassigned ticket to a technician.
- The assigned technician records troubleshooting notes when resolving the ticket.
- The reporting employee can close or reopen a resolved ticket and must provide a note.
- Every status change is recorded in ticket history.

## 5. Exception Handling

- If the issue persists, the reporting employee can reopen the ticket to return it to In Progress.
- If the user cannot access the application,
  they can contact IT through another channel.
- If the system fails during an update,
  the database must not contain partial changes.

## 6. Manual Test Cases

Use a disposable copy of the app and its demo database. Follow the [local setup instructions](../readme.md#run-locally-on-windows), then switch among the Employee, Admin, and Technician dashboards in the sidebar. Use distinct test ticket titles so you can identify each record in the UI.

| Case | What to do | Expected result |
| --- | --- | --- |
| QA-01 — Create | On Employee, fill **Ticket Title** and **Description**, choose a **Category** and **Priority**, and click **Submit Ticket**. Note the ticket ID. | A success message appears, the form resets, and **My Tickets** shows the new ticket as `open` and `Unassigned`. |
| QA-02 — Invalid create | Leave **Ticket Title** empty, enter a description, choose a different category and priority, then click **Submit Ticket**. | A validation error appears. The description, category, and priority stay in the form, and **My Tickets** gains no row. |
| QA-03 — Assign | On Admin, click **Assign Ticket** with no selections. Then choose the QA-01 ticket under **Select Ticket**, choose Binh under **Select Technician**, and submit again. | The first submission shows a validation error. The second changes the ticket to `in_progress`, sets Binh as technician, and makes the ticket available on the Technician dashboard. |
| QA-04 — Resolve | On Technician, select the assigned ticket in **Resolve Ticket** and click **Mark as Resolved** with blank **Troubleshooting Notes**. Add a note and submit again. | The first attempt leaves the ticket `in_progress`. The second changes it to `resolved` and makes it available in **Review Resolved Tickets** on Employee. |
| QA-05 — Reopen | On Employee, choose the resolved ticket, select **Reopen Ticket** under **Your Decision**, fill **Confirmation / Reopen Note**, and click **Submit Decision**. | The ticket returns to `in_progress`, keeps Binh as its technician, and appears again in **Resolve Ticket**. |
| QA-06 — Close | Have Binh resolve the reopened ticket with a second note. On Employee, choose **Close Ticket**, enter a confirmation note, and click **Submit Decision**. | **My Tickets** shows `closed`. The ticket leaves **Review Resolved Tickets**. |
| QA-07 — Stale Employee form | Prepare two resolved tickets, A and B. Open Employee in two tabs. In both tabs select A, choose **Close Ticket**, and enter a note before submitting either form. Submit in the first tab, then submit in the second. | The stale submission is rejected. A remains `closed` and B remains `resolved`. |
| QA-08 — Stale Technician form | Prepare two assigned `in_progress` tickets, C and D. Open Technician in two tabs. In both tabs select C and enter notes before submitting either form. Submit in the first tab, then submit in the second. | The stale submission is rejected. C remains `resolved` and D remains `in_progress`. |
| QA-09 — Dashboard filters | With tickets in different statuses and priorities, combine **Search Tickets**, **Filter by Status**, and **Filter by Priority** on Admin. Clear them and search for a title that does not exist. On Technician, use **Search Tickets** and **Filter by Status** with an assigned ticket. | Tables display only matching rows. Admin overview totals still describe all tickets. Searching for a nonexistent title shows the empty-result message. Technician results remain limited to assigned tickets. |
| QA-10 — Search boundary | On Technician, paste a string longer than 100 characters into **Search Tickets**. | The field keeps at most 100 characters, and the **Resolve Ticket** section stays accessible. |
| QA-11 — Audit history | Query the QA-01 ticket ID after finishing QA-06. | Six history rows show the transitions in order, the correct actor IDs, and the submitted notes. |

Keep another eligible ticket available when checking form reset after assignment, resolution, or review. That keeps the form visible so you can verify that its selections and note have cleared.

### Check the audit rows in SQLite

Run this read-only query with the QA-01 ticket ID bound as `:ticket_id`.

```sql
SELECT OLD_STATUS, NEW_STATUS, CHANGED_BY, NOTE
FROM TICKET_HISTORY
WHERE TICKET_ID = :ticket_id
ORDER BY HISTORY_ID;
```

For the full workflow, expect `NULL → open` by An (1), `open → in_progress` by Chi (3), `in_progress → resolved` by Binh (2), `resolved → in_progress` by An (1), another `in_progress → resolved` by Binh (2), and `resolved → closed` by An (1). Each resolution and employee review row should contain the note used at that step.

The [automated workflow test](../tests/test_ticket_workflow.py) uses Streamlit AppTest and a temporary SQLite database for the full lifecycle and history. The [employee](../tests/test_employee_dashboard.py), [technician](../tests/test_technician_dashboard.py), and [service](../tests/test_ticket_service.py) tests cover focused cases such as stale form submissions, input validation, access rules, and rollback. Use the manual cases above to verify browser behavior and dashboard filters.

## 7. Internal Pilot Test Cases

Use disposable data. In company mode, enroll test accounts with your organization's identity provider according to the [operations guide](operations.md). Keep notes entered in the current forms suitable for everyone who can view the ticket. They appear in its shared history.

| Case | What to do | Expected result |
| --- | --- | --- |
| Sign-in and role access | Open an Admin page while signed out, then sign in as an enrolled Employee. Try the Admin page again. | Signed-out visitors are asked to sign in. The Employee cannot open the Admin dashboard. |
| Employee ownership | Sign in as two different Employees. Create a ticket as the first. Use the second account to look for it in **My Tickets** and **Ticket details and shared history**. | Only the first account can see the ticket. The history actor identifies the enrolled account. |
| Stale version after reopening | Leave a Close form open in one tab. Reopen the same ticket in another session and have the technician resolve it again. Submit Close from the first tab. | The stale form reports a version conflict. The ticket remains `resolved` after the second fix. A fresh form can close it. |
| Reassignment | Enroll two Technicians. Assign an open ticket to the first one. In **Reassign In-Progress Ticket**, pick the second and provide a reason. | The ticket stays `in_progress`. The old technician loses access, the new one gains it, and history shows the old and new technician and the reason. |
| Pagination and priority | Create more than 25 tickets, including two high-priority tickets created at different times. Navigate to the next page and change a filter. Review the Technician queue. | Tables display up to 25 rows per page, totals cover all matching rows, filters restart pagination, and older tickets appear first within the same priority. |
| Migration and restore | Run the migration on a copy of an older database. Create an online backup and point a test instance at a separate restored copy. | Existing tickets and history are present, the updated app can use them, and the source database remains available. |
