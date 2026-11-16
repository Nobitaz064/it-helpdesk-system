
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


# =====================================
# HELPER: ESCAPE LIKE CHARACTERS
# =====================================

def escape_like(text):
    return (
        text.replace("!", "!!")
            .replace("%", "!%")
            .replace("_", "!_")
    )



def get_tickets(
    viewer_id,
    keyword=None,
    status=None,
    priority=None,
    category_id=None
):


    # STEP 1: Validate viewer ID
    if type(viewer_id) is not int or viewer_id <= 0:
        raise ValueError("Invalid viewer ID")

    # STEP 1.5: Validate keyword
    if keyword is not None:

        if not isinstance(keyword, str):
            raise ValueError("Keyword must be a string")

        keyword = keyword.strip()

        if len(keyword) > 100:
            raise ValueError("Keyword is too long")


    # STEP 1.6: Validate filters
    valid_statuses = (
        "open", "in_progress", "resolved", "closed"
    )

    valid_priorities = (
        "low", "medium", "high", "critical"
    )

    if status is not None:
        if type(status) is not str or status not in valid_statuses:
            raise ValueError("Invalid status")

    if priority is not None:
        if type(priority) is not str or priority not in valid_priorities:
            raise ValueError("Invalid priority")

    if category_id is not None:
        if type(category_id) is not int or category_id <= 0:
            raise ValueError("Invalid category ID")

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
        
        
        # STEP 4.5: Search by keyword
        if keyword:
            query += """
                AND (
                    T.TITLE LIKE ? ESCAPE '!'
                    OR T.DESCRIPTION LIKE ? ESCAPE '!'
                )
            """

            pattern = f"%{escape_like(keyword)}%"

            params.extend([pattern, pattern])


        # STEP 4.6: Filter by status
        if status is not None:
            query += " AND T.STATUS = ?"
            params.append(status)

        # STEP 4.7: Filter by priority
        if priority is not None:
            query += " AND T.PRIORITY = ?"
            params.append(priority)

        # STEP 4.8: Filter by category
        if category_id is not None:
            query += " AND T.CATEGORY_ID = ?"
            params.append(category_id)


        # STEP 5: Sort tickets
        query += " ORDER BY T.TICKET_ID DESC"

        # STEP 6: Execute SQL
        cursor = conn.execute(query, params)

        # STEP 7: Fetch results
        tickets = cursor.fetchall()

        return tickets

    finally:
        conn.close()


# =====================================
# LESSON 2.3.2: SEARCH TICKET BY ID
# =====================================

def get_ticket_by_id(viewer_id, ticket_id):

    # STEP 1: Validate input
    if type(viewer_id) is not int or viewer_id <= 0:
        raise ValueError("Invalid viewer ID")

    if type(ticket_id) is not int or ticket_id <= 0:
        raise ValueError("Invalid ticket ID")

    conn = get_connection()

    try:
        # STEP 2: Check viewer role
        user = conn.execute("""
            SELECT ROLE
            FROM USERS
            WHERE USER_ID = ?
        """, (viewer_id,)).fetchone()

        if user is None:
            raise ValueError("User does not exist")

        role = user[0]

        # STEP 3: Search ticket using JOIN
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
            WHERE T.TICKET_ID = ?
        """

        params = [ticket_id]

        # STEP 4: Check viewing permission
        if role == "employee":
            query += " AND T.REPORTER_ID = ?"
            params.append(viewer_id)

        elif role == "technician":
            query += " AND T.ASSIGNED_TO = ?"
            params.append(viewer_id)

        elif role != "admin":
            raise ValueError("Invalid user role")

        # STEP 5: Return one ticket
        return conn.execute(query, params).fetchone()

    finally:
        conn.close()


# =====================================
# LESSON 2.4: ASSIGN TECHNICIAN
# =====================================

def assign_ticket(ticket_id, technician_id, admin_id,
                  note="Assigned to technician"):

    # STEP 1: Validate input
    for value in (ticket_id, technician_id, admin_id):
        if type(value) is not int or value <= 0:
            raise ValueError("Invalid user or ticket ID")

    if not isinstance(note, str) or not note.strip():
        raise ValueError("Assignment note cannot be empty")

    note = note.strip()

    if len(note) > 500:
        raise ValueError("Assignment note is too long")

    # STEP 2: Connect to database
    conn = get_connection()

    try:
        # STEP 3: Start transaction
        with conn:

            # Check admin permission
            admin = conn.execute("""
                SELECT ROLE
                FROM USERS
                WHERE USER_ID = ?
            """, (admin_id,)).fetchone()

            if admin is None or admin[0] != "admin":
                raise PermissionError(
                    "Only admins can assign tickets"
                )

            # STEP 4: Check technician
            technician = conn.execute("""
                SELECT ROLE
                FROM USERS
                WHERE USER_ID = ?
            """, (technician_id,)).fetchone()

            if technician is None:
                raise ValueError("Technician does not exist")

            if technician[0] != "technician":
                raise ValueError(
                    "Assigned user must be a technician"
                )

            # STEP 5: Check ticket
            ticket = conn.execute("""
                SELECT STATUS, ASSIGNED_TO
                FROM TICKETS
                WHERE TICKET_ID = ?
            """, (ticket_id,)).fetchone()

            if ticket is None:
                raise ValueError("Ticket does not exist")

            old_status, assigned_to = ticket

            if old_status != "open":
                raise ValueError(
                    "Only open tickets can be assigned"
                )

            if assigned_to is not None:
                raise ValueError(
                    "Ticket already has a technician"
                )

            # STEP 6: Update ticket
            cursor = conn.execute("""
                UPDATE TICKETS
                SET
                    ASSIGNED_TO = ?,
                    STATUS = 'in_progress',
                    UPDATED_AT = CURRENT_TIMESTAMP
                WHERE TICKET_ID = ?
                  AND STATUS = 'open'
                  AND ASSIGNED_TO IS NULL
            """, (technician_id, ticket_id))

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Ticket assignment conflict"
                )

            # STEP 7: Record history
            conn.execute("""
                INSERT INTO TICKET_HISTORY
                (
                    TICKET_ID,
                    CHANGED_BY,
                    OLD_STATUS,
                    NEW_STATUS,
                    NOTE
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                ticket_id,
                admin_id,
                old_status,
                "in_progress",
                f"Assigned to technician #{technician_id}. {note}"
            ))

        # STEP 8: Return after successful commit
        return ticket_id

    finally:
        conn.close()


# =====================================
# LESSON 2.5: UPDATE TICKET STATUS
# =====================================

def update_ticket_status(ticket_id, new_status,
                         actor_id, note):

    # STEP 1: Validate input
    if type(ticket_id) is not int or ticket_id <= 0:
        raise ValueError("Invalid ticket ID")

    if type(actor_id) is not int or actor_id <= 0:
        raise ValueError("Invalid actor ID")

    valid_statuses = (
        "in_progress", "resolved", "closed"
    )

    if type(new_status) is not str or new_status not in valid_statuses:
        raise ValueError("Invalid new status")

    if not isinstance(note, str) or not note.strip():
        raise ValueError("Status update note cannot be empty")

    note = note.strip()

    if len(note) > 500:
        raise ValueError("Note is too long")

    # STEP 2: Connect to database
    conn = get_connection()

    try:
        # STEP 3: Begin transaction
        with conn:

            # Check actor
            actor = conn.execute("""
                SELECT ROLE
                FROM USERS
                WHERE USER_ID = ?
            """, (actor_id,)).fetchone()

            if actor is None:
                raise ValueError("User does not exist")

            role = actor[0]

            # STEP 4: Get current ticket information
            ticket = conn.execute("""
                SELECT STATUS, REPORTER_ID, ASSIGNED_TO
                FROM TICKETS
                WHERE TICKET_ID = ?
            """, (ticket_id,)).fetchone()

            if ticket is None:
                raise ValueError("Ticket does not exist")

            old_status, reporter_id, technician_id = ticket

            # STEP 5: Check valid status transitions
            allowed_transitions = (
                ("in_progress", "resolved"),
                ("resolved", "closed"),
                ("resolved", "in_progress")
            )

            if (old_status, new_status) not in allowed_transitions:
                raise ValueError(
                    "Invalid ticket status transition"
                )

            # STEP 6: Check permissions
            if new_status == "resolved":

                if role != "technician" or technician_id != actor_id:
                    raise PermissionError(
                        "Only the assigned technician can resolve this ticket"
                    )

            elif new_status in ("closed", "in_progress"):

                if role != "employee" or reporter_id != actor_id:
                    raise PermissionError(
                        "Only the ticket reporter can close or reopen it"
                    )

            # STEP 7: Update current status
            cursor = conn.execute("""
                UPDATE TICKETS
                SET
                    STATUS = ?,
                    UPDATED_AT = CURRENT_TIMESTAMP
                WHERE TICKET_ID = ?
                  AND STATUS = ?
            """, (
                new_status,
                ticket_id,
                old_status
            ))

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Ticket status update conflict"
                )

            # STEP 8: Record ticket history
            conn.execute("""
                INSERT INTO TICKET_HISTORY
                (
                    TICKET_ID,
                    CHANGED_BY,
                    OLD_STATUS,
                    NEW_STATUS,
                    NOTE
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                ticket_id,
                actor_id,
                old_status,
                new_status,
                note
            ))

        # STEP 9: Return after commit
        return ticket_id

    finally:
        conn.close()


# STEP 8: Test the function
if __name__ == "__main__":
    print("Use separate commands to test ticket services.")
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
