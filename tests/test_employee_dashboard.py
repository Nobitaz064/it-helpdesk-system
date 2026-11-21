# Tuần 3 | Kiểm thử Employee Close/Reopen theo Bài 3.5 bằng Streamlit AppTest.
# Tuần 4 | Thêm ca kiểm thử giữ bản nháp và reset sau khi gửi thành công.
# Sau Tuần 4 | Kiểm tra form cũ sau khi ticket trải qua thêm một vòng xử lý.

import os
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from database import init_db
from src import db, ticket_service


DASHBOARD = Path(__file__).resolve().parents[1] / "app.py"


class TestEmployeeDashboard(unittest.TestCase):
    # DB tạm tách test khỏi dữ liệu demo. Hai ticket giúp phát hiện chọn nhầm khi form cũ.
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"HELPDESK_AUTH_MODE": "demo"}))
        temp_dir = self.enterContext(tempfile.TemporaryDirectory())
        db_path = Path(temp_dir) / "helpdesk.db"
        self.enterContext(patch.object(init_db, "DB_PATH", db_path))
        self.enterContext(patch.object(db, "DB_PATH", db_path))
        init_db.init_db()

        self.first_ticket = self.create_resolved_ticket("Cannot turn on PC")
        self.second_ticket = self.create_resolved_ticket("Cannot connect to Wi-Fi")

    def create_resolved_ticket(self, title, reporter_id=1):
        ticket_id = ticket_service.create_ticket(title, "Test issue", reporter_id, 2)
        ticket_service.assign_ticket(ticket_id, technician_id=2, admin_id=3)
        ticket_service.update_ticket_status(ticket_id, "resolved", 2, "Issue fixed.")
        return ticket_id

    def open_dashboard(self):
        dashboard = AppTest.from_file(str(DASHBOARD)).run()
        self.assertFalse(dashboard.exception)
        return dashboard

    def set_review(self, dashboard, action, note):
        dashboard.selectbox(key="employee_review_ticket").set_value(self.first_ticket)
        dashboard.radio(key="employee_review_action").set_value(action)
        dashboard.text_area(key="employee_review_note").set_value(note)

    def submit_review(self, dashboard):
        button = next(button for button in dashboard.button if button.label == "Submit Decision")
        button.click().run()
        self.assertFalse(dashboard.exception)

    # Tuần 4 | Cố tình để trống title để kiểm tra dữ liệu vẫn còn trước khi gửi lại.
    def test_creation_keeps_failed_draft_and_resets_after_success(self):
        dashboard = self.open_dashboard()
        description = "The printer on floor 2 shows a paper jam."
        dashboard.text_area[0].set_value(description)
        dashboard.selectbox[0].set_value(2)
        dashboard.selectbox[1].set_value("critical")
        submit = next(button for button in dashboard.button if button.label == "Submit Ticket")
        submit.click().run()

        self.assertFalse(dashboard.exception)
        self.assertEqual(dashboard.error[0].value, "Cannot create ticket: Ticket title cannot be empty")
        self.assertEqual(dashboard.text_area[0].value, description)
        self.assertEqual(dashboard.selectbox[0].value, 2)
        self.assertEqual(dashboard.selectbox[1].value, "critical")
        self.assertEqual(len(ticket_service.get_tickets(1)), 2)

        title = "Cannot print on floor 2"
        dashboard.text_input[0].set_value(title)
        submit = next(button for button in dashboard.button if button.label == "Submit Ticket")
        submit.click().run()

        self.assertFalse(dashboard.exception)
        self.assertFalse(dashboard.error)
        self.assertEqual(dashboard.text_input[0].value, "")
        self.assertEqual(dashboard.text_area[0].value, "")
        self.assertEqual(dashboard.selectbox[0].value, 1)
        self.assertEqual(dashboard.selectbox[1].value, "medium")
        self.assertEqual(dashboard.session_state["employee_create_form_version"], 1)
        ticket = dashboard.dataframe[0].value.set_index("Title").loc[title]
        self.assertEqual((ticket["Status"], ticket["Category"], ticket["Priority"]), (
            "open", "Hardware", "critical"
        ))
        self.assertIn("created successfully!", dashboard.success[0].value)

    def test_success_resets_form_while_another_ticket_is_available(self):
        dashboard = self.open_dashboard()
        self.set_review(dashboard, "Close Ticket", "I confirmed the fix.")
        self.submit_review(dashboard)

        self.assertEqual(
            dashboard.success[0].value,
            f"Ticket #{self.first_ticket} updated to closed successfully!",
        )
        ticket_picker = dashboard.selectbox(key="employee_review_ticket")
        self.assertEqual(ticket_picker.options, [f"#{self.second_ticket} - Cannot connect to Wi-Fi"])
        self.assertIsNone(ticket_picker.value)
        self.assertIsNone(dashboard.radio(key="employee_review_action").value)
        self.assertEqual(dashboard.text_area(key="employee_review_note").value, "")

    # Tuần 3 | Một phiên đóng ticket trước. Phiên cũ không được sửa ticket còn trong danh sách.
    def test_stale_selection_does_not_update_another_ticket(self):
        stale_dashboard = self.open_dashboard()
        self.set_review(stale_dashboard, "Reopen Ticket", "Issue still occurs.")

        current_dashboard = self.open_dashboard()
        self.set_review(current_dashboard, "Close Ticket", "I confirmed the fix.")
        self.submit_review(current_dashboard)

        self.submit_review(stale_dashboard)
        self.assertEqual(stale_dashboard.error[0].value, "Please select a ticket and decision.")
        self.assertEqual(ticket_service.get_ticket_by_id(1, self.first_ticket)[2], "closed")
        self.assertEqual(ticket_service.get_ticket_by_id(1, self.second_ticket)[2], "resolved")

    # Sau Tuần 4 | Trạng thái lại là resolved, nhưng version mới phải làm lần xác nhận cũ thất bại.
    def test_stale_review_rejects_same_status_after_reopen_and_resolve(self):
        stale = self.open_dashboard()
        self.set_review(stale, "Close Ticket", "Confirmation after the first fix.")

        ticket_service.update_ticket_status(self.first_ticket, "in_progress", 1, "Issue persists.")
        ticket_service.update_ticket_status(self.first_ticket, "resolved", 2, "Second fix.")
        self.submit_review(stale)

        self.assertIn("Ticket version conflict", stale.error[0].value)
        self.assertEqual(ticket_service.get_ticket_by_id(1, self.first_ticket)[2], "resolved")

    def test_missing_selection_and_blank_note_preserve_resolved_status(self):
        dashboard = self.open_dashboard()
        self.submit_review(dashboard)
        self.assertEqual(dashboard.error[0].value, "Please select a ticket and decision.")

        dashboard.selectbox(key="employee_review_ticket").set_value(self.first_ticket)
        self.submit_review(dashboard)
        self.assertEqual(dashboard.error[0].value, "Please select a ticket and decision.")

        self.set_review(dashboard, "Close Ticket", "   ")
        self.submit_review(dashboard)
        self.assertEqual(dashboard.error[0].value, "Please provide a note.")
        self.assertEqual(ticket_service.get_ticket_by_id(1, self.first_ticket)[2], "resolved")
        self.assertEqual(ticket_service.get_ticket_by_id(1, self.second_ticket)[2], "resolved")

    # Bài 3.5 | Kiểm tra cả quyền trên UI lẫn service, sau đó đối chiếu lịch sử đã lưu.
    def test_reporter_reopens_and_closes_ticket_with_history(self):
        with closing(db.get_connection()) as conn, conn:
            other_reporter = conn.execute(
                "INSERT INTO USERS (FULL_NAME, EMAIL, ROLE) VALUES (?, ?, ?)",
                ("Other Employee", "other@example.com", "employee"),
            ).lastrowid
        other_ticket = self.create_resolved_ticket("Other employee ticket", other_reporter)

        dashboard = self.open_dashboard()
        options = dashboard.selectbox(key="employee_review_ticket").options
        self.assertNotIn(f"#{other_ticket} - Other employee ticket", options)
        with self.assertRaises(PermissionError):
            ticket_service.update_ticket_status(
                self.first_ticket, "closed", other_reporter, "Wrong employee."
            )

        self.set_review(dashboard, "Reopen Ticket", "Issue still occurs.")
        self.submit_review(dashboard)
        self.assertEqual(
            dashboard.success[0].value,
            f"Ticket #{self.first_ticket} updated to in_progress successfully!",
        )
        self.assertEqual(ticket_service.get_ticket_by_id(2, self.first_ticket)[2], "in_progress")

        ticket_service.update_ticket_status(self.first_ticket, "resolved", 2, "Tested again.")
        dashboard.run()
        self.set_review(dashboard, "Close Ticket", "I confirmed the fix.")
        self.submit_review(dashboard)
        self.assertEqual(ticket_service.get_ticket_by_id(1, self.first_ticket)[2], "closed")
        self.assertEqual(ticket_service.get_ticket_by_id(other_reporter, other_ticket)[2], "resolved")

        with closing(db.get_connection()) as conn:
            history = conn.execute(
                """
                SELECT OLD_STATUS, NEW_STATUS, CHANGED_BY, NOTE
                FROM TICKET_HISTORY
                WHERE TICKET_ID = ?
                ORDER BY HISTORY_ID
                """,
                (self.first_ticket,),
            ).fetchall()
        self.assertEqual(history[3:], [
            ("resolved", "in_progress", 1, "Issue still occurs."),
            ("in_progress", "resolved", 2, "Tested again."),
            ("resolved", "closed", 1, "I confirmed the fix."),
        ])
