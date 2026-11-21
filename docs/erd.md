
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
- TICKET_HISTORY.old_assignee_id -> USERS.user_id
- TICKET_HISTORY.new_assignee_id -> USERS.user_id

## 4. Company pilot schema

- `USER_IDENTITIES` maps each OIDC issuer and subject pair to one local `USERS.user_id`.
- `HELPDESK_SETTINGS` records the database sign-in mode.
- `TICKETS.version` advances with each status change or assignment. Forms submit
  the version that was displayed so another update cannot silently be overwritten.
- The added history columns record both technicians on reassignment.
  Earlier history rows keep their original note and can have empty assignee columns.
