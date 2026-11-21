# Tuần 3 | Bài 3.4 — Admin xem tổng quan, lọc và phân công ticket.
# Sau Tuần 4 | Xác thực, phân trang, thống kê SQL và chuyển người xử lý.

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


# Tuần 3 | Cấu hình trang trước khi tạo widget Streamlit.
st.set_page_config(page_title="Admin Dashboard", page_icon="📋", layout="wide")
# Sau Tuần 4 | Xác thực Admin trước khi đọc hàng đợi hay gọi thao tác phân công.
admin_id = require_user("admin")
st.title("Admin Dashboard")

# Reset đúng form vừa ghi thành công. Mỗi form có nhóm key riêng.
for scope in ("assignment", "reassignment"):
    message = st.session_state.pop(f"{scope}_success", None)
    if message:
        st.success(message)
        st.session_state[f"{scope}_ticket"] = None
        st.session_state[f"{scope}_technician"] = None
        st.session_state[f"{scope}_note"] = ""


st.subheader("Ticket Overview")

try:
    # Tổng quan dùng toàn bộ hàng đợi, nên vẫn giữ số tổng khi bảng phía dưới được lọc.
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
        # Sau Tuần 4 | DB công ty chỉ liệt kê Technician có danh tính đã đăng ký.
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

    # row[6] là tên Technician. Giao mới cần ticket chưa có người, chuyển giao cần đã có.
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

    # Tuần 3 | Giao mới đưa ticket open sang in_progress.
    # Sau Tuần 4 | Chuyển giao dùng cùng form, giữ in_progress và bắt buộc ghi lý do.
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
