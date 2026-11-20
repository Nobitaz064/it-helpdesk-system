import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from database import init_db
from src import db


APP = Path(__file__).resolve().parents[1] / "app.py"
TECHNICIAN_PAGE = "pages/1_Technician_Dashboard.py"
ADMIN_PAGE = "pages/2_Admin_Dashboard.py"


class TestTicketWorkflow(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        database_path = Path(folder) / "helpdesk.db"
        self.enterContext(patch.object(init_db, "DB_PATH", database_path))
        self.enterContext(patch.object(db, "DB_PATH", database_path))
        init_db.init_db()

    def submit_form(self, app, label):
        button = next((button for button in app.button if button.label == label), None)
        self.assertIsNotNone(button, f"Expected to find the {label!r} button")
        button.click().run()
        self.assertFalse(app.exception, f"{label}: {app.exception}")
        self.assertFalse(app.error, f"{label}: {app.error}")

    def resolve_ticket(self, app, ticket_id, note):
        app.switch_page(TECHNICIAN_PAGE).run()
        app.selectbox(key="resolve_ticket").set_value(ticket_id)
        app.text_area(key="resolve_note").set_value(note)
        self.submit_form(app, "Mark as Resolved")

    def review_ticket(self, app, ticket_id, decision, note):
        app.switch_page("app.py").run()
        app.selectbox(key="employee_review_ticket").set_value(ticket_id)
        app.radio(key="employee_review_action").set_value(decision)
        app.text_area(key="employee_review_note").set_value(note)
        self.submit_form(app, "Submit Decision")

    def test_create_assign_resolve_reopen_and_close(self):
        app = AppTest.from_file(str(APP)).run()
        self.assertFalse(app.exception)
        title = "Wi-Fi disconnects after restart"
        app.text_input[0].set_value(title)
        app.text_area[0].set_value("The laptop loses Wi-Fi after each restart.")
        self.submit_form(app, "Submit Ticket")
        (ticket,) = app.dataframe[0].value.to_dict("records")
        self.assertEqual((ticket["Title"], ticket["Status"]), (title, "open"))
        ticket_id = ticket["ID"]

        app.switch_page(ADMIN_PAGE).run()
        app.selectbox(key="assignment_ticket").set_value(ticket_id)
        app.selectbox(key="assignment_technician").set_value(2)
        app.text_area(key="assignment_note").set_value("Check the Wi-Fi configuration.")
        self.submit_form(app, "Assign Ticket")
        assigned = app.dataframe[0].value.set_index("ID").loc[ticket_id]
        self.assertEqual((assigned["Status"], assigned["Technician"]), ("in_progress", "Binh"))

        self.resolve_ticket(app, ticket_id, "Reset Wi-Fi settings.")
        self.review_ticket(app, ticket_id, "Reopen Ticket", "The connection still drops.")
        reopened = app.dataframe[0].value.set_index("ID").loc[ticket_id]
        self.assertEqual((reopened["Status"], reopened["Technician"]), ("in_progress", "Binh"))

        self.resolve_ticket(app, ticket_id, "Updated the network driver.")
        self.review_ticket(app, ticket_id, "Close Ticket", "Confirmed Wi-Fi works.")
        closed = app.dataframe[0].value.set_index("ID").loc[ticket_id]
        self.assertEqual(closed["Status"], "closed")
        self.assertIn("No resolved tickets are waiting for your review.", [info.value for info in app.info])

        with closing(db.get_connection()) as connection:
            history = connection.execute(
                """
                SELECT OLD_STATUS, NEW_STATUS, CHANGED_BY, NOTE
                FROM TICKET_HISTORY
                WHERE TICKET_ID = ?
                ORDER BY HISTORY_ID
                """,
                (ticket_id,),
            ).fetchall()

        self.assertEqual(
            history,
            [
                (None, "open", 1, "Ticket created"),
                ("open", "in_progress", 3, "Assigned to technician #2. Check the Wi-Fi configuration."),
                ("in_progress", "resolved", 2, "Reset Wi-Fi settings."),
                ("resolved", "in_progress", 1, "The connection still drops."),
                ("in_progress", "resolved", 2, "Updated the network driver."),
                ("resolved", "closed", 1, "Confirmed Wi-Fi works."),
            ],
        )
