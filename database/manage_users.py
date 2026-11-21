# Sau Tuần 4 | CLI tạo, liên kết và thu hồi tài khoản công ty trong SQLite.

"""Provision and revoke company identities in an initialized Helpdesk database."""

import argparse
import sqlite3
from contextlib import closing

from src.auth import ROLES, database_auth_mode, validate_identity
from src.db import get_connection


# Kiểm tra chế độ DB trước khi thay đổi danh tính để tránh thao tác nhầm vào DB demo.
def _require_company_database(conn):
    if database_auth_mode(conn) != "oidc":
        raise ValueError("Initialize this database in production mode before enrolling users.")


def create_user(issuer, subject, full_name, email, role):
    issuer, subject = validate_identity(issuer, subject)
    full_name, email = full_name.strip(), email.strip()
    email_parts = email.split("@")
    if not full_name or len(email_parts) != 2 or not all(email_parts) or any(c.isspace() for c in email):
        raise ValueError("Provide a name and a valid email address.")
    if role not in ROLES:
        raise ValueError("Role must be employee, technician, or admin.")

    # Tạo user và liên kết OIDC trong cùng giao dịch. Trùng email hoặc danh tính sẽ rollback.
    try:
        with closing(get_connection()) as conn, conn:
            _require_company_database(conn)
            result = conn.execute(
                "INSERT INTO USERS (FULL_NAME, EMAIL, ROLE) VALUES (?, ?, ?)",
                (full_name, email, role),
            )
            user_id = result.lastrowid
            conn.execute(
                "INSERT INTO USER_IDENTITIES (ISSUER, SUBJECT, USER_ID) VALUES (?, ?, ?)",
                (issuer, subject, user_id),
            )
    except sqlite3.IntegrityError as error:
        raise ValueError("That email address or company identity is already enrolled.") from error
    return user_id


# Dùng ID hiện có để người dùng giữ nguyên ticket và lịch sử khi chuyển sang đăng nhập công ty.
def link_user(user_id, issuer, subject):
    issuer, subject = validate_identity(issuer, subject)
    if type(user_id) is not int or user_id < 1:
        raise ValueError("Provide a positive user ID.")

    try:
        with closing(get_connection()) as conn, conn:
            _require_company_database(conn)
            if conn.execute("SELECT 1 FROM USERS WHERE USER_ID = ?", (user_id,)).fetchone() is None:
                raise ValueError("The specified Helpdesk user does not exist.")
            conn.execute(
                "INSERT INTO USER_IDENTITIES (ISSUER, SUBJECT, USER_ID) VALUES (?, ?, ?)",
                (issuer, subject, user_id),
            )
    except sqlite3.IntegrityError as error:
        raise ValueError("That company identity is already enrolled.") from error


# Chỉ xóa liên kết đăng nhập. USERS vẫn còn để giữ các khóa ngoại và lịch sử.
def unlink_user(issuer, subject):
    issuer, subject = validate_identity(issuer, subject)
    with closing(get_connection()) as conn, conn:
        _require_company_database(conn)
        result = conn.execute(
            "DELETE FROM USER_IDENTITIES WHERE ISSUER = ? AND SUBJECT = ?",
            (issuer, subject),
        )
        if result.rowcount != 1:
            raise ValueError("That company identity is not enrolled.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="Create and enroll a new Helpdesk user.")
    create.add_argument("--name", required=True)
    create.add_argument("--email", required=True)
    create.add_argument("--role", choices=ROLES, required=True)
    link = commands.add_parser("link", help="Enroll a company identity for an existing user.")
    link.add_argument("--user-id", type=int, required=True)
    unlink = commands.add_parser("unlink", help="Revoke an identity and retain the user's history.")
    for command in (create, link, unlink):
        command.add_argument("--issuer", required=True)
        command.add_argument("--subject", required=True)
    args = parser.parse_args()

    try:
        if args.command == "create":
            user_id = create_user(args.issuer, args.subject, args.name, args.email, args.role)
            print(f"Enrolled Helpdesk user {user_id}.")
        elif args.command == "link":
            link_user(args.user_id, args.issuer, args.subject)
            print(f"Identity linked to Helpdesk user {args.user_id}.")
        else:
            unlink_user(args.issuer, args.subject)
            print("Identity revoked.")
    except (ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")
    except sqlite3.Error:
        parser.exit(1, "Could not update Helpdesk users. Check the database and run its migration.\n")


if __name__ == "__main__":
    main()
