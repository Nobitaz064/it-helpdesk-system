
from contextlib import closing

import streamlit as st

from src.auth import require_user
from src.dashboard_ui import (
    SERVICE_ERRORS,
    expected_version,
    remember_versions,
    show_service_error,
    show_ticket_detail,
    show_ticket_table,
    ticket_page,
)
from src.db import get_connection

from src.ticket_service import (
    create_ticket,
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

# Company pilot: resolve the user before loading Employee data or accepting a form.
employee_id = require_user("employee", landing=True)


# Display ticket creation result after the form version has changed.
create_message = st.session_state.pop("employee_create_success", None)

if create_message:
    st.success(create_message)


# Display ticket review result
review_message = st.session_state.pop(
    "employee_review_success", None
)

if review_message:
    st.success(review_message)
    st.session_state["employee_review_ticket"] = None
    st.session_state["employee_review_action"] = None
    st.session_state["employee_review_note"] = ""


st.title("IT Helpdesk Ticket Management System")
st.subheader("Employee Dashboard")


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

except SERVICE_ERRORS as error:
    show_service_error("Cannot load categories", error)
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

# Week 4: keep the same form after validation errors to preserve the user's draft.
create_form_version = st.session_state.get("employee_create_form_version", 0)
with st.form(f"create_ticket_form_{create_form_version}"):

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
            reporter_id=employee_id,
            category_id=category_id,
            priority=priority
        )

    except SERVICE_ERRORS as error:
        show_service_error("Cannot create ticket", error)

    else:
        st.session_state["employee_create_success"] = (
            f"Ticket #{ticket_id} created successfully!"
        )
        # Use a fresh form ID so the browser discards the submitted draft.
        st.session_state["employee_create_form_version"] = create_form_version + 1
        st.rerun()


# =====================================
# STEP 6: DISPLAY EMPLOYEE TICKETS
# =====================================

st.divider()
st.header("My Tickets")

try:
    tickets = ticket_page("employee_tickets", employee_id)
    show_ticket_table(tickets, "You have not created any tickets yet.")
except SERVICE_ERRORS as error:
    show_service_error("Cannot load tickets", error)

show_ticket_detail("employee", employee_id)


# =====================================
# LESSON 3.5: CLOSE / REOPEN TICKET
# =====================================

st.divider()
st.header("Review Resolved Tickets")

# STEP 1: Load resolved tickets belonging to Employee
try:
    resolved_tickets = ticket_page(
        "employee_review", employee_id, status="resolved", include_version=True
    )

except SERVICE_ERRORS as error:
    show_service_error("Cannot load resolved tickets", error)
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
    if not submitted:
        # Company pilot: store what the form displayed for the next submission.
        remember_versions("employee_review", employee_id, resolved_tickets)
    else:

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
                    actor_id=employee_id,
                    note=note,
                    expected_version=expected_version("employee_review", employee_id, selected_ticket_id),
                )

            except SERVICE_ERRORS as error:
                show_service_error("Cannot update ticket", error)

            else:
                st.session_state["employee_review_success"] = (
                    f"Ticket #{selected_ticket_id} "
                    f"updated to {new_status} successfully!"
                )

                st.rerun()
