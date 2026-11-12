
import sqlite3
from src.db import get_connection


def create_ticket(title, description, reporter_id,
                  category_id, priority="medium"):

    # STEP 1: Validate input
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Ticket title cannot be empty")

    if not isinstance(description, str) or not description.strip():
        raise ValueError("Description cannot be empty")

    title = title.strip()
    description = description.strip()

    if len(title) > 120:
        raise ValueError("Title must not exceed 120 characters")

    if type(reporter_id) is not int or reporter_id <= 0:
        raise ValueError("Invalid reporter ID")

    if type(category_id) is not int or category_id <= 0:
        raise ValueError("Invalid category ID")

    valid_priorities = ("low", "medium", "high", "critical")

    if priority not in valid_priorities:
        raise ValueError("Invalid priority")

    # STEP 2: Connect to database
    conn = get_connection()

    try:
        # STEP 3: Begin database transaction
        with conn:

            # Check reporter
            reporter = conn.execute("""
                SELECT ROLE
                FROM USERS
                WHERE USER_ID = ?
            """, (reporter_id,)).fetchone()

            if reporter is None:
                raise ValueError("Reporter does not exist")

            if reporter[0] != "employee":
                raise ValueError("Reporter must be an employee")

            # Check category
            category = conn.execute("""
                SELECT CATEGORY_ID
                FROM CATEGORIES
                WHERE CATEGORY_ID = ?
            """, (category_id,)).fetchone()

            if category is None:
                raise ValueError("Category does not exist")

            # STEP 4: Create ticket
            cursor = conn.execute("""
                INSERT INTO TICKETS
                (TITLE, DESCRIPTION, REPORTER_ID,
                 CATEGORY_ID, PRIORITY)
                VALUES (?, ?, ?, ?, ?)
            """, (
                title,
                description,
                reporter_id,
                category_id,
                priority
            ))

            # STEP 5: Get generated ticket ID
            ticket_id = cursor.lastrowid

            # STEP 6: Record ticket history
            conn.execute("""
                INSERT INTO TICKET_HISTORY
                (TICKET_ID, CHANGED_BY,
                 OLD_STATUS, NEW_STATUS, NOTE)
                VALUES (?, ?, ?, ?, ?)
            """, (
                ticket_id,
                reporter_id,
                None,
                "open",
                "Ticket created"
            ))

        # STEP 7: Return result after commit
        return ticket_id

    finally:
        conn.close()


# =====================================
# LESSON 2.3: VIEW TICKETS
# =====================================

def get_tickets(viewer_id):

    # STEP 1: Validate viewer ID
    if type(viewer_id) is not int or viewer_id <= 0:
        raise ValueError("Invalid viewer ID")

    conn = get_connection()

    try:
        # STEP 2: Get viewer role
        user = conn.execute("""
            SELECT ROLE
            FROM USERS
            WHERE USER_ID = ?
        """, (viewer_id,)).fetchone()

        if user is None:
            raise ValueError("User does not exist")

        role = user[0]

        # STEP 3: Join ticket information
        query = """
            SELECT
                T.TICKET_ID,
                T.TITLE,
                T.STATUS,
                T.PRIORITY,
                U.FULL_NAME AS REPORTER_NAME,
                C.CATEGORY_NAME,
                TECH.FULL_NAME AS TECHNICIAN_NAME

            FROM TICKETS AS T

            JOIN USERS AS U
                ON T.REPORTER_ID = U.USER_ID

            JOIN CATEGORIES AS C
                ON T.CATEGORY_ID = C.CATEGORY_ID

            LEFT JOIN USERS AS TECH
                ON T.ASSIGNED_TO = TECH.USER_ID

            WHERE 1 = 1
        """

        params = []

        # STEP 4: Apply role-based access
        if role == "employee":
            query += " AND T.REPORTER_ID = ?"
            params.append(viewer_id)

        elif role == "technician":
            query += " AND T.ASSIGNED_TO = ?"
            params.append(viewer_id)

        elif role != "admin":
            raise ValueError("Invalid user role")

        # STEP 5: Sort tickets
        query += " ORDER BY T.TICKET_ID DESC"

        # STEP 6: Execute SQL
        cursor = conn.execute(query, params)

        # STEP 7: Fetch results
        tickets = cursor.fetchall()

        return tickets

    finally:
        conn.close()


# STEP 8: Test the function
if __name__ == "__main__":
    try:
        new_id = create_ticket(
            title="Laptop cannot turn on",
            description="Laptop does not power on.",
            reporter_id=1,
            category_id=2,
            priority="high"
        )

        print(f"Ticket #{new_id} created successfully!")

    except (ValueError, sqlite3.Error) as error:
        print("Error:", error)
