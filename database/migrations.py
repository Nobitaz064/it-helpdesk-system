"""Explicit schema upgrades for the Helpdesk SQLite database."""

import sqlite3


SCHEMA_VERSION = 1


def apply_migrations(connection: sqlite3.Connection) -> None:
    """Upgrade the schema within the caller's transaction."""
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema version {version} requires a newer version of Helpdesk."
        )

    if version == 0:
        connection.execute(
            "ALTER TABLE TICKETS ADD COLUMN VERSION INTEGER NOT NULL DEFAULT 1"
        )
        connection.execute(
            "ALTER TABLE TICKET_HISTORY ADD COLUMN OLD_ASSIGNEE_ID "
            "INTEGER REFERENCES USERS(USER_ID)"
        )
        connection.execute(
            "ALTER TABLE TICKET_HISTORY ADD COLUMN NEW_ASSIGNEE_ID "
            "INTEGER REFERENCES USERS(USER_ID)"
        )
        connection.execute("""
            CREATE TABLE USER_IDENTITIES (
                ISSUER TEXT NOT NULL,
                SUBJECT TEXT NOT NULL,
                USER_ID INTEGER NOT NULL REFERENCES USERS(USER_ID),
                PRIMARY KEY (ISSUER, SUBJECT)
            )
        """)
        connection.execute("""
            CREATE TABLE HELPDESK_SETTINGS (
                KEY TEXT NOT NULL PRIMARY KEY,
                VALUE TEXT NOT NULL
            )
        """)
        connection.execute(
            "CREATE INDEX idx_tickets_reporter_status "
            "ON TICKETS (REPORTER_ID, STATUS, TICKET_ID)"
        )
        connection.execute(
            "CREATE INDEX idx_tickets_assignee_status "
            "ON TICKETS (ASSIGNED_TO, STATUS, TICKET_ID)"
        )
        connection.execute(
            "CREATE INDEX idx_tickets_status ON TICKETS (STATUS, TICKET_ID)"
        )
        connection.execute(
            "CREATE INDEX idx_ticket_history_ticket "
            "ON TICKET_HISTORY (TICKET_ID, HISTORY_ID)"
        )
        connection.execute("PRAGMA user_version = 1")
