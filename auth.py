import streamlit as st
import hashlib
import hmac
from dataclasses import dataclass
from db import get_user_hash, upsert_user

@dataclass
class AuthUser:
    username: str
    is_admin: bool = False

def _app_salt() -> str:
    # Required for stable hashing across restarts/deployments
    salt = st.secrets.get("APP_SALT", None)
    if not salt:
        # Works locally, but you MUST set APP_SALT in production secrets.
        salt = "dev_salt_change_me"
    return str(salt)

def hash_password(password: str) -> str:
    # salted SHA256 (simple). For larger production, use bcrypt/argon2.
    msg = (_app_salt() + "::" + password).encode("utf-8")
    return hashlib.sha256(msg).hexdigest()

def verify_password(password: str, stored_hash: str) -> bool:
    candidate = hash_password(password)
    return hmac.compare_digest(candidate, stored_hash)

def ensure_admin_user_exists():
    # admin password is stored in secrets; create/rotate from secrets
    admin_pw = st.secrets.get("ADMIN_PASSWORD", None)
    if admin_pw:
        upsert_user("admin", hash_password(str(admin_pw)))

def login_panel() -> AuthUser | None:
    st.sidebar.header("🔐 Login")

    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button("Sign in", use_container_width=True):
        if not username or not password:
            st.sidebar.error("Enter username and password.")
            return None

        stored = get_user_hash(username)
        if stored and verify_password(password, stored):
            st.session_state["auth_user"] = username
            st.sidebar.success("Signed in.")
            return AuthUser(username=username, is_admin=(username == "admin"))
        st.sidebar.error("Invalid credentials.")
        return None

    # already signed in
    if st.session_state.get("auth_user"):
        u = st.session_state["auth_user"]
        st.sidebar.success(f"Signed in as: {u}")
        if st.sidebar.button("Sign out", use_container_width=True):
            st.session_state["auth_user"] = None
            st.rerun()
        return AuthUser(username=u, is_admin=(u == "admin"))

    return None

def require_login() -> AuthUser:
    ensure_admin_user_exists()
    user = login_panel()
    if user is None:
        st.title("Review-to-Action Intelligence Engine")
        st.info("Please sign in to continue.")
        st.stop()
    return user

