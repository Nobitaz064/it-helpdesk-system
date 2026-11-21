# Tuần 3 | Bài 3.2 — Employee tạo/xem ticket. Bài 3.5 — Đóng hoặc mở lại.
# Tuần 4 | Giữ bản nháp khi lỗi và reset form sau khi ghi thành công.
# Sau Tuần 4 | Xác thực, phân trang, lịch sử và kiểm tra version khi submit.

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
# Tuần 3 | Bài 3.2 — Employee Dashboard
# =====================================

# STEP 1: Page configuration
st.set_page_config(
    page_title="IT Helpdesk System",
    page_icon="🛠️",
    layout="wide"
)

# Sau Tuần 4 | Lấy ID từ xác thực trước khi tải dữ liệu hoặc xử lý form.
employee_id = require_user("employee", landing=True)


# Tuần 4 | pop() hiển thị thông báo một lần sau khi Streamlit chạy lại file.
create_message = st.session_state.pop("employee_create_success", None)

if create_message:
    st.success(create_message)


# Tuần 4 | Đặt lại giá trị widget trước khi dựng form review ở lượt chạy mới.
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

# Dùng ID làm giá trị gửi về service và tên danh mục làm nhãn hiển thị.
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

# Tuần 4 | Giữ nguyên ID form khi validation lỗi để người dùng sửa bản nháp.
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

    # Gửi ID từ phiên đăng nhập để ticket gắn đúng người tạo.
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
        # Chỉ đổi ID sau khi service đã commit. Lượt chạy sau sẽ dựng form trống.
        st.session_state["employee_create_form_version"] = create_form_version + 1
        st.rerun()


# =====================================
# STEP 6: DISPLAY EMPLOYEE TICKETS
# =====================================

st.divider()
st.header("My Tickets")

try:
    # Sau Tuần 4 | Trang chỉ lấy một nhóm ticket. Service lọc theo employee_id.
    tickets = ticket_page("employee_tickets", employee_id)
    show_ticket_table(tickets, "You have not created any tickets yet.")
except SERVICE_ERRORS as error:
    show_service_error("Cannot load tickets", error)

show_ticket_detail("employee", employee_id)


# =====================================
# Tuần 3 | Bài 3.5 — Đóng hoặc mở lại ticket đã xử lý
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

    # Giữ ID ticket trong selectbox vì hai ticket có thể có cùng tiêu đề.
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
        # Sau Tuần 4 | Lưu version khi hiển thị. Lượt submit dùng chính version này.
        remember_versions("employee_review", employee_id, resolved_tickets)
    else:

        if selected_ticket_id is None or action is None:
            st.error("Please select a ticket and decision.")

        elif not note.strip():
            st.error("Please provide a note.")

        else:
            # Mở lại đưa ticket về in_progress và giữ người xử lý hiện tại.
            # Service kiểm tra người tạo, trạng thái, version và ghi lịch sử.
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
