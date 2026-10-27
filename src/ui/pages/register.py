"""Registration view."""
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
        auth_layout.form_title(tr("Create an account", "Buat akun"),
                               tr("Join the future of fanfiction archiving with automated, high-precision tagging.",
                                  "Bergabunglah dan beri tag fanfiksimu secara otomatis dan akurat."))

        with st.form("register_form", border=False):
            email = st.text_input("Email", key="register_email",
                                  placeholder="e.g. author_apprentice@fanmeta.ai", autocomplete="username")
            password = st.text_input("Password", type="password", key="register_password",
                                     placeholder=tr("Choose a secure password", "Pilih password yang aman"))
            st.markdown("<div class='auth-hint'>" + tr("Must be at least 6 characters.",
                                                       "Minimal 6 karakter.") + "</div>",
                        unsafe_allow_html=True)
            confirm_password = st.text_input(tr("Confirm Password", "Ulangi Password"), type="password",
                                             key="register_confirm",
                                             placeholder=tr("Retype your spell", "Ketik ulang mantramu"))
            submitted = st.form_submit_button(tr("Register Account", "Daftarkan Akun"), use_container_width=True)

        if submitted:
            if password != confirm_password:
                st.error(tr("Password and confirmation must match.", "Password dan konfirmasi password harus sama."))
            else:
                try:
                    st.session_state["firebase_user"] = authenticator.register(email.strip(), password)
                    st.session_state["page"] = st.session_state.pop("after_login", "home")
                    st.rerun()
                except (FirebaseAuthError, ValueError) as error:
                    st.error(str(error))

        c1, c2 = st.columns([1.55, 1], gap="small")
        with c1:
            st.markdown("<div class='auth-switch'>" + tr("Already have an account?", "Sudah punya akun?") + "</div>",
                        unsafe_allow_html=True)
        with c2:
            if st.button(tr("Login here", "Masuk di sini"), key="go_login"):
                navigate("login")

        if st.button(tr("← Back to Home", "← Kembali ke Beranda"), key="go_home"):
            st.session_state.pop("after_login", None)
            navigate("home")
