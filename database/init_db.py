# Tuần 2 | Script khởi tạo DB tự động từ schema đã thiết kế ở Tuần 1.
# Sau Tuần 4 | Nâng cấp DB đang có và tách cấu hình demo với OIDC.

"""Initialize a new Helpdesk database or explicitly upgrade an existing one."""

import argparse
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

# Khi chạy file trực tiếp, thêm thư mục repo để import database và src.
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.migrations import SCHEMA_VERSION, apply_migrations
from src.db import DB_PATH


SQL_PATH = Path(__file__).with_name("TICKET_MANAGEMENT.sql")
SCHEMA_END = "-- PART 2: INSERT SAMPLE DATA"
BASE_TABLES = {"USERS", "CATEGORIES", "TICKETS", "TICKET_HISTORY"}

DEMO_USERS = (
    (1, "An", "an@company.com", "employee"),
    (2, "Binh", "binh@company.com", "technician"),
    (3, "Chi", "chi@company.com", "admin"),
)

DEFAULT_CATEGORIES = (
    (1, "Network", "Network and Internet issues"),
    (2, "Hardware", "Computer hardware issues"),
    (3, "Software", "Software and application issues"),
    (4, "Account", "Login and account issues"),
)


def create_base_schema(connection: sqlite3.Connection) -> None:
    # Chỉ đọc DDL Tuần 1. Chạy cả file sẽ nạp ticket mẫu và thực thi các bài UPDATE.
    schema, marker, _ = SQL_PATH.read_text(encoding="utf-8").partition(SCHEMA_END)
    if not marker:
        raise RuntimeError("Schema section marker not found")

    # Thực thi từng câu SQL vì executescript() có thể commit sớm.
    # Giữ schema, seed và migration trong giao dịch của init_db().
    statement = ""
    for line in schema.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            connection.execute(statement)
            statement = ""


def init_db(*, production: bool = False) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute("PRAGMA foreign_keys = ON")
        # Sau Tuần 4 | Giành quyền ghi trước khi đọc schema để hai tiến trình không cùng nâng cấp.
        connection.execute("BEGIN IMMEDIATE")
        existing_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND substr(name, 1, 7) != 'sqlite_'"
            )
        }
        # Tuần 2 | Chỉ nạp seed cho DB mới. Lần chạy lại giữ dữ liệu đang có.
        if not existing_tables:
            create_base_schema(connection)
            connection.executemany(
                "INSERT INTO CATEGORIES (CATEGORY_ID, CATEGORY_NAME, DESCRIPTION) "
                "VALUES (?, ?, ?)",
                DEFAULT_CATEGORIES,
            )
            # Sau Tuần 4 | Tài khoản An, Bình, Chi chỉ dùng cho DB demo.
            if not production:
                connection.executemany(
                    "INSERT INTO USERS (USER_ID, FULL_NAME, EMAIL, ROLE) VALUES (?, ?, ?, ?)",
                    DEMO_USERS,
                )
        elif not BASE_TABLES.issubset(existing_tables):
            raise RuntimeError("Existing database is missing one or more Helpdesk tables.")

        # Sau Tuần 4 | Lưu schema và chế độ đăng nhập cùng nhau.
        # INSERT OR IGNORE giữ chế độ đã lưu nếu chạy lại lệnh mặc định.
        apply_migrations(connection)
        connection.execute(
            "INSERT OR IGNORE INTO HELPDESK_SETTINGS (KEY, VALUE) VALUES ('auth_mode', ?)",
            ("oidc" if production else "demo",),
        )
        if production:
            connection.execute(
                "UPDATE HELPDESK_SETTINGS SET VALUE = 'oidc' WHERE KEY = 'auth_mode'"
            )
        # Gặp liên kết cũ bị hỏng thì dừng để rollback toàn bộ lần nâng cấp.
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise RuntimeError("Foreign key validation failed")

    print(f"Helpdesk database ready (schema version {SCHEMA_VERSION}).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--production",
        action="store_true",
        help="Require OIDC for this database and omit demo users when creating it.",
    )
    init_db(production=parser.parse_args().production)


if __name__ == "__main__":
    main()
