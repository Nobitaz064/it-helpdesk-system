import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from database import init_db
from src import db, ticket_service


DASHBOARD = Path(__file__).resolve().parents[1] / "pages" / "1_Technician_Dashboard.py"


class TestTechnicianDashboard(unittest.TestCase):
    def setUp(self):
        temp_dir = self.enterContext(tempfile.TemporaryDirectory())
        db_path = Path(temp_dir) / "helpdesk.db"
        self.enterContext(patch.object(init_db, "DB_PATH", db_path))
        self.enterContext(patch.object(db, "DB_PATH", db_path))
        init_db.init_db()

        self.first_ticket = self.create_assigned_ticket("Cannot turn on PC")
        self.second_ticket = self.create_assigned_ticket("Cannot connect to Wi-Fi")

    def create_assigned_ticket(self, title):
        ticket_id = ticket_service.create_ticket(title, "Test issue", 1, 2)
        ticket_service.assign_ticket(ticket_id, technician_id=2, admin_id=3)
        return ticket_id

    def open_dashboard(self):
        dashboard = AppTest.from_file(str(DASHBOARD)).run()
        self.assertFalse(dashboard.exception)
        return dashboard

    def resolve_first_ticket(self, dashboard):
        dashboard.selectbox(key="resolve_ticket").set_value(self.first_ticket)
        dashboard.text_area(key="resolve_note").set_value("Replaced the power adapter.")
        dashboard.button[0].click().run()
        self.assertFalse(dashboard.exception)
        self.assertEqual(
            dashboard.success[0].value,
            f"Ticket #{self.first_ticket} resolved successfully!",
        )

    def test_success_clears_ticket_and_note(self):
        dashboard = self.open_dashboard()
        self.resolve_first_ticket(dashboard)

        self.assertIsNone(dashboard.selectbox(key="resolve_ticket").value)
        self.assertEqual(dashboard.text_area(key="resolve_note").value, "")

    def test_search_input_limits_keywords_to_100_characters(self):
        dashboard = self.open_dashboard()
        search = next(widget for widget in dashboard.text_input if widget.label == "Search Tickets")
        self.assertEqual(search.proto.max_chars, 100)

    def test_stale_selection_does_not_resolve_another_ticket(self):
        stale_dashboard = self.open_dashboard()
        stale_dashboard.selectbox(key="resolve_ticket").set_value(self.first_ticket)
        stale_dashboard.text_area(key="resolve_note").set_value("Stale troubleshooting notes.")

        self.resolve_first_ticket(self.open_dashboard())
        stale_dashboard.button[0].click().run()

        self.assertFalse(stale_dashboard.exception)
        self.assertEqual(stale_dashboard.error[0].value, "Select a ticket to resolve.")
        self.assertEqual(ticket_service.get_ticket_by_id(2, self.second_ticket)[2], "in_progress")
