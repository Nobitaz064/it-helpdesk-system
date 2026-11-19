import sqlite3
from contextlib import closing

import streamlit as st

from src.db import get_connection
from src.ticket_service import assign_ticket, get_tickets


ADMIN_ID = 3

st.set_page_config(page_title="Admin Dashboard", page_icon="📋", layout="wide")
st.title("Admin Dashboard")
st.sidebar.info("Demo Mode: Admin Chi (User ID = 3)")
st.caption("This dashboard uses a demo account without login authentication.")

if "assignment_success" in st.session_state:
    st.success(st.session_state.pop("assignment_success"))
    for key in ("assignment_ticket", "assignment_technician", "assignment_note"):
        st.session_state.pop(key, None)


# =====================================
# LESSON 3.4.3: DASHBOARD METRICS
# =====================================

st.subheader("Ticket Overview")

# STEP 1: Load all tickets
try:
    all_tickets = get_tickets(viewer_id=ADMIN_ID)

except (ValueError, FileNotFoundError, sqlite3.Error) as error:
    st.error(f"Cannot load dashboard metrics: {error}")
    st.stop()

# STEP 2: Count tickets by status
total_count = len(all_tickets)

statuses = [ticket[2] for ticket in all_tickets]

open_count = statuses.count("open")
in_progress_count = statuses.count("in_progress")
resolved_count = statuses.count("resolved")
closed_count = statuses.count("closed")

# STEP 3: Display dashboard metrics
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total", total_count)
col2.metric("Open", open_count)
col3.metric("In Progress", in_progress_count)
col4.metric("Resolved", resolved_count)
col5.metric("Closed", closed_count)

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
    tickets = get_tickets(
        viewer_id=ADMIN_ID,
        keyword=keyword,
        status=None if status == "All" else status,
        priority=None if priority == "All" else priority,
    )
except (ValueError, FileNotFoundError, sqlite3.Error) as error:
    st.error(f"Cannot load tickets: {error}")
    st.stop()

if tickets:
    st.dataframe(
        [
            {
                "ID": ticket_id,
                "Title": title,
                "Status": ticket_status,
                "Priority": ticket_priority,
                "Reporter": reporter,
                "Category": category,
                "Technician": technician or "Unassigned",
            }
            for ticket_id, title, ticket_status, ticket_priority, reporter, category, technician in tickets
        ],
        hide_index=True,
        width="stretch",
    )
else:
    st.info("No tickets match your search or filters.")

st.divider()
st.header("Assign Ticket")

try:
    open_tickets = get_tickets(viewer_id=ADMIN_ID, status="open")
    with closing(get_connection()) as conn:
        technicians = dict(conn.execute(
            """
            SELECT USER_ID, FULL_NAME
            FROM USERS
            WHERE ROLE = ?
            ORDER BY FULL_NAME, USER_ID
            """,
            ("technician",),
        ))
except (ValueError, FileNotFoundError, sqlite3.Error) as error:
    st.error(f"Cannot load assignment options: {error}")
    st.stop()

ticket_titles = {
    ticket[0]: ticket[1] for ticket in open_tickets if ticket[6] is None
}

if not ticket_titles:
    st.info("No unassigned open tickets.")
    st.stop()

if not technicians:
    st.info("No technicians are available.")
    st.stop()

with st.form("assign_ticket_form"):
    ticket_id = st.selectbox(
        "Select Ticket",
        options=list(ticket_titles),
        index=None,
        format_func=lambda ticket_id: f"#{ticket_id} - {ticket_titles[ticket_id]}",
        key="assignment_ticket",
    )
    technician_id = st.selectbox(
        "Select Technician",
        options=list(technicians),
        index=None,
        format_func=lambda technician_id: f"{technicians[technician_id]} (#{technician_id})",
        key="assignment_technician",
    )
    note = st.text_area("Assignment Note (optional)", max_chars=500, key="assignment_note")
    submitted = st.form_submit_button("Assign Ticket")

if submitted:
    if ticket_id is None or technician_id is None:
        st.error("Select both a ticket and a technician.")
    else:
        try:
            assign_ticket(
                ticket_id=ticket_id,
                technician_id=technician_id,
                admin_id=ADMIN_ID,
                note=note.strip() or "Assigned to technician",
            )
        except (ValueError, PermissionError, RuntimeError, FileNotFoundError, sqlite3.Error) as error:
            st.error(f"Cannot assign ticket: {error}")
        else:
            st.session_state["assignment_success"] = (
                f"Ticket #{ticket_id} assigned to {technicians[technician_id]}."
            )
            st.rerun()
