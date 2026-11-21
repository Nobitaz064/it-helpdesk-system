# Sau Tuần 4 | UI dùng chung để phân trang, xem lịch sử và chống gửi form cũ.

"""Streamlit helpers shared by Employee, Technician, and Admin pages."""

import logging
import sqlite3

import streamlit as st

from src.ticket_service import get_ticket_detail, get_tickets


PAGE_SIZE = 25
SERVICE_ERRORS = (ValueError, PermissionError, RuntimeError, OSError, sqlite3.Error)
LOGGER = logging.getLogger(__name__)


def show_service_error(message, error):
    if isinstance(error, (sqlite3.Error, OSError)) and not isinstance(error, PermissionError):
        # Log tên thao tác và loại exception để tra lỗi mà giữ kín nội dung ticket.
        LOGGER.error("%s (%s)", message, type(error).__name__)
        st.error(f"{message}. Try again or contact IT if the problem persists.")
    else:
        st.error(f"{message}: {error}")


def ticket_page(scope, viewer_id, **filters):
    """Read one page and a lookahead row using the same access filters."""
    key = f"{scope}_page"
    criteria = (viewer_id, tuple(filters.items()))
    previous_criteria, previous_offset = st.session_state.get(key, (None, 0))
    # Đổi tài khoản hoặc bộ lọc thì quay lại trang đầu.
    offset = previous_offset if previous_criteria == criteria else 0
    # Đọc thêm một dòng để biết còn trang sau. Chỉ hiển thị PAGE_SIZE dòng.
    rows = get_tickets(viewer_id, limit=PAGE_SIZE + 1, offset=offset, **filters)
    # Dữ liệu có thể thay đổi giữa hai lần bấm, khiến trang đang xem trống.
    if not rows and offset:
        offset = 0
        rows = get_tickets(viewer_id, limit=PAGE_SIZE + 1, **filters)
    st.session_state[key] = (criteria, offset)

    has_next = len(rows) > PAGE_SIZE
    if offset or has_next:
        previous, following, counter = st.columns([1, 1, 3])

        def move(new_offset):
            st.session_state[key] = (criteria, new_offset)

        previous.button(
            "Previous", key=f"{scope}_previous", disabled=offset == 0,
            on_click=move, args=(max(0, offset - PAGE_SIZE),),
        )
        following.button(
            "Next", key=f"{scope}_next", disabled=not has_next,
            on_click=move, args=(offset + PAGE_SIZE,),
        )
        counter.caption(f"Page {offset // PAGE_SIZE + 1}")
    return rows[:PAGE_SIZE]


# Đổi tuple từ service sang cột có tên để ba dashboard hiển thị cùng định dạng.
def show_ticket_table(rows, empty_message):
    if not rows:
        st.info(empty_message)
        return
    st.dataframe(
        [
            {
                "ID": ticket_id,
                "Title": title,
                "Status": status,
                "Priority": priority,
                "Reporter": reporter,
                "Category": category,
                "Technician": technician or "Unassigned",
            }
            for ticket_id, title, status, priority, reporter, category, technician in rows
        ],
        hide_index=True,
        width="stretch",
    )


def expected_version(scope, viewer_id, ticket_id):
    # Dùng version lúc người dùng nhìn thấy form. Đọc lại lúc submit sẽ lấy version mới
    # và có thể bỏ qua xung đột. Đối chiếu owner để tránh dùng dữ liệu của phiên trước.
    owner, versions = st.session_state.get(f"{scope}_versions", (None, {}))
    version = versions.get(ticket_id) if owner == viewer_id else None
    if version is None:
        raise RuntimeError("Ticket selection changed. Refresh and select the ticket again.")
    return version


def remember_versions(scope, viewer_id, rows):
    """Store versions sent on this render for use on the next form submission."""
    # Lưu theo form, user và ID ticket. ticket[7] là cột VERSION khi include_version=True.
    st.session_state[f"{scope}_versions"] = (
        viewer_id,
        {ticket[0]: ticket[7] for ticket in rows},
    )


def show_ticket_detail(scope, viewer_id):
    with st.container(border=True):
        st.subheader("Ticket details and shared history")
        ticket_id = st.number_input(
            "Ticket ID", min_value=1, step=1, value=None, key=f"{scope}_detail"
        )
        if ticket_id is None:
            return
        try:
            # Service kiểm tra phạm vi trước khi trả mô tả và lịch sử cho UI.
            details = get_ticket_detail(viewer_id, ticket_id)
        except SERVICE_ERRORS as error:
            show_service_error("Cannot load ticket details", error)
            return
        if details is None:
            st.info("Ticket unavailable.")
            return
        st.subheader(f"#{details['ticket_id']} {details['title']}")
        st.caption(
            f"{details['status']} · {details['priority']} · {details['category']} · "
            f"{details['technician'] or 'Unassigned'}"
        )
        st.caption(f"Created {details['created_at']} · Updated {details['updated_at']}")
        st.text(details["description"])
        if details["history"]:
            st.dataframe(
                [
                    {
                        "Time": event["changed_at"],
                        "By": event["actor_name"],
                        "From": event["old_status"],
                        "To": event["new_status"],
                        "Note": event["note"],
                        "Previous technician": event["old_assignee"],
                        "New technician": event["new_assignee"],
                    }
                    for event in details["history"]
                ],
                hide_index=True,
                width="stretch",
            )
