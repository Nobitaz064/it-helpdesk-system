
from src.db import get_connection


TICKET_STATUSES = ("open", "in_progress", "resolved", "closed")


def _validate_version(expected_version):
    if expected_version is not None and (
        type(expected_version) is not int or expected_version <= 0
    ):
        raise ValueError("Invalid ticket version")


def _check_version(expected_version, current_version):
    # Company pilot: a ticket can return to the same status at a newer version.
    if expected_version is not None and expected_version != current_version:
        raise RuntimeError("Ticket version conflict. Refresh and try again.")


def _ticket_scope(conn, viewer_id):
    # Week 2: share one visibility rule across list, count, and detail queries.
    viewer = conn.execute(
        "SELECT ROLE FROM USERS WHERE USER_ID = ?", (viewer_id,)
    ).fetchone()
    if viewer is None:
        raise ValueError("User does not exist")

    if viewer[0] == "employee":
        return " AND T.REPORTER_ID = ?", [viewer_id]
    if viewer[0] == "technician":
        return " AND T.ASSIGNED_TO = ?", [viewer_id]
    if viewer[0] == "admin":
        return "", []
    raise ValueError("Invalid user role")


# Week 2: validate the request before creating the ticket and its first audit row.
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
        # The new ticket and its history entry commit or roll back together.
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



def _search_filters(keyword, status):
    conditions = ""
    params = []
    if keyword is not None:
        if not isinstance(keyword, str):
            raise ValueError("Keyword must be a string")
        keyword = keyword.strip()
        if len(keyword) > 100:
            raise ValueError("Keyword is too long")
    if keyword:
        conditions += """
            AND (
                T.TITLE LIKE ? ESCAPE '!'
                OR T.DESCRIPTION LIKE ? ESCAPE '!'
            )
        """
        pattern = f"%{escape_like(keyword)}%"
        params.extend((pattern, pattern))
    if status is not None:
        if type(status) is not str or status not in TICKET_STATUSES:
            raise ValueError("Invalid status")
        conditions += " AND T.STATUS = ?"
        params.append(status)
    return conditions, params


def get_tickets(
    viewer_id,
    keyword=None,
    status=None,
    priority=None,
    category_id=None,
    *,
    limit=None,
    offset=0,
    sort="newest",
    include_version=False,
):
    if type(viewer_id) is not int or viewer_id <= 0:
        raise ValueError("Invalid viewer ID")
    filters, filter_params = _search_filters(keyword, status)
    valid_priorities = ("low", "medium", "high", "critical")
    if priority is not None and (
        type(priority) is not str or priority not in valid_priorities
    ):
        raise ValueError("Invalid priority")
    if category_id is not None and (type(category_id) is not int or category_id <= 0):
        raise ValueError("Invalid category ID")
    if limit is not None and (type(limit) is not int or limit <= 0):
        raise ValueError("Invalid ticket page limit")
    if type(offset) is not int or offset < 0:
        raise ValueError("Invalid ticket page offset")
    if sort not in ("newest", "priority"):
        raise ValueError("Invalid ticket sort order")

    conn = get_connection()
    try:
        scope, params = _ticket_scope(conn, viewer_id)
        version_column = ", T.VERSION" if include_version else ""
        query = f"""
            SELECT
                T.TICKET_ID, T.TITLE, T.STATUS, T.PRIORITY,
                U.FULL_NAME AS REPORTER_NAME, C.CATEGORY_NAME,
                TECH.FULL_NAME AS TECHNICIAN_NAME{version_column}
            FROM TICKETS AS T
            JOIN USERS AS U ON T.REPORTER_ID = U.USER_ID
            JOIN CATEGORIES AS C ON T.CATEGORY_ID = C.CATEGORY_ID
            LEFT JOIN USERS AS TECH ON T.ASSIGNED_TO = TECH.USER_ID
            WHERE 1 = 1
        """
        query += scope + filters
        params.extend(filter_params)
        if priority is not None:
            query += " AND T.PRIORITY = ?"
            params.append(priority)
        if category_id is not None:
            query += " AND T.CATEGORY_ID = ?"
            params.append(category_id)
        if sort == "priority":
            query += """
                ORDER BY CASE T.PRIORITY
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    ELSE 4
                END, T.CREATED_AT ASC, T.TICKET_ID ASC
            """
        else:
            query += " ORDER BY T.TICKET_ID DESC"
        if limit is not None or offset:
            query += " LIMIT ? OFFSET ?"
            params.extend((-1 if limit is None else limit, offset))
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def get_ticket_counts(viewer_id, *, keyword=None, status=None):
    # Company pilot: count all matching rows in SQL independently of page size.
    if type(viewer_id) is not int or viewer_id <= 0:
        raise ValueError("Invalid viewer ID")
    filters, filter_params = _search_filters(keyword, status)

    conn = get_connection()
    try:
        scope, params = _ticket_scope(conn, viewer_id)
        counts = dict(conn.execute(
            "SELECT T.STATUS, COUNT(*) FROM TICKETS AS T WHERE 1 = 1"
            + scope + filters + " GROUP BY T.STATUS",
            [*params, *filter_params],
        ))
        return {status: counts.get(status, 0) for status in TICKET_STATUSES}
    finally:
        conn.close()


# =====================================
# LESSON 2.3.2: SEARCH TICKET BY ID
# =====================================

def get_ticket_by_id(viewer_id, ticket_id):
    if type(viewer_id) is not int or viewer_id <= 0:
        raise ValueError("Invalid viewer ID")
    if type(ticket_id) is not int or ticket_id <= 0:
        raise ValueError("Invalid ticket ID")

    conn = get_connection()
    try:
        scope, params = _ticket_scope(conn, viewer_id)
        return conn.execute("""
            SELECT
                T.TICKET_ID, T.TITLE, T.STATUS, T.PRIORITY,
                U.FULL_NAME AS REPORTER_NAME, C.CATEGORY_NAME,
                TECH.FULL_NAME AS TECHNICIAN_NAME
            FROM TICKETS AS T
            JOIN USERS AS U ON T.REPORTER_ID = U.USER_ID
            JOIN CATEGORIES AS C ON T.CATEGORY_ID = C.CATEGORY_ID
            LEFT JOIN USERS AS TECH ON T.ASSIGNED_TO = TECH.USER_ID
            WHERE T.TICKET_ID = ?
        """ + scope, [ticket_id, *params]).fetchone()
    finally:
        conn.close()


# Company pilot: load the original report and ordered history after checking visibility.
def get_ticket_detail(viewer_id, ticket_id):
    if type(viewer_id) is not int or viewer_id <= 0:
        raise ValueError("Invalid viewer ID")
    if type(ticket_id) is not int or ticket_id <= 0:
        raise ValueError("Invalid ticket ID")

    conn = get_connection()
    try:
        # Read permissions, ticket details and history from the same snapshot.
        conn.execute("BEGIN")
        scope, params = _ticket_scope(conn, viewer_id)
        detail = conn.execute("""
            SELECT
                T.TICKET_ID, T.TITLE, T.DESCRIPTION, T.STATUS, T.PRIORITY,
                U.FULL_NAME, C.CATEGORY_NAME, TECH.FULL_NAME, T.ASSIGNED_TO,
                T.VERSION, T.CREATED_AT, T.UPDATED_AT
            FROM TICKETS AS T
            JOIN USERS AS U ON T.REPORTER_ID = U.USER_ID
            JOIN CATEGORIES AS C ON T.CATEGORY_ID = C.CATEGORY_ID
            LEFT JOIN USERS AS TECH ON T.ASSIGNED_TO = TECH.USER_ID
            WHERE T.TICKET_ID = ?
        """ + scope, [ticket_id, *params]).fetchone()
        if detail is None:
            return None

        history = conn.execute("""
            SELECT H.CHANGED_AT, ACTOR.FULL_NAME, H.OLD_STATUS, H.NEW_STATUS,
                   H.NOTE, PREVIOUS.FULL_NAME, CURRENT_OWNER.FULL_NAME
            FROM TICKET_HISTORY AS H
            JOIN USERS AS ACTOR ON H.CHANGED_BY = ACTOR.USER_ID
            LEFT JOIN USERS AS PREVIOUS ON H.OLD_ASSIGNEE_ID = PREVIOUS.USER_ID
            LEFT JOIN USERS AS CURRENT_OWNER ON H.NEW_ASSIGNEE_ID = CURRENT_OWNER.USER_ID
            WHERE H.TICKET_ID = ?
            ORDER BY H.CHANGED_AT, H.HISTORY_ID
        """, (ticket_id,)).fetchall()

        detail_keys = (
            "ticket_id", "title", "description", "status", "priority", "reporter",
            "category", "technician", "assigned_to", "version", "created_at", "updated_at",
        )
        history_keys = (
            "changed_at", "actor_name", "old_status", "new_status", "note",
            "old_assignee", "new_assignee",
        )
        result = dict(zip(detail_keys, detail, strict=True))
        result["history"] = [dict(zip(history_keys, event, strict=True)) for event in history]
        return result
    finally:
        conn.close()


# =====================================
# LESSON 2.4: ASSIGN TECHNICIAN
# =====================================

def _check_assignment_roles(conn, technician_id, admin_id):
    admin = conn.execute(
        "SELECT ROLE FROM USERS WHERE USER_ID = ?", (admin_id,)
    ).fetchone()
    if admin is None or admin[0] != "admin":
        raise PermissionError("Only admins can assign tickets")

    technician = conn.execute(
        "SELECT ROLE FROM USERS WHERE USER_ID = ?", (technician_id,)
    ).fetchone()
    if technician is None:
        raise ValueError("Technician does not exist")
    if technician[0] != "technician":
        raise ValueError("Assigned user must be a technician")


def _record_assignment(
    conn, ticket_id, admin_id, old_status, new_status, note, old_assignee, new_assignee
):
    conn.execute("""
        INSERT INTO TICKET_HISTORY (
            TICKET_ID, CHANGED_BY, OLD_STATUS, NEW_STATUS, NOTE,
            OLD_ASSIGNEE_ID, NEW_ASSIGNEE_ID
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ticket_id, admin_id, old_status, new_status, note, old_assignee, new_assignee))


def assign_ticket(ticket_id, technician_id, admin_id,
                  note="Assigned to technician", *, expected_version=None):
    for value in (ticket_id, technician_id, admin_id):
        if type(value) is not int or value <= 0:
            raise ValueError("Invalid user or ticket ID")

    if not isinstance(note, str) or not note.strip():
        raise ValueError("Assignment note cannot be empty")
    note = note.strip()
    if len(note) > 500:
        raise ValueError("Assignment note is too long")
    _validate_version(expected_version)

    conn = get_connection()
    try:
        with conn:
            _check_assignment_roles(conn, technician_id, admin_id)
            ticket = conn.execute("""
                SELECT STATUS, ASSIGNED_TO, VERSION
                FROM TICKETS
                WHERE TICKET_ID = ?
            """, (ticket_id,)).fetchone()
            if ticket is None:
                raise ValueError("Ticket does not exist")

            old_status, assigned_to, version = ticket
            _check_version(expected_version, version)
            if old_status != "open":
                raise ValueError("Only open tickets can be assigned")
            if assigned_to is not None:
                raise ValueError("Ticket already has a technician")

            cursor = conn.execute("""
                UPDATE TICKETS
                SET ASSIGNED_TO = ?, STATUS = 'in_progress',
                    UPDATED_AT = CURRENT_TIMESTAMP, VERSION = VERSION + 1
                WHERE TICKET_ID = ? AND STATUS = 'open'
                    AND ASSIGNED_TO IS NULL AND VERSION = ?
            """, (technician_id, ticket_id, version))
            if cursor.rowcount != 1:
                raise RuntimeError("Ticket assignment conflict")

            _record_assignment(
                conn, ticket_id, admin_id, old_status, "in_progress",
                f"Assigned to technician #{technician_id}. {note}", None, technician_id,
            )
        return ticket_id
    finally:
        conn.close()


# Company pilot: record both technicians while the ticket remains in progress.
def reassign_ticket(ticket_id, technician_id, admin_id, note, *, expected_version):
    for value in (ticket_id, technician_id, admin_id):
        if type(value) is not int or value <= 0:
            raise ValueError("Invalid user or ticket ID")
    if not isinstance(note, str) or not note.strip():
        raise ValueError("Reassignment reason cannot be empty")
    note = note.strip()
    if len(note) > 500:
        raise ValueError("Reassignment reason is too long")
    if expected_version is None:
        raise ValueError("Invalid ticket version")
    _validate_version(expected_version)

    conn = get_connection()
    try:
        with conn:
            _check_assignment_roles(conn, technician_id, admin_id)
            ticket = conn.execute("""
                SELECT STATUS, ASSIGNED_TO, VERSION
                FROM TICKETS
                WHERE TICKET_ID = ?
            """, (ticket_id,)).fetchone()
            if ticket is None:
                raise ValueError("Ticket does not exist")

            status, old_assignee, version = ticket
            _check_version(expected_version, version)
            if status != "in_progress":
                raise ValueError("Only in-progress tickets can be reassigned")
            if old_assignee is None:
                raise ValueError("Ticket has no assigned technician")
            if old_assignee == technician_id:
                raise ValueError("Ticket is already assigned to this technician")

            cursor = conn.execute("""
                UPDATE TICKETS
                SET ASSIGNED_TO = ?, UPDATED_AT = CURRENT_TIMESTAMP, VERSION = VERSION + 1
                WHERE TICKET_ID = ? AND STATUS = 'in_progress'
                    AND ASSIGNED_TO = ? AND VERSION = ?
            """, (technician_id, ticket_id, old_assignee, version))
            if cursor.rowcount != 1:
                raise RuntimeError("Ticket reassignment conflict")

            _record_assignment(
                conn, ticket_id, admin_id, status, status, note, old_assignee, technician_id
            )
        return ticket_id
    finally:
        conn.close()


# =====================================
# LESSON 2.5: UPDATE TICKET STATUS
# =====================================

def update_ticket_status(ticket_id, new_status,
                         actor_id, note, *, expected_version=None):

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

    _validate_version(expected_version)

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
                SELECT STATUS, REPORTER_ID, ASSIGNED_TO, VERSION
                FROM TICKETS
                WHERE TICKET_ID = ?
            """, (ticket_id,)).fetchone()

            if ticket is None:
                raise ValueError("Ticket does not exist")

            old_status, reporter_id, technician_id, version = ticket

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

            _check_version(expected_version, version)

            # Company pilot: SQL checks the version again at the moment it writes.
            cursor = conn.execute("""
                UPDATE TICKETS
                SET
                    STATUS = ?,
                    UPDATED_AT = CURRENT_TIMESTAMP,
                    VERSION = VERSION + 1
                WHERE TICKET_ID = ?
                  AND STATUS = ?
                  AND VERSION = ?
            """, (
                new_status,
                ticket_id,
                old_status,
                version,
            ))

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Ticket status update conflict"
                )

            # Week 2: keep the audit write in this transaction with the status update.
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
