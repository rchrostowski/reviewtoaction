import streamlit as st
import hashlib
from dataclasses import dataclass

@dataclass
class AuthUser:
    username: str

# --- DEMO USERS ---
# In production, move these to st.secrets and store salted hashes.
# Passwords here are "demo123" and "demo123" (same) for convenience.
def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

USERS = {
    "coffee_shop_1": _hash_pw("demo123"),
    "gym_1": _hash_pw("demo123"),
}

def login_panel() -> AuthUser | None:
    st.sidebar.header("🔐 Login")

    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button("Sign in", use_container_width=True):
        if not username or not password:
            st.sidebar.error("Enter username and password.")
            return None

        pw_hash = _hash_pw(password)
        if USERS.get(username) == pw_hash:
            st.session_state["auth_user"] = username
            st.sidebar.success("Signed in.")
            return AuthUser(username=username)
        else:
            st.sidebar.error("Invalid credentials.")
            return None

    # If already signed in
    if "auth_user" in st.session_state and st.session_state["auth_user"]:
        st.sidebar.success(f"Signed in as: {st.session_state['auth_user']}")
        if st.sidebar.button("Sign out", use_container_width=True):
            st.session_state["auth_user"] = None
            st.rerun()
        return AuthUser(username=st.session_state["auth_user"])

    return None

def require_login() -> AuthUser:
    user = login_panel()
    if user is None:
        st.title("Review-to-Action Intelligence Engine")
        st.info("Please sign in to continue.")
        st.stop()
    return user

