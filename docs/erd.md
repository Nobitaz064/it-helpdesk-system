
# Database Design — IT Helpdesk System

## 1. Entities

The system has four main entities:

- USERS
- CATEGORIES
- TICKETS
- TICKET_HISTORY


## 2. Primary Keys

- USERS: user_id
- CATEGORIES: category_id
- TICKETS: ticket_id
- TICKET_HISTORY: history_id

## 3. Foreign Keys

- TICKETS.reporter_id -> USERS.user_id
- TICKETS.assigned_to -> USERS.user_id
- TICKETS.category_id -> CATEGORIES.category_id
- TICKET_HISTORY.ticket_id -> TICKETS.ticket_id
- TICKET_HISTORY.changed_by -> USERS.user_id