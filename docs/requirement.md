# IT Helpdesk & Asset Management System

## 1. Project Overview

The IT Helpdesk & Asset Management System is a web application designed to help a small company manage IT support requests, computer equipment, and troubleshooting activities.

## 2. Project Objectives

- Manage IT support tickets.
- Track ticket status and priority.
- Assign tickets to technicians.
- Manage IT assets.
- Record ticket resolution history.
- Analyze IT support performance using Power BI.

## 3. User Roles

### Employee
- Create support tickets.
- View submitted tickets.
- Check ticket status.

### Technician
- View assigned tickets.
- Update ticket status.
- Record troubleshooting notes.
- Resolve technical issues.

### Admin
- Manage users and IT assets.
- View all support tickets.
- Monitor system activity.
- Analyze support reports.

## 4. Functional Requirements

- FR01: The system shall allow users to create support tickets.
- FR02: The system shall allow users to view and search tickets.
- FR03: The system shall support ticket priority levels.
- FR04: The system shall allow technicians to update ticket status.
- FR05: The system shall record ticket history.
- FR06: The system shall manage IT assets.
- FR07: The system shall associate tickets with relevant assets.
- FR08: The system shall provide data for Power BI reports.

## 5. Non-Functional Requirements

- NFR01: The application should have a simple interface.
- NFR02: The database should maintain data integrity.
- NFR03: The application should validate user input.
- NFR04: Database queries should use parameterized statements.
- NFR05: The project should include documentation and test cases.

## 6. Technology Stack

- Programming Language: Python
- Database: SQLite
- User Interface: Streamlit
- Data Analysis: SQL, Pandas, Power BI
- Version Control: Git and GitHub

## 7. Project Scope

The initial version will simulate the IT support process of a small company. It will use sample data and will not initially integrate with real corporate systems.


## 8. Business Rules

- BR01: Every ticket must have a unique ID.
- BR02: Every new ticket must have the status Open.
- BR03: A ticket can only be assigned to a technician.
- BR04: Only authorized users can update ticket status.
- BR05: Every ticket status change must be recorded.
- BR06: Employees can only view their own tickets.
