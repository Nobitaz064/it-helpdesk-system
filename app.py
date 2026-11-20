
import sqlite3
from contextlib import closing

import streamlit as st

from src.db import get_connection

from src.ticket_service import (
    create_ticket,
    get_tickets,
    update_ticket_status
)



# =====================================
# LESSON 3.2: EMPLOYEE DASHBOARD
# =====================================

# STEP 1: Page configuration
st.set_page_config(
    page_title="IT Helpdesk System",
    page_icon="🛠️",
    layout="wide"
)


# Display ticket review result
review_message = st.session_state.pop(
    "employee_review_success", None
)

if review_message:
    st.success(review_message)
    st.session_state.pop("employee_review_ticket", None)
    st.session_state.pop("employee_review_action", None)
    st.session_state.pop("employee_review_note", None)


# STEP 2: Simulated employee
EMPLOYEE_ID = 1

st.title("IT Helpdesk Ticket Management System")
st.subheader("Employee Dashboard")

st.sidebar.info(
    "Demo Mode: Employee An (User ID = 1)"
)

st.caption(
    "This dashboard uses a sample employee account. "
    "Login authentication is not implemented yet."
)


# =====================================
# STEP 3: LOAD TICKET CATEGORIES
# =====================================

try:
    with closing(get_connection()) as conn:
        category_rows = conn.execute("""
            SELECT CATEGORY_ID, CATEGORY_NAME
            FROM CATEGORIES
            ORDER BY CATEGORY_ID
        """).fetchall()

except (FileNotFoundError, sqlite3.Error) as error:
    st.error(f"Cannot load categories: {error}")
    st.stop()

categories = {
    category_id: category_name
    for category_id, category_name in category_rows
}

if not categories:
    st.error("No ticket categories are available.")
    st.stop()


# =====================================
# STEP 4: CREATE TICKET FORM
# =====================================

st.header("Create New Ticket")

with st.form("create_ticket_form", clear_on_submit=True):

    title = st.text_input(
        "Ticket Title",
        max_chars=120,
        placeholder="Example: Cannot connect to Wi-Fi"
    )

    description = st.text_area(
        "Description",
        placeholder="Describe the problem in detail..."
    )

    category_id = st.selectbox(
        "Category",
        options=list(categories.keys()),
        format_func=lambda cid: categories[cid]
    )

    priority = st.selectbox(
        "Priority",
        options=["low", "medium", "high", "critical"],
        index=1
    )

    submitted = st.form_submit_button(
        "Submit Ticket"
    )


# =====================================
# STEP 5: PROCESS FORM SUBMISSION
# =====================================

if submitted:

    try:
        ticket_id = create_ticket(
            title=title,
            description=description,
            reporter_id=EMPLOYEE_ID,
            category_id=category_id,
            priority=priority
        )

    except (ValueError, FileNotFoundError, sqlite3.Error) as error:
        st.error(f"Cannot create ticket: {error}")

    else:
        st.success(
            f"Ticket #{ticket_id} created successfully!"
        )


# =====================================
# STEP 6: DISPLAY EMPLOYEE TICKETS
# =====================================

st.divider()
st.header("My Tickets")

try:
    tickets = get_tickets(EMPLOYEE_ID)

    if tickets:

        ticket_data = []

        for ticket in tickets:
            ticket_data.append({
                "ID": ticket[0],
                "Title": ticket[1],
                "Status": ticket[2],
                "Priority": ticket[3],
                "Reporter": ticket[4],
                "Category": ticket[5],
                "Technician": ticket[6] or "Unassigned"
            })

        st.dataframe(
            ticket_data,
            hide_index=True,
            width="stretch"
        )

    else:
        st.info("You have not created any tickets yet.")

except (ValueError, FileNotFoundError, sqlite3.Error) as error:
    st.error(f"Cannot load tickets: {error}")


# =====================================
# LESSON 3.5: CLOSE / REOPEN TICKET
# =====================================

st.divider()
st.header("Review Resolved Tickets")

# STEP 1: Load resolved tickets belonging to Employee
try:
    resolved_tickets = get_tickets(
        viewer_id=EMPLOYEE_ID,
        status="resolved"
    )

except (ValueError, FileNotFoundError, sqlite3.Error) as error:
    st.error(f"Cannot load resolved tickets: {error}")
    st.stop()


# STEP 2: Check if there are tickets to review
if not resolved_tickets:
    st.info("No resolved tickets are waiting for your review.")

else:
    ticket_titles = {
        ticket[0]: ticket[1]
        for ticket in resolved_tickets
    }

    # STEP 3: Create review form
    with st.form("employee_review_form"):

        selected_ticket_id = st.selectbox(
            "Select Resolved Ticket",
            options=list(ticket_titles.keys()),
            index=None,
            format_func=lambda tid: (
                f"#{tid} - {ticket_titles[tid]}"
            ),
            key="employee_review_ticket",
        )

        action = st.radio(
            "Your Decision",
            options=[
                "Close Ticket",
                "Reopen Ticket"
            ],
            index=None,
            horizontal=True,
            key="employee_review_action",
        )

        note = st.text_area(
            "Confirmation / Reopen Note",
            max_chars=500,
            placeholder="Explain your decision...",
            key="employee_review_note",
        )

        submitted = st.form_submit_button(
            "Submit Decision"
        )

    # STEP 4: Validate and process decision
    if submitted:

        if selected_ticket_id is None or action is None:
            st.error("Please select a ticket and decision.")

        elif not note.strip():
            st.error("Please provide a note.")

        else:
            new_status = (
                "closed"
                if action == "Close Ticket"
                else "in_progress"
            )

            try:
                update_ticket_status(
                    ticket_id=selected_ticket_id,
                    new_status=new_status,
                    actor_id=EMPLOYEE_ID,
                    note=note
                )

            except (
                ValueError,
                PermissionError,
                RuntimeError,
                FileNotFoundError,
                sqlite3.Error
            ) as error:
                st.error(f"Cannot update ticket: {error}")

            else:
                st.session_state["employee_review_success"] = (
                    f"Ticket #{selected_ticket_id} "
                    f"updated to {new_status} successfully!"
                )

                st.rerun()
