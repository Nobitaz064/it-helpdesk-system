
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
from src.ticket_service import get_ticket_counts, update_ticket_status



# =====================================
# LESSON 3.3.1: TECHNICIAN DASHBOARD
# =====================================

# STEP 1: Page configuration
st.set_page_config(
    page_title="Technician Dashboard",
    page_icon="🔧",
    layout="wide"
)

# Company pilot: check the role before querying the technician's assigned tickets.
technician_id = require_user("technician")
st.title("Technician Dashboard")

if "resolve_success" in st.session_state:
    st.success(st.session_state.pop("resolve_success"))
    st.session_state["resolve_ticket"] = None
    st.session_state["resolve_note"] = ""


# =====================================
# STEP 3: SEARCH AND FILTER
# =====================================

st.subheader("My Assigned Tickets")

col1, col2 = st.columns(2)

with col1:
    keyword = st.text_input(
        "Search Tickets",
        max_chars=100,
        placeholder="Enter a keyword..."
    )

with col2:
    status_filter = st.selectbox(
        "Filter by Status",
        options=[
            "All",
            "open",
            "in_progress",
            "resolved",
            "closed"
        ]
    )


# =====================================
# STEP 4: GET ASSIGNED TICKETS
# =====================================

try:
    selected_status = (
        None if status_filter == "All"
        else status_filter
    )

    tickets = ticket_page(
        "technician_tickets", technician_id,
        keyword=keyword,
        status=selected_status,
        sort="priority",
    )
    counts = get_ticket_counts(
        technician_id, keyword=keyword, status=selected_status
    )

except SERVICE_ERRORS as error:
    show_service_error("Cannot load assigned tickets", error)
    st.stop()


# =====================================
# STEP 5: DISPLAY TICKET METRICS
# =====================================

metric1, metric2 = st.columns(2)

with metric1:
    st.metric("Matching Assigned Tickets", sum(counts.values()))

with metric2:
    st.metric("In Progress", counts["in_progress"])


# =====================================
# STEP 6: DISPLAY TICKET TABLE
# =====================================

show_ticket_table(tickets, "No assigned tickets match your search or filters.")
show_ticket_detail("technician", technician_id)


# =====================================
# LESSON 3.3.2: RESOLVE TICKET
# =====================================

st.divider()
st.header("Resolve Ticket")

# STEP 1: Load tickets ready for resolution
try:
    active_tickets = ticket_page(
        "technician_resolve", technician_id,
        status="in_progress", sort="priority", include_version=True,
    )

except SERVICE_ERRORS as error:
    show_service_error("Cannot load active tickets", error)
    st.stop()


# STEP 2: Check available tickets
if not active_tickets:
    st.info("No tickets are currently in progress.")

else:
    ticket_titles = {
        ticket[0]: ticket[1]
        for ticket in active_tickets
    }

    # STEP 3: Create resolution form
    with st.form("resolve_ticket_form"):

        selected_ticket_id = st.selectbox(
            "Select Ticket",
            options=list(ticket_titles.keys()),
            index=None,
            format_func=lambda tid: (
                f"#{tid} - {ticket_titles[tid]}"
            ),
            key="resolve_ticket",
        )

        note = st.text_area(
            "Troubleshooting Notes",
            max_chars=500,
            placeholder=(
                "Describe the problem, troubleshooting "
                "steps, and final solution..."
            ),
            key="resolve_note",
        )

        submitted = st.form_submit_button(
            "Mark as Resolved"
        )

    # STEP 4: Process resolution
    if not submitted:
        remember_versions("technician_resolve", technician_id, active_tickets)
    else:

        if selected_ticket_id is None:
            st.error("Select a ticket to resolve.")

        elif not note.strip():
            st.error(
                "Troubleshooting notes cannot be empty."
            )

        else:
            try:
                update_ticket_status(
                    ticket_id=selected_ticket_id,
                    new_status="resolved",
                    actor_id=technician_id,
                    note=note,
                    expected_version=expected_version(
                        "technician_resolve", technician_id, selected_ticket_id
                    ),
                )

            except SERVICE_ERRORS as error:
                show_service_error("Cannot resolve ticket", error)

            else:
                st.session_state["resolve_success"] = (
                    f"Ticket #{selected_ticket_id} "
                    "resolved successfully!"
                )

                st.rerun()
