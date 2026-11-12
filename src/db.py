
import sqlite3
from pathlib import Path

# 1. Locate the existing database
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "helpdesk.db"


# 2. Connect to SQLite
def get_connection():
    if not DB_PATH.is_file():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# 3. Test the connection
if __name__ == "__main__":
    conn = get_connection()

    try:
        required = {
            "USERS",
            "CATEGORIES",
            "TICKETS",
            "TICKET_HISTORY"
        }

        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table'"
            )
        }

        if not required.issubset(tables):
            raise RuntimeError(
                f"Missing tables: {required - tables}"
            )

        print("Connection: OK")
        print("Database:", DB_PATH)
        print("Tables:", ", ".join(sorted(required)))

        print(
            "Foreign keys:",
            conn.execute("PRAGMA foreign_keys").fetchone()[0]
        )

        ticket = conn.execute(
            "SELECT TICKET_ID, STATUS FROM TICKETS "
            "WHERE TICKET_ID = ?",
            (1,)
        ).fetchone()

        print("Ticket #1:", ticket)

        count = conn.execute(
            "SELECT COUNT(*) FROM TICKET_HISTORY "
            "WHERE TICKET_ID = ?",
            (1,)
        ).fetchone()[0]

        print("History count:", count)

    finally:
        conn.close()
