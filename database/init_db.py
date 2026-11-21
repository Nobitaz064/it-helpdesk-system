"""Initialize a new Helpdesk database or explicitly upgrade an existing one."""

import argparse
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

# Keep the original script entry point working alongside python -m.
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
    schema, marker, _ = SQL_PATH.read_text(encoding="utf-8").partition(SCHEMA_END)
    if not marker:
        raise RuntimeError("Schema section marker not found")

    # executescript() can commit a pending transaction before running its SQL.
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
        connection.execute("BEGIN IMMEDIATE")
        existing_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND substr(name, 1, 7) != 'sqlite_'"
            )
        }
        if not existing_tables:
            create_base_schema(connection)
            connection.executemany(
                "INSERT INTO CATEGORIES (CATEGORY_ID, CATEGORY_NAME, DESCRIPTION) "
                "VALUES (?, ?, ?)",
                DEFAULT_CATEGORIES,
            )
            if not production:
                connection.executemany(
                    "INSERT INTO USERS (USER_ID, FULL_NAME, EMAIL, ROLE) VALUES (?, ?, ?, ?)",
                    DEMO_USERS,
                )
        elif not BASE_TABLES.issubset(existing_tables):
            raise RuntimeError("Existing database is missing one or more Helpdesk tables.")

        apply_migrations(connection)
        connection.execute(
            "INSERT OR IGNORE INTO HELPDESK_SETTINGS (KEY, VALUE) VALUES ('auth_mode', ?)",
            ("oidc" if production else "demo",),
        )
        if production:
            connection.execute(
                "UPDATE HELPDESK_SETTINGS SET VALUE = 'oidc' WHERE KEY = 'auth_mode'"
            )
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
