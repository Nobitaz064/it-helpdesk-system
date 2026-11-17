
import sqlite3
from pathlib import Path

# STEP 1: Locate project files
BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "database" / "helpdesk.db"
SQL_PATH = BASE_DIR / "database" / "TICKET_MANAGEMENT.sql"

SCHEMA_END = "-- PART 2: INSERT SAMPLE DATA"


def init_db():

    # STEP 2: Protect existing database
    if DB_PATH.exists():
        print("Database already exists. Skipped.")
        return

    # STEP 3: Read schema from SQL file
    sql_text = SQL_PATH.read_text(encoding="utf-8")

    if SCHEMA_END not in sql_text:
        raise RuntimeError("Schema section marker not found")

    schema = sql_text.split(SCHEMA_END, 1)[0]

    # STEP 4: Create new database
    conn = sqlite3.connect(DB_PATH)

    try:
        conn.execute("PRAGMA foreign_keys = ON")

        # Create tables only
        conn.executescript(schema)

        # STEP 5: Insert sample users and categories
        with conn:
            conn.executemany("""
                INSERT INTO USERS
                (USER_ID, FULL_NAME, EMAIL, ROLE)
                VALUES (?, ?, ?, ?)
            """, [
                (1, "An", "an@company.com", "employee"),
                (2, "Binh", "binh@company.com", "technician"),
                (3, "Chi", "chi@company.com", "admin")
            ])

            conn.executemany("""
                INSERT INTO CATEGORIES
                (CATEGORY_ID, CATEGORY_NAME, DESCRIPTION)
                VALUES (?, ?, ?)
            """, [
                (1, "Network", "Network and Internet issues"),
                (2, "Hardware", "Computer hardware issues"),
                (3, "Software", "Software and application issues"),
                (4, "Account", "Login and account issues")
            ])

        # STEP 6: Verify database structure
        tables = {
            row[0] for row in conn.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
            """)
        }

        required = {
            "USERS", "CATEGORIES",
            "TICKETS", "TICKET_HISTORY"
        }

        if not required.issubset(tables):
            raise RuntimeError("Database tables are missing")

        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("Foreign key validation failed")

    except Exception:
        conn.close()
        DB_PATH.unlink(missing_ok=True)
        raise

    else:
        conn.close()
        print("Database initialized successfully!")
        print("Tables:", ", ".join(sorted(required)))


if __name__ == "__main__":
    init_db()
