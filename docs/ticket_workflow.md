
# Ticket Workflow

## 1. Overview

This document describes the lifecycle of IT support
tickets from creation to closure.

## 2. Ticket Status

- Open: A new ticket waiting for support.
- In Progress: A technician is working on the issue.
- Resolved: The issue has been fixed.
- Closed: The resolution has been confirmed.

## 3. Status Transitions

- Open -> In Progress
- In Progress -> Resolved
- Resolved -> Closed
- Resolved -> In Progress (Reopen)

## 4. Business Rules

- A new ticket starts with Open status.
- Only authorized technicians or admins can
  start working on a ticket.
- Technicians must record resolution notes.
- Employees can confirm the resolution
  of their own tickets.
- Every status change must be recorded
  in ticket history.

## 5. Exception Handling

- If the issue is not resolved, the ticket
  returns to In Progress.
- If the user cannot access the application,
  they can contact IT through another channel.
- If the system fails during an update,
  the database must not contain partial changes.
