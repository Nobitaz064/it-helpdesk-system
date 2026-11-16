
import sqlite3
import tempfile
import unittest

from pathlib import Path
from contextlib import closing
from unittest.mock import patch

from src.db import DB_PATH
import src.ticket_service as service


class TestTicketService(unittest.TestCase):

    def setUp(self):
        # STEP 1: Create temporary directory
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.test_db = (
            Path(self.temp_dir.name) / "helpdesk_test.db"
        )

        # STEP 2: Copy database safely
        with closing(sqlite3.connect(DB_PATH)) as source:
            with closing(sqlite3.connect(self.test_db)) as target:
                source.backup(target)

        # STEP 3: Redirect service to test database
        def test_connection():
            conn = sqlite3.connect(self.test_db)
            conn.execute("PRAGMA foreign_keys = ON")
            return conn

        patcher = patch.object(
            service,
            "get_connection",
            side_effect=test_connection
        )

        patcher.start()
        self.addCleanup(patcher.stop)

    # =====================================
    # TEST 1: INPUT VALIDATION
    # =====================================

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            service.get_tickets(3, status="waiting")

        with self.assertRaises(ValueError):
            service.get_tickets(3, priority="urgent")

        with self.assertRaises(ValueError):
            service.get_tickets(3, category_id=-1)

        with self.assertRaises(ValueError):
            service.get_tickets(3, keyword=123)

        with self.assertRaises(ValueError):
            service.create_ticket(
                "", "Invalid title", 1, 2
            )

    # =====================================
    # TEST 2: ROLE-BASED ACCESS
    # =====================================

    def test_ticket_permissions(self):

        ticket_id = service.create_ticket(
            "TEST - Permission Check",
            "Test unauthorized access",
            1, 2, "high"
        )

        # Employee An can view the ticket
        self.assertIsNotNone(
            service.get_ticket_by_id(1, ticket_id)
        )

        # Technician Binh cannot view unassigned ticket
        self.assertIsNone(
            service.get_ticket_by_id(2, ticket_id)
        )

        # Admin Chi can view all tickets
        self.assertIsNotNone(
            service.get_ticket_by_id(3, ticket_id)
        )

    # =====================================
    # TEST 3: COMPLETE TICKET LIFECYCLE
    # =====================================

    def test_ticket_lifecycle(self):

        ticket_id = service.create_ticket(
            "TEST - Full Lifecycle",
            "Testing all ticket status changes",
            1, 2, "medium"
        )

        service.assign_ticket(
            ticket_id, 2, 3, "Assign to Binh"
        )

        service.update_ticket_status(
            ticket_id, "resolved", 2, "Issue fixed"
        )

        service.update_ticket_status(
            ticket_id, "in_progress", 1,
            "Issue still exists"
        )

        service.update_ticket_status(
            ticket_id, "resolved", 2,
            "Issue fixed again"
        )

        service.update_ticket_status(
            ticket_id, "closed", 1,
            "Confirmed by employee"
        )

        conn = service.get_connection()

        try:
            status = conn.execute("""
                SELECT STATUS
                FROM TICKETS
                WHERE TICKET_ID = ?
            """, (ticket_id,)).fetchone()[0]

            count = conn.execute("""
                SELECT COUNT(*)
                FROM TICKET_HISTORY
                WHERE TICKET_ID = ?
            """, (ticket_id,)).fetchone()[0]

            self.assertEqual(status, "closed")
            self.assertEqual(count, 6)

        finally:
            conn.close()

    # =====================================
    # TEST 4: TRANSACTION ROLLBACK
    # =====================================

    def test_rollback_when_history_fails(self):

        conn = service.get_connection()

        try:
            before = conn.execute(
                "SELECT COUNT(*) FROM TICKETS"
            ).fetchone()[0]

            # Simulate history insertion failure
            conn.executescript("""
                CREATE TRIGGER fail_test_history
                BEFORE INSERT ON TICKET_HISTORY
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'Simulated history failure'
                    );
                END;
            """)

        finally:
            conn.close()

        # Creation must fail and rollback
        with self.assertRaises(sqlite3.IntegrityError):
            service.create_ticket(
                "TEST - Rollback",
                "Testing transaction failure",
                1, 2
            )

        conn = service.get_connection()

        try:
            after = conn.execute(
                "SELECT COUNT(*) FROM TICKETS"
            ).fetchone()[0]

            self.assertEqual(before, after)

        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
