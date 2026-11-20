
import sqlite3
import streamlit as st


from src.ticket_service import get_tickets, update_ticket_status



# =====================================
# LESSON 3.3.1: TECHNICIAN DASHBOARD
# =====================================

# STEP 1: Page configuration
st.set_page_config(
    page_title="Technician Dashboard",
    page_icon="🔧",
    layout="wide"
)

# STEP 2: Simulated technician
TECHNICIAN_ID = 2

st.title("Technician Dashboard")
st.write("Welcome, Technician Binh!")

st.sidebar.info(
    "Demo Mode: Technician Binh (User ID = 2)"
)

st.caption(
    "Demo account only. Authentication is not implemented."
)

if "resolve_success" in st.session_state:
    st.success(st.session_state.pop("resolve_success"))
    st.session_state.pop("resolve_ticket", None)
    st.session_state.pop("resolve_note", None)


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

    tickets = get_tickets(
        viewer_id=TECHNICIAN_ID,
        keyword=keyword,
        status=selected_status
    )

except (ValueError, FileNotFoundError, sqlite3.Error) as error:
    st.error(f"Cannot load assigned tickets: {error}")
    st.stop()


# =====================================
# STEP 5: DISPLAY TICKET METRICS
# =====================================

total_tickets = len(tickets)

in_progress_count = sum(
    1 for ticket in tickets
    if ticket[2] == "in_progress"
)

metric1, metric2 = st.columns(2)

with metric1:
    st.metric("Matching Assigned Tickets", total_tickets)

with metric2:
    st.metric("In Progress", in_progress_count)


# =====================================
# STEP 6: DISPLAY TICKET TABLE
# =====================================

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
            "Technician": ticket[6]
        })

    st.dataframe(
        ticket_data,
        hide_index=True,
        width="stretch"
    )

else:
    st.info(
        "No assigned tickets match your search or filters."
    )


# =====================================
# LESSON 3.3.2: RESOLVE TICKET
# =====================================

st.divider()
st.header("Resolve Ticket")

# STEP 1: Load tickets ready for resolution
try:
    active_tickets = get_tickets(
        viewer_id=TECHNICIAN_ID,
        status="in_progress"
    )

except (ValueError, FileNotFoundError, sqlite3.Error) as error:
    st.error(f"Cannot load active tickets: {error}")
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
    if submitted:

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
                    actor_id=TECHNICIAN_ID,
                    note=note
                )

            except (
                ValueError,
                PermissionError,
                RuntimeError,
                FileNotFoundError,
                sqlite3.Error
            ) as error:
                st.error(f"Cannot resolve ticket: {error}")

            else:
                st.session_state["resolve_success"] = (
                    f"Ticket #{selected_ticket_id} "
                    "resolved successfully!"
                )

                st.rerun()
