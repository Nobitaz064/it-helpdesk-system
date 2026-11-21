# Sau Tuần 4 | Kiểm thử khởi tạo, nâng cấp và sao lưu bằng SQLite thật trong thư mục tạm.

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from database import backup_db, init_db
from database.migrations import SCHEMA_VERSION
from src import db


class TestDatabaseOperations(unittest.TestCase):
    def setUp(self):
        temporary = self.enterContext(tempfile.TemporaryDirectory())
        self.db_path = Path(temporary) / "data" / "helpdesk.db"
        self.enterContext(patch.object(init_db, "DB_PATH", self.db_path))
        self.enterContext(patch.object(db, "DB_PATH", self.db_path))

    def test_new_demo_database_creates_current_schema_and_sample_users(self):
        init_db.init_db()

        with closing(db.get_connection()) as connection:
            users = connection.execute("SELECT ROLE FROM USERS ORDER BY USER_ID").fetchall()
            self.assertEqual(users, [("employee",), ("technician",), ("admin",)])
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone(), (SCHEMA_VERSION,))
            self.assertEqual(
                connection.execute(
                    "SELECT VALUE FROM HELPDESK_SETTINGS WHERE KEY = 'auth_mode'"
                ).fetchone(),
                ("demo",),
            )

    # Chạy init hai lần để bắt lỗi vô tình bật lại demo trên DB công ty.
    def test_production_seeds_categories_without_demo_users_and_stays_production(self):
        init_db.init_db(production=True)
        init_db.init_db()

        with closing(db.get_connection()) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM USERS").fetchone(), (0,))
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM CATEGORIES").fetchone(), (4,))
            self.assertEqual(
                connection.execute(
                    "SELECT VALUE FROM HELPDESK_SETTINGS WHERE KEY = 'auth_mode'"
                ).fetchone(),
                ("oidc",),
            )

    # Tạo schema Tuần 1 với dữ liệu cũ để kiểm tra migration bảo toàn ID và lịch sử.
    def test_upgrade_preserves_legacy_ticket_and_history(self):
        self.db_path.parent.mkdir()
        schema = init_db.SQL_PATH.read_text(encoding="utf-8").split(init_db.SCHEMA_END, 1)[0]
        with closing(sqlite3.connect(self.db_path)) as connection, connection:
            connection.executescript(schema)
            connection.execute(
                "INSERT INTO USERS VALUES (25, 'Riley', 'riley@example.com', 'employee')"
            )
            connection.execute("INSERT INTO CATEGORIES VALUES (13, 'Access', 'Team access')")
            connection.execute("""
                INSERT INTO TICKETS (TICKET_ID, TITLE, DESCRIPTION, REPORTER_ID, CATEGORY_ID)
                VALUES (43, 'Locked out', 'Cannot sign in', 25, 13)
            """)
            connection.execute("""
                INSERT INTO TICKET_HISTORY (TICKET_ID, CHANGED_BY, NEW_STATUS, NOTE)
                VALUES (43, 25, 'open', 'Ticket created')
            """)

        init_db.init_db(production=True)
        init_db.init_db()

        with closing(db.get_connection()) as connection:
            self.assertEqual(
                connection.execute("SELECT TITLE, REPORTER_ID, VERSION FROM TICKETS").fetchall(),
                [("Locked out", 25, 1)],
            )
            self.assertEqual(
                connection.execute(
                    "SELECT NOTE, OLD_ASSIGNEE_ID, NEW_ASSIGNEE_ID FROM TICKET_HISTORY"
                ).fetchall(),
                [("Ticket created", None, None)],
            )
            self.assertEqual(
                connection.execute("SELECT USER_ID FROM USERS").fetchall(), [(25,)]
            )

    # Cố tình tạo khóa ngoại hỏng. Gặp lỗi phải trả schema và dữ liệu về trước nâng cấp.
    def test_failed_upgrade_leaves_original_schema_and_data(self):
        self.db_path.parent.mkdir()
        schema = init_db.SQL_PATH.read_text(encoding="utf-8").split(init_db.SCHEMA_END, 1)[0]
        with closing(sqlite3.connect(self.db_path)) as connection, connection:
            connection.executescript(schema)
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute("""
                INSERT INTO TICKETS (TICKET_ID, TITLE, DESCRIPTION, REPORTER_ID, CATEGORY_ID)
                VALUES (43, 'Broken references', 'Old data', 25, 13)
            """)

        with self.assertRaisesRegex(RuntimeError, "Foreign key validation failed"):
            init_db.init_db()

        with closing(sqlite3.connect(self.db_path)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone(), (0,))
            columns = {column[1] for column in connection.execute("PRAGMA table_info(TICKETS)")}
            self.assertNotIn("VERSION", columns)
            self.assertEqual(connection.execute("SELECT TITLE FROM TICKETS").fetchall(),
                             [("Broken references",)])

    # Sửa nguồn sau khi sao lưu, rồi mở bản sao để xác nhận trạng thái tại thời điểm backup.
    def test_backup_restores_a_snapshot_and_refuses_overwrite(self):
        init_db.init_db()
        with closing(db.get_connection()) as connection, connection:
            connection.execute("""
                INSERT INTO TICKETS (TITLE, DESCRIPTION, REPORTER_ID, CATEGORY_ID)
                VALUES ('VPN incident', 'Offline', 1, 1)
            """)

        destination = self.db_path.parent / "backups" / "snapshot.db"
        self.assertEqual(backup_db.backup_database(destination), destination)

        with closing(db.get_connection()) as connection, connection:
            connection.execute("UPDATE TICKETS SET STATUS = 'in_progress'")

        with self.assertRaises(FileExistsError):
            backup_db.backup_database(destination)

        with patch.object(db, "DB_PATH", destination):
            with closing(db.get_connection()) as restored:
                self.assertEqual(restored.execute("PRAGMA quick_check").fetchone(), ("ok",))
                self.assertEqual(
                    restored.execute("SELECT TITLE, STATUS FROM TICKETS").fetchall(),
                    [("VPN incident", "open")],
                )
