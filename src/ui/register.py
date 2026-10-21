"""Registration view."""
import streamlit as st
from src.firebase_auth import FirebaseAuth, FirebaseAuthError
from src.ui.components import navigate
from src.ui import auth_layout


def render(authenticator: FirebaseAuth) -> None:
    art_col, form_col = st.columns([1.15, .85], gap="small")

    with art_col:
        auth_layout.art_panel()

    with form_col:
        auth_layout.form_title("Create an account", "Join the future of fanfiction archiving with automated, high-precision tagging.")

        with st.form("register_form", border=False):
            email = st.text_input("Username or Email", key="register_email", placeholder="e.g. author_apprentice@fanmeta.ai",
                                  autocomplete="username")
            password = st.text_input("Password", type="password", key="register_password", placeholder="Choose a secure password")
            st.markdown("<div class='auth-hint'>Must be at least 8 characters with numbers and symbols.</div>", unsafe_allow_html=True)
            confirm_password = st.text_input("Confirm Password", type="password", key="register_confirm", placeholder="Retype your spell")
            submitted = st.form_submit_button("Register Account", use_container_width=True)

        if submitted:
            if password != confirm_password:
                st.error("Password dan konfirmasi password harus sama.")
            else:
                try:
                    st.session_state["firebase_user"] = authenticator.register(email.strip(), password)
                    st.session_state["page"] = st.session_state.pop("after_login", "analysis")
                    st.rerun()
                except (FirebaseAuthError, ValueError) as error:
                    st.error(str(error))

        c1, c2 = st.columns([1.55, 1], gap="small")
        with c1:
            st.markdown("<div class='auth-switch'>Already have an account?</div>", unsafe_allow_html=True)
        with c2:
            if st.button("Login here", key="go_login"):
                navigate("login")

        if st.button("← Back to Home", key="go_home"):
            st.session_state.pop("after_login", None)
            navigate("home")
