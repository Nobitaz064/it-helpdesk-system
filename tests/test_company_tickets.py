import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from database import init_db
from src import db, ticket_service as service


class TestCompanyTicketService(unittest.TestCase):
    def setUp(self):
        temp_dir = self.enterContext(tempfile.TemporaryDirectory())
        db_path = Path(temp_dir) / "helpdesk_test.db"
        self.enterContext(patch.object(init_db, "DB_PATH", db_path))
        self.enterContext(patch.object(db, "DB_PATH", db_path))
        init_db.init_db()

        with closing(db.get_connection()) as conn, conn:
            self.other_employee = conn.execute(
                "INSERT INTO USERS (FULL_NAME, EMAIL, ROLE) VALUES (?, ?, ?)",
                ("Mai", "mai@example.com", "employee"),
            ).lastrowid
            self.other_technician = conn.execute(
                "INSERT INTO USERS (FULL_NAME, EMAIL, ROLE) VALUES (?, ?, ?)",
                ("Dung", "dung@example.com", "technician"),
            ).lastrowid

    def test_ticket_detail_includes_history_and_honors_viewer_scope(self):
        ticket_id = service.create_ticket("Printer stuck", "Queue stops after restart.", 1, 2)
        self.assertIsNone(service.get_ticket_detail(2, ticket_id))
        service.assign_ticket(ticket_id, 2, 3, "Check print spooler", expected_version=1)

        detail = service.get_ticket_detail(1, ticket_id)
        self.assertEqual(detail["description"], "Queue stops after restart.")
        self.assertEqual(detail["assigned_to"], 2)
        self.assertEqual(detail["version"], 2)
        self.assertTrue(detail["created_at"])
        self.assertTrue(detail["updated_at"])
        self.assertEqual(service.get_ticket_detail(2, ticket_id), detail)
        self.assertEqual(service.get_ticket_detail(3, ticket_id), detail)
        self.assertIsNone(service.get_ticket_detail(self.other_employee, ticket_id))

        created, assigned = detail["history"]
        self.assertEqual((created["actor_name"], created["new_status"]), ("An", "open"))
        self.assertEqual(
            (assigned["actor_name"], assigned["old_status"], assigned["new_status"]),
            ("Chi", "open", "in_progress"),
        )
        self.assertIsNone(assigned["old_assignee"])
        self.assertEqual(assigned["new_assignee"], "Binh")

    def test_pages_priority_order_and_filtered_counts_share_viewer_scope(self):
        critical_first = service.create_ticket("First critical", "VPN", 1, 2, "critical")
        critical_second = service.create_ticket("Second critical", "VPN", 1, 2, "critical")
        high = service.create_ticket("High", "VPN", 1, 2, "high")
        low = service.create_ticket("Low", "VPN", 1, 2, "low")
        service.create_ticket("Other employee", "VPN", self.other_employee, 2)
        service.assign_ticket(critical_first, 2, 3)

        first_page = service.get_tickets(1, limit=2, sort="priority", include_version=True)
        second_page = service.get_tickets(1, limit=2, offset=2, sort="priority")
        self.assertEqual([row[0] for row in first_page], [critical_first, critical_second])
        self.assertEqual([row[7] for row in first_page], [2, 1])
        self.assertEqual([row[0] for row in second_page], [high, low])
        self.assertEqual(len(second_page[0]), 7)
        self.assertEqual(service.get_tickets(1)[0][0], low)
        self.assertEqual(
            service.get_ticket_counts(1, keyword="VPN", status="open"),
            {"open": 3, "in_progress": 0, "resolved": 0, "closed": 0},
        )
        self.assertEqual(service.get_ticket_counts(2)["in_progress"], 1)
        self.assertEqual(service.get_ticket_counts(2, keyword="Missing")["in_progress"], 0)
        self.assertEqual(service.get_ticket_counts(3)["open"], 4)

    def test_old_review_cannot_close_after_a_reopen_and_resolve_cycle(self):
        ticket_id = service.create_ticket("Wi-Fi drops", "Disconnects in meetings.", 1, 2)
        service.assign_ticket(ticket_id, 2, 3)
        service.update_ticket_status(ticket_id, "resolved", 2, "First attempt")
        stale = service.get_ticket_detail(1, ticket_id)

        service.update_ticket_status(ticket_id, "in_progress", 1, "It still drops")
        service.update_ticket_status(ticket_id, "resolved", 2, "Replaced adapter")
        with self.assertRaisesRegex(RuntimeError, "Ticket version conflict"):
            service.update_ticket_status(
                ticket_id, "closed", 1, "Old confirmation", expected_version=stale["version"]
            )

        current = service.get_ticket_detail(1, ticket_id)
        self.assertEqual(current["status"], "resolved")
        self.assertEqual(current["version"], stale["version"] + 2)
        self.assertEqual(len(current["history"]), 5)
        service.update_ticket_status(
            ticket_id, "closed", 1, "New confirmation", expected_version=current["version"]
        )
        self.assertEqual(service.get_ticket_detail(1, ticket_id)["status"], "closed")

    def test_handoff_changes_access_and_records_both_assignees(self):
        ticket_id = service.create_ticket("Slow laptop", "Startup takes six minutes.", 1, 2)
        service.assign_ticket(ticket_id, 2, 3, expected_version=1)
        service.reassign_ticket(
            ticket_id, self.other_technician, 3, "Switch shift", expected_version=2
        )

        handoff = service.get_ticket_detail(self.other_technician, ticket_id)
        self.assertIsNone(service.get_ticket_detail(2, ticket_id))
        self.assertEqual(handoff["status"], "in_progress")
        self.assertEqual(handoff["version"], 3)
        self.assertEqual(handoff["technician"], "Dung")
        self.assertEqual(
            {key: value for key, value in handoff["history"][-1].items() if key != "changed_at"},
            {
                "actor_name": "Chi",
                "old_status": "in_progress",
                "new_status": "in_progress",
                "note": "Switch shift",
                "old_assignee": "Binh",
                "new_assignee": "Dung",
            },
        )
        with self.assertRaisesRegex(RuntimeError, "Ticket version conflict"):
            service.reassign_ticket(ticket_id, 2, 3, "Outdated form", expected_version=2)
        with self.assertRaises(PermissionError):
            service.reassign_ticket(ticket_id, 2, 1, "Not the admin", expected_version=3)
        with self.assertRaisesRegex(ValueError, "Reassignment reason cannot be empty"):
            service.reassign_ticket(ticket_id, 2, 3, " ", expected_version=3)

    def test_handoff_rolls_back_when_history_write_fails(self):
        ticket_id = service.create_ticket("Broken keyboard", "Several keys fail.", 1, 2)
        service.assign_ticket(ticket_id, 2, 3)
        with closing(db.get_connection()) as conn:
            conn.executescript("""
                CREATE TRIGGER fail_handoff_history
                BEFORE INSERT ON TICKET_HISTORY
                WHEN NEW.OLD_ASSIGNEE_ID IS NOT NULL
                BEGIN
                    SELECT RAISE(ABORT, 'Test history failure');
                END;
            """)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "Test history failure"):
            service.reassign_ticket(
                ticket_id, self.other_technician, 3, "Switch shift", expected_version=2
            )
        current = service.get_ticket_detail(2, ticket_id)
        self.assertEqual((current["assigned_to"], current["version"]), (2, 2))
        self.assertEqual(len(current["history"]), 2)
