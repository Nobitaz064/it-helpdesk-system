"""Authenticate dashboard requests and resolve roles from the Helpdesk database."""

import logging
import os
import sqlite3
import time
from collections.abc import Mapping
from contextlib import closing
from math import inf
from typing import NoReturn
from urllib.parse import urlsplit

import streamlit as st
from streamlit.errors import StreamlitAPIException

from src.db import get_connection


ROLES = ("employee", "technician", "admin")
DEMO_USERS = {"employee": 1, "technician": 2, "admin": 3}
ROLE_PAGES = {
    "technician": "pages/1_Technician_Dashboard.py",
    "admin": "pages/2_Admin_Dashboard.py",
}
_AUTH_SETTINGS = ("redirect_uri", "cookie_secret", "client_id", "client_secret", "server_metadata_url")
_LOGGER = logging.getLogger(__name__)


def validate_identity(issuer, subject):
    """Check OIDC identifier structure while preserving the provider's exact values."""
    if not isinstance(issuer, str) or not issuer or any(
        character.isspace() or ord(character) < 33 or ord(character) > 126 for character in issuer
    ):
        raise ValueError("Issuer must be a valid HTTPS URL.")

    try:
        url = urlsplit(issuer)
        host = url.hostname
        # Accessing port also validates non-numeric or out-of-range ports.
        url.port
    except ValueError as error:
        raise ValueError("Issuer must be a valid HTTPS URL.") from error

    if url.scheme != "https" or not host or url.username is not None or "?" in issuer or "#" in issuer:
        raise ValueError("Issuer must be an HTTPS URL without credentials, a query, or a fragment.")

    if (
        not isinstance(subject, str)
        or not subject.strip()
        or len(subject) > 255
        or not subject.isascii()
        or not subject.isprintable()
    ):
        raise ValueError("Subject must be a non-empty OIDC subject of at most 255 ASCII characters.")

    return issuer, subject


def database_auth_mode(conn):
    row = conn.execute(
        "SELECT VALUE FROM HELPDESK_SETTINGS WHERE KEY = ?",
        ("auth_mode",),
    ).fetchone()
    return row[0] if row else None


def _deny(message: str) -> NoReturn:
    st.error(message)
    st.stop()


def _show_sign_in() -> NoReturn:
    st.title("IT Helpdesk")
    try:
        settings = st.secrets.get("auth")
    except (StreamlitAPIException, OSError):
        settings = None

    if not isinstance(settings, Mapping) or not all(
        isinstance(settings.get(key), str) and settings[key].strip() for key in _AUTH_SETTINGS
    ):
        _deny("Company sign-in is not configured. Contact your Helpdesk administrator.")

    st.info("Sign in with your organization account to continue.")
    if st.button("Sign in", key="helpdesk_login"):
        try:
            st.login()
        except (StreamlitAPIException, OSError) as error:
            _LOGGER.error("Could not start OIDC sign-in (%s).", type(error).__name__)
            st.error("Could not start sign-in. Contact your Helpdesk administrator.")
    st.stop()


def _authenticated_identity():
    try:
        user = st.user
        logged_in = user.get("is_logged_in") is True
    except (StreamlitAPIException, OSError):
        _deny("Company sign-in could not load its configuration.")

    if not logged_in:
        _show_sign_in()

    if st.sidebar.button("Sign out", key="helpdesk_logout"):
        try:
            st.logout()
        except (StreamlitAPIException, OSError) as error:
            _LOGGER.error("Could not complete OIDC sign-out (%s).", type(error).__name__)
            _deny("Could not sign out. Contact your Helpdesk administrator.")
        st.stop()

    expires_at = user.get("exp")
    if type(expires_at) not in (int, float) or not time.time() < expires_at < inf:
        _deny("Your sign-in has expired or is invalid. Sign out and sign in again.")

    try:
        return validate_identity(user.get("iss"), user.get("sub"))
    except ValueError:
        _deny("Your sign-in is missing a supported account identifier.")


def require_user(role: str, *, landing: bool = False) -> int:
    """Return a local user ID after checking the current request's authentication and role."""
    if role not in ROLES:
        raise ValueError("Unsupported dashboard role.")

    mode = os.environ.get("HELPDESK_AUTH_MODE", "oidc").strip().lower()
    if mode not in ("oidc", "demo"):
        _deny("Helpdesk authentication mode is invalid. Contact your administrator.")

    identity = _authenticated_identity() if mode == "oidc" else None
    try:
        with closing(get_connection()) as conn:
            if database_auth_mode(conn) != mode:
                _deny("Helpdesk is configured for a different database sign-in mode.")
            if mode == "demo":
                account = conn.execute(
                    "SELECT USER_ID, FULL_NAME, ROLE FROM USERS WHERE USER_ID = ? AND ROLE = ?",
                    (DEMO_USERS[role], role),
                ).fetchone()
            else:
                account = conn.execute(
                    """
                    SELECT U.USER_ID, U.FULL_NAME, U.ROLE
                    FROM USER_IDENTITIES AS I
                    JOIN USERS AS U ON U.USER_ID = I.USER_ID
                    WHERE I.ISSUER = ? AND I.SUBJECT = ?
                    """,
                    identity,
                ).fetchone()
    except (sqlite3.Error, OSError) as error:
        _LOGGER.error("Could not read Helpdesk account settings (%s).", type(error).__name__)
        _deny("Helpdesk could not check your access. Contact your administrator.")

    if account is None:
        if mode == "demo":
            _deny("This Helpdesk database is missing the requested demo account.")
        _deny("Your organization account is not enrolled in Helpdesk.")

    user_id, full_name, registered_role = account
    if registered_role != role:
        if mode == "oidc" and role == "employee" and landing and registered_role in ROLE_PAGES:
            st.switch_page(ROLE_PAGES[registered_role])
            st.stop()
        _deny("Your Helpdesk role does not have access to this dashboard.")

    identity_label = "Demo mode" if mode == "demo" else "Signed in"
    st.sidebar.text(f"{identity_label} · {full_name} ({registered_role.title()})")
    return user_id
