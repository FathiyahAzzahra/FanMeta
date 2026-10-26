"""Login view."""
import streamlit as st
from src.services.firebase_auth import FirebaseAuth, FirebaseAuthError
from src.ui.components import navigate, tr
from src.ui import auth_layout


def render(authenticator: FirebaseAuth) -> None:
    art_col, form_col = st.columns([1.15, .85], gap="small")

    with art_col:
        auth_layout.art_panel()

    with form_col:
        auth_layout.preferences_row()
        auth_layout.form_title(tr("Welcome back", "Selamat datang kembali"),
                               tr("Sign in to generate tags and polish your latest story draft.",
                                  "Masuk untuk membuat tag dan merapikan draf ceritamu."))

        with st.form("login_form", border=False):
            # autocomplete: supaya browser menawarkan email & password yang pernah disimpan
            # (bawaan Streamlit untuk password = "new-password", yang membuat browser menganggap ini form daftar)
            email = st.text_input(tr("Username or Email", "Username atau Email"), key="login_email",
                                  placeholder="e.g. writer.work@fanmeta.ai", autocomplete="username")
            password = st.text_input("Password", type="password", key="login_password",
                                     placeholder=tr("Enter your secret spell", "Masukkan mantra rahasiamu"),
                                     autocomplete="current-password")
            submitted = st.form_submit_button(tr("Login to Workspace", "Masuk ke Workspace"), use_container_width=True)

        if submitted:
            try:
                st.session_state["firebase_user"] = authenticator.login(email.strip(), password)
                st.session_state["page"] = st.session_state.pop("after_login", "home")
                st.rerun()
            except (FirebaseAuthError, ValueError) as error:
                st.error(str(error))

        c1, c2 = st.columns([1.55, 1], gap="small")
        with c1:
            st.markdown("<div class='auth-switch'>" + tr("Don’t have an account?", "Belum punya akun?") + "</div>",
                        unsafe_allow_html=True)
        with c2:
            if st.button(tr("Register here", "Daftar di sini"), key="go_register"):
                navigate("register")

        if st.button(tr("← Back to Home", "← Kembali ke Beranda"), key="go_home"):
            st.session_state.pop("after_login", None)
            navigate("home")
