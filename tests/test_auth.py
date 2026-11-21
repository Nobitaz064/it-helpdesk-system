"""Verify authorization and local identity enrollment without an OIDC provider."""

import os
import time
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from database import init_db, manage_users
from src import auth, db, ticket_service


ISSUER = "https://idp.example.test/tenant"


class DashboardStopped(Exception):
    """Represent Streamlit stopping this render before the dashboard can run."""


class TestAuthentication(unittest.TestCase):
    def setUp(self):
        directory = Path(self.enterContext(TemporaryDirectory()))
        self.directory = directory
        database = directory / "company.db"
        self.enterContext(patch.object(db, "DB_PATH", database))
        self.enterContext(patch.object(init_db, "DB_PATH", database))
        self.enterContext(patch.dict(os.environ))
        os.environ.pop("HELPDESK_AUTH_MODE", None)
        init_db.init_db(production=True)
        self.employee_id = manage_users.create_user(
            ISSUER, "employee-sub", "Employee One", "one@example.test", "employee"
        )
        self.admin_id = manage_users.create_user(
            ISSUER, "admin-sub", "Support Admin", "admin@example.test", "admin"
        )
        self.streamlit = Mock()
        self.streamlit.sidebar.button.return_value = False
        self.streamlit.button.return_value = False
        self.streamlit.stop.side_effect = DashboardStopped
        self.streamlit.secrets = {}
        self.set_claims("employee-sub")
        self.enterContext(patch.object(auth, "st", self.streamlit))

    def set_claims(self, subject, **claims):
        self.streamlit.user = {
            "is_logged_in": True,
            "iss": ISSUER,
            "sub": subject,
            "exp": int(time.time()) + 3600,
            **claims,
        }

    def test_default_company_mode_uses_enrolled_identity_and_local_role(self):
        self.set_claims(
            "employee-sub",
            email="admin@example.test",
            role="admin",
        )
        self.assertEqual(auth.require_user("employee"), self.employee_id)
        with self.assertRaises(DashboardStopped):
            auth.require_user("admin")
        self.streamlit.error.assert_called_with("Your Helpdesk role does not have access to this dashboard.")

    def test_two_enrolled_employees_see_only_their_tickets_and_are_audited(self):
        second_employee = manage_users.create_user(
            ISSUER, "employee-two-sub", "Employee Two", "two@example.test", "employee"
        )
        first_ticket = ticket_service.create_ticket(
            "First request", "First private ticket", auth.require_user("employee"), 1
        )
        self.set_claims("employee-two-sub")
        second_ticket = ticket_service.create_ticket(
            "Second request", "Second private ticket", auth.require_user("employee"), 1
        )
        self.assertEqual(
            [ticket[0] for ticket in ticket_service.get_tickets(auth.require_user("employee"))],
            [second_ticket],
        )

        self.set_claims("employee-sub")
        self.assertEqual(
            [ticket[0] for ticket in ticket_service.get_tickets(auth.require_user("employee"))],
            [first_ticket],
        )
        with closing(db.get_connection()) as conn:
            entries = conn.execute(
                "SELECT TICKET_ID, CHANGED_BY FROM TICKET_HISTORY ORDER BY HISTORY_ID"
            ).fetchall()
        self.assertEqual(entries, [(first_ticket, self.employee_id), (second_ticket, second_employee)])

    def test_landing_redirects_to_the_registered_role(self):
        self.set_claims("admin-sub")
        with self.assertRaises(DashboardStopped):
            auth.require_user("employee", landing=True)
        self.streamlit.switch_page.assert_called_once_with("pages/2_Admin_Dashboard.py")
        self.assertEqual(auth.require_user("admin"), self.admin_id)

    def test_direct_wrong_role_page_is_denied(self):
        self.set_claims("admin-sub")
        with self.assertRaises(DashboardStopped):
            auth.require_user("technician")
        self.streamlit.switch_page.assert_not_called()

    def test_missing_issuer_subject_or_expiry_stops_the_dashboard(self):
        for claim in ("iss", "sub", "exp"):
            with self.subTest(claim=claim):
                self.set_claims("employee-sub")
                del self.streamlit.user[claim]
                with self.assertRaises(DashboardStopped):
                    auth.require_user("employee")

    def test_expired_identity_is_denied(self):
        self.set_claims("employee-sub", exp=1)
        with self.assertRaises(DashboardStopped):
            auth.require_user("employee")
        self.streamlit.error.assert_called_with("Your sign-in has expired or is invalid. Sign out and sign in again.")

    def test_wrong_issuer_and_unknown_subject_are_denied(self):
        for claims in (
            {"iss": "https://another.example.test/tenant"},
            {"sub": "unknown-account"},
        ):
            with self.subTest(claims=claims):
                self.set_claims("employee-sub")
                self.streamlit.user.update(claims)
                with self.assertRaises(DashboardStopped):
                    auth.require_user("employee")
                self.streamlit.error.assert_called_with("Your organization account is not enrolled in Helpdesk.")

    def test_unauthenticated_request_stops_gracefully_without_oidc_settings(self):
        self.streamlit.user = {}
        with self.assertRaises(DashboardStopped):
            auth.require_user("employee")
        self.streamlit.error.assert_called_with(
            "Company sign-in is not configured. Contact your Helpdesk administrator."
        )
        self.streamlit.login.assert_not_called()

    def test_production_database_rejects_demo_mode(self):
        os.environ["HELPDESK_AUTH_MODE"] = "demo"
        with self.assertRaises(DashboardStopped):
            auth.require_user("admin")
        self.streamlit.error.assert_called_with("Helpdesk is configured for a different database sign-in mode.")

    def test_demo_requires_explicit_mode_and_a_demo_database(self):
        database = self.directory / "demo.db"
        self.enterContext(patch.object(db, "DB_PATH", database))
        self.enterContext(patch.object(init_db, "DB_PATH", database))
        init_db.init_db()
        with self.assertRaises(DashboardStopped):
            auth.require_user("admin")
        os.environ["HELPDESK_AUTH_MODE"] = "demo"
        self.assertEqual(auth.require_user("employee"), 1)
        self.assertEqual(auth.require_user("technician"), 2)
        self.assertEqual(auth.require_user("admin"), 3)

    def test_duplicate_enrollment_rolls_back_new_local_user(self):
        with self.assertRaisesRegex(ValueError, "already enrolled"):
            manage_users.create_user(
                ISSUER, "employee-sub", "Duplicate", "duplicate@example.test", "admin"
            )
        with closing(db.get_connection()) as conn:
            exists = conn.execute(
                "SELECT USER_ID FROM USERS WHERE EMAIL = ?",
                ("duplicate@example.test",),
            ).fetchone()
        self.assertIsNone(exists)

    def test_link_and_unlink_existing_user_preserve_the_user_record(self):
        with closing(db.get_connection()) as conn, conn:
            user_id = conn.execute(
                "INSERT INTO USERS (FULL_NAME, EMAIL, ROLE) VALUES (?, ?, ?)",
                ("Existing Employee", "existing@example.test", "employee"),
            ).lastrowid
        manage_users.link_user(user_id, ISSUER, "existing-sub")
        self.set_claims("existing-sub")
        self.assertEqual(auth.require_user("employee"), user_id)
        manage_users.unlink_user(ISSUER, "existing-sub")
        with self.assertRaises(DashboardStopped):
            auth.require_user("employee")
        with closing(db.get_connection()) as conn:
            self.assertIsNotNone(
                conn.execute("SELECT USER_ID FROM USERS WHERE USER_ID = ?", (user_id,)).fetchone()
            )


if __name__ == "__main__":
    unittest.main()
