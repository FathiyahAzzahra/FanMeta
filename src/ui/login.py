"""Login view."""
import streamlit as st
from src.firebase_auth import FirebaseAuth, FirebaseAuthError
from src.ui.components import navigate
from src.ui import auth_layout


def render(authenticator: FirebaseAuth) -> None:
    art_col, form_col = st.columns([1.15, .85], gap="small")

    with art_col:
        auth_layout.art_panel()

    with form_col:
        auth_layout.form_title("Welcome back", "Sign in to generate tags and polish your latest story draft.")

        with st.form("login_form", border=False):
            # autocomplete: supaya browser menawarkan email & password yang pernah disimpan
            # (bawaan Streamlit untuk password = "new-password", yang membuat browser menganggap ini form daftar)
            email = st.text_input("Username or Email", key="login_email", placeholder="e.g. writer.work@fanmeta.ai",
                                  autocomplete="username")
            password = st.text_input("Password", type="password", key="login_password", placeholder="Enter your secret spell",
                                     autocomplete="current-password")
            submitted = st.form_submit_button("Login to Workspace", use_container_width=True)

        if submitted:
            try:
                st.session_state["firebase_user"] = authenticator.login(email.strip(), password)
                st.session_state["page"] = st.session_state.pop("after_login", "analysis")
                st.rerun()
            except (FirebaseAuthError, ValueError) as error:
                st.error(str(error))

        c1, c2 = st.columns([1.55, 1], gap="small")
        with c1:
            st.markdown("<div class='auth-switch'>Don’t have an account?</div>", unsafe_allow_html=True)
        with c2:
            if st.button("Register here", key="go_register"):
                navigate("register")

        if st.button("← Back to Home", key="go_home"):
            st.session_state.pop("after_login", None)
            navigate("home")
