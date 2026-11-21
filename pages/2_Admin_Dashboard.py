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
from src.ticket_service import assign_ticket, get_ticket_counts, reassign_ticket


# Lesson 3.4: view the queue and assign technicians.
st.set_page_config(page_title="Admin Dashboard", page_icon="📋", layout="wide")
admin_id = require_user("admin")
st.title("Admin Dashboard")

for scope in ("assignment", "reassignment"):
    message = st.session_state.pop(f"{scope}_success", None)
    if message:
        st.success(message)
        st.session_state[f"{scope}_ticket"] = None
        st.session_state[f"{scope}_technician"] = None
        st.session_state[f"{scope}_note"] = ""


st.subheader("Ticket Overview")

try:
    counts = get_ticket_counts(admin_id)
except SERVICE_ERRORS as error:
    show_service_error("Cannot load dashboard metrics", error)
    st.stop()

total, open_column, in_progress, resolved, closed = st.columns(5)
total.metric("Total", sum(counts.values()))
open_column.metric("Open", counts["open"])
in_progress.metric("In Progress", counts["in_progress"])
resolved.metric("Resolved", counts["resolved"])
closed.metric("Closed", counts["closed"])

st.divider()
st.header("All Tickets")
search_column, status_column, priority_column = st.columns(3)

with search_column:
    keyword = st.text_input("Search Tickets", max_chars=100)
with status_column:
    status = st.selectbox(
        "Filter by Status",
        ["All", "open", "in_progress", "resolved", "closed"],
    )
with priority_column:
    priority = st.selectbox(
        "Filter by Priority",
        ["All", "low", "medium", "high", "critical"],
    )

try:
    tickets = ticket_page(
        "admin_tickets", admin_id, keyword=keyword,
        status=None if status == "All" else status,
        priority=None if priority == "All" else priority,
    )
except SERVICE_ERRORS as error:
    show_service_error("Cannot load tickets", error)
    st.stop()

show_ticket_table(tickets, "No tickets match your search or filters.")
show_ticket_detail("admin", admin_id)

try:
    with closing(get_connection()) as conn:
        technicians = dict(conn.execute(
            """
            SELECT U.USER_ID, U.FULL_NAME
            FROM USERS AS U
            WHERE U.ROLE = 'technician'
                AND (
                    EXISTS (SELECT 1 FROM HELPDESK_SETTINGS
                            WHERE KEY = 'auth_mode' AND VALUE = 'demo')
                    OR EXISTS (SELECT 1 FROM USER_IDENTITIES WHERE USER_ID = U.USER_ID)
                )
            ORDER BY U.FULL_NAME, U.USER_ID
            """
        ))
except SERVICE_ERRORS as error:
    show_service_error("Cannot load technicians", error)
    st.stop()


def show_assignment_form(scope, *, reassign):
    action_name = "Reassign Ticket" if reassign else "Assign Ticket"
    st.divider()
    st.header("Reassign In-Progress Ticket" if reassign else action_name)

    if not technicians:
        st.info("No technicians are available.")
        return
    try:
        candidates = ticket_page(
            scope, admin_id, status="in_progress" if reassign else "open",
            sort="priority", include_version=True,
        )
    except SERVICE_ERRORS as error:
        show_service_error("Cannot load assignment options", error)
        return

    candidates = [row for row in candidates if (row[6] is not None) == reassign]
    if not candidates:
        message = "No assigned tickets are in progress." if reassign else "No unassigned open tickets."
        st.info(message)
        return
    titles = {row[0]: row[1] for row in candidates}
    with st.form(f"{scope}_form"):
        ticket_id = st.selectbox(
            "Select Active Ticket" if reassign else "Select Ticket",
            options=list(titles),
            index=None,
            format_func=lambda value: f"#{value} - {titles[value]}",
            key=f"{scope}_ticket",
        )
        technician_id = st.selectbox(
            "Select New Technician" if reassign else "Select Technician",
            options=list(technicians),
            index=None,
            format_func=lambda value: f"{technicians[value]} (#{value})",
            key=f"{scope}_technician",
        )
        note = st.text_area(
            "Reason for Reassignment" if reassign else "Assignment Note (optional)",
            max_chars=500,
            key=f"{scope}_note",
        )
        submitted = st.form_submit_button(action_name)

    if not submitted:
        remember_versions(scope, admin_id, candidates)
        return
    if ticket_id is None or technician_id is None:
        st.error("Select both a ticket and a technician.")
        return

    # Company pilot: the active-ticket form reuses the UI and invokes the handoff rule.
    operation = reassign_ticket if reassign else assign_ticket
    if not reassign:
        note = note.strip() or "Assigned to technician"
    try:
        operation(
            ticket_id=ticket_id,
            technician_id=technician_id,
            admin_id=admin_id,
            note=note,
            expected_version=expected_version(scope, admin_id, ticket_id),
        )
    except SERVICE_ERRORS as error:
        show_service_error(f"Cannot {action_name.lower()}", error)
    else:
        verb = "reassigned" if reassign else "assigned"
        st.session_state[f"{scope}_success"] = f"Ticket #{ticket_id} {verb} to {technicians[technician_id]}."
        st.rerun()


show_assignment_form("assignment", reassign=False)
show_assignment_form("reassignment", reassign=True)
