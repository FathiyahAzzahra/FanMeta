"""FanMeta entry point. Run with: streamlit run app.py."""

from datetime import datetime, timezone
from typing import Any

import streamlit as st

from src.firebase_auth import FirebaseAuth, FirebaseAuthError
from src.firestore_history import FirestoreHistory, FirestoreHistoryError
from src.predictor import FanMetaPredictor
from src.gallery_store import GalleryStore
from src.workspace_store import WorkspaceStore
from src.ui import analysis, gallery, glossary, history, home, login, processing, register, results, workspace
from src.ui.components import GALLERY_ENABLED, render_footer, render_topbar, tr

GUEST_PAGES = {"home", "gallery", "work", "glossary", "login", "register"}
from src.ui.styles import apply_theme


from pathlib import Path
from PIL import Image

_icon = Image.open(Path(__file__).parent / "src" / "asset" / "logo_nobg.png")
st.set_page_config(page_title="FanMeta", page_icon=_icon, layout="wide")  # sesuaikan dengan yang sudah ada

@st.cache_resource(show_spinner=False)
def get_predictor() -> FanMetaPredictor:
    """Keep the FanMeta models loaded for the lifetime of the app session."""
    return FanMetaPredictor()

@st.cache_resource
def get_authenticator(api_key: str) -> FirebaseAuth:
    """Create a reusable Firebase client from a Streamlit secret."""
    return FirebaseAuth(api_key)


@st.cache_resource
def get_history_store(service_account: dict[str, str]) -> FirestoreHistory:
    """Cache the Firestore client instead of reconnecting on every rerun."""
    return FirestoreHistory.from_service_account(service_account)


def render_items(items: list[str]) -> None:
    """Render model labels, including an explicit empty-result state."""
    if items:
        st.write(", ".join(items))
    else:
        st.write("Tidak ada label di atas ambang prediksi.")


def get_firebase_api_key() -> str | None:
    """Read Firebase configuration without exposing it in the interface or source."""
    try:
        return str(st.secrets["firebase"]["api_key"])
    except (KeyError, FileNotFoundError):
        return None


def get_firestore_service_account() -> dict[str, str] | None:
    """Read the Firestore service account only from Streamlit secrets."""
    try:
        return dict(st.secrets["firebase_service_account"])
    except (KeyError, FileNotFoundError):
        return None


def set_logged_in_user(user: dict[str, str]) -> None:
    st.session_state["firebase_user"] = user


def logout() -> None:
    st.session_state.pop("firebase_user", None)


def render_auth_page(authenticator: FirebaseAuth) -> None:
    st.subheader("Masuk ke FanMeta")
    register_tab, login_tab = st.tabs(("Register", "Login"))

    with register_tab:
        with st.form("register_form"):
            email = st.text_input("Email", key="register_email")
            password = st.text_input("Password", type="password", key="register_password")
            submitted = st.form_submit_button("Register")
        if submitted:
            try:
                set_logged_in_user(authenticator.register(email.strip(), password))
                st.rerun()
            except (FirebaseAuthError, ValueError) as error:
                st.error(str(error))

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login")
        if submitted:
            try:
                set_logged_in_user(authenticator.login(email.strip(), password))
                st.rerun()
            except (FirebaseAuthError, ValueError) as error:
                st.error(str(error))


def render_analysis_page(user: dict[str, str], history_store: FirestoreHistory | None) -> None:
    st.title("FanMeta")
    st.caption("Analisis Content Rating, Archive Warning, dan Additional Tags cerita fanfiction.")

    language_label = st.selectbox("Bahasa", ("Bahasa Inggris", "Bahasa Indonesia"))
    title = st.text_input("Judul")
    story = st.text_area("Cerita", height=240, placeholder="Masukkan isi cerita di sini...")

    if st.button("Analisis", type="primary"):
        if not story.strip():
            st.warning("Cerita wajib diisi sebelum dianalisis.")
            return

        source_language = "id" if language_label == "Bahasa Indonesia" else "en"
        # Judul hanya disimpan; yang dianalisis isi cerita saja (sama seperti data latih).
        text_for_prediction = story.strip()

        try:
            with st.spinner("Menganalisis cerita..."):
                result = get_predictor().predict(
                    text_for_prediction,
                    source_language=source_language,
                )
        except Exception as error:
            st.error(f"Analisis gagal: {error}")
            return

        if history_store is None:
            st.warning("Hasil tidak dapat disimpan karena Firestore belum dikonfigurasi.")
        else:
            try:
                history_store.save_analysis(
                    firebase_uid=user["uid"],
                    email=user["email"],
                    title=title.strip(),
                    language=language_label,
                    story=story.strip(),
                    rating=result["rating"],
                    warnings=result["warnings"],
                    tags=result["tags"],
                )
            except FirestoreHistoryError:
                st.warning("Hasil analisis tersedia, tetapi riwayat tidak dapat disimpan.")

        st.subheader("Hasil Analisis")
        st.markdown(f"**Content Rating:** {result['rating']}")
        st.markdown("**Archive Warning**")
        render_items(result["warnings"])
        st.markdown("**Additional Tags**")
        render_items(result["tags"])


def format_created_at(value: Any) -> str:
    """Format Firestore timestamps for the Indonesian history interface."""
    if hasattr(value, "to_datetime"):
        value = value.to_datetime()
    if not isinstance(value, datetime):
        return "Tanggal tidak tersedia"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().strftime("%d %B %Y, %H:%M")


def render_history_page(user: dict[str, str], history_store: FirestoreHistory | None) -> None:
    st.title("Riwayat Analisis")
    if history_store is None:
        st.error("Firestore belum dikonfigurasi. Riwayat analisis tidak tersedia.")
        return

    try:
        history = history_store.list_history(user["uid"])
    except FirestoreHistoryError:
        st.error("Riwayat analisis tidak dapat dimuat. Silakan coba lagi.")
        return

    if not history:
        st.info("Belum ada riwayat analisis.")
        return

    for item in history:
        title = str(item.get("title") or "Tanpa judul")
        created_at = format_created_at(item.get("created_at"))
        language = str(item.get("language") or "Tidak diketahui")
        rating = str(item.get("rating") or "Tidak tersedia")
        warnings = item.get("warnings") or []
        tags = item.get("tags") or []

        with st.expander(f"{title} — {created_at}"):
            st.caption(f"{language} | {created_at}")
            st.markdown(f"**Content Rating:** {rating}")
            st.markdown("**Archive Warning**")
            render_items(warnings)
            st.markdown("**Additional Tags**")
            render_items(tags)
            st.markdown("**Cerita**")
            st.write(item.get("story") or "Tidak ada cerita tersimpan.")


def legacy_main() -> None:
    # =========================
    # Firebase Configuration
    # =========================
    api_key = get_firebase_api_key()

    if api_key is None:
        st.error(
            "Firebase belum dikonfigurasi. "
            "Tambahkan `firebase.api_key` ke Streamlit secrets."
        )
        return

    try:
        authenticator = get_authenticator(api_key)
    except ValueError:
        st.error("Konfigurasi Firebase tidak valid.")
        return

    # =========================
    # Authentication
    # =========================
    user = st.session_state.get("firebase_user")

    if not user:
        render_auth_page(authenticator)
        return

    # =========================
    # Sidebar Styling
    # =========================
    st.markdown(
        """
        <style>
        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #F8F7FC;
            border-right: 1px solid #E8E5F0;
        }

        section[data-testid="stSidebar"] > div {
            padding-top: 2rem;
        }

        /* Sidebar title */
        .sidebar-brand {
            padding: 0 0.5rem 1.5rem 0.5rem;
        }

        .sidebar-brand h1 {
            font-size: 1.6rem;
            font-weight: 700;
            color: #5B4B8A;
            margin: 0;
        }

        .sidebar-brand p {
            font-size: 0.78rem;
            color: #8A8499;
            margin-top: 0.2rem;
        }

        /* Account card */
        .account-card {
            background: white;
            border: 1px solid #E8E5F0;
            border-radius: 12px;
            padding: 0.85rem;
            margin-bottom: 1.5rem;
        }

        .account-label {
            font-size: 0.7rem;
            font-weight: 600;
            color: #9A94A8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.25rem;
        }

        .account-email {
            font-size: 0.82rem;
            color: #403B4A;
            word-break: break-word;
        }

        /* Menu label */
        .menu-label {
            font-size: 0.7rem;
            font-weight: 600;
            color: #9A94A8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin: 0 0 0.5rem 0.25rem;
        }

        /* Logout button */
        section[data-testid="stSidebar"] button {
            border-radius: 9px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

    # =========================
    # Sidebar Header
    # =========================
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <h1>✦ FanMeta</h1>
                <p>AI Metadata Assistant</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Account information
        st.markdown(
            f"""
            <div class="account-card">
                <div class="account-label">Account</div>
                <div class="account-email">
                    👤 {user['email']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # =========================
        # Navigation
        # =========================
        st.markdown(
            '<div class="menu-label">Menu</div>',
            unsafe_allow_html=True,
        )

        page = st.radio(
            "Menu",
            (
                "Analisis Cerita",
                "Riwayat Analisis",
            ),
            label_visibility="collapsed",
        )

        st.markdown("<br>", unsafe_allow_html=True)

    # =========================
    # Firestore
    # =========================
    service_account = get_firestore_service_account()
    history_store = None

    if service_account is not None:
        try:
            history_store = get_history_store(service_account)
        except FirestoreHistoryError:
            st.sidebar.warning(
                "Firestore tidak dapat dihubungkan."
            )

    # =========================
    # Logout
    # =========================
    with st.sidebar:
        st.markdown("---")

        if st.button(
            "↪  Keluar",
            use_container_width=True,
        ):
            logout()
            st.rerun()

    # =========================
    # Page Routing
    # =========================
    if page == "Riwayat Analisis":
        render_history_page(user, history_store)
    else:
        render_analysis_page(user, history_store)


if __name__ == "__main__":
    pass


def main() -> None:
    """Route users through the modular Streamlit views."""
    apply_theme()
    api_key = get_firebase_api_key()
    if api_key is None:
        st.error(tr("Firebase is not configured. Add `firebase.api_key` to Streamlit secrets.",
                    "Firebase belum dikonfigurasi. Tambahkan `firebase.api_key` ke Streamlit secrets."))
        return
    try:
        authenticator = get_authenticator(api_key)
    except ValueError:
        st.error(tr("The Firebase configuration is invalid.", "Konfigurasi Firebase tidak valid."))
        return

    user = st.session_state.get("firebase_user")
    page = st.session_state.get("page") or ("analysis" if user else "home")
    if not GALLERY_ENABLED and page in ("gallery", "work"):
        page = "analysis" if user else "home"
    if not user:
        if page not in GUEST_PAGES:
            # halaman khusus pengguna: login dulu, lalu kembali ke halaman itu
            st.session_state["after_login"] = page
            page = "login"
        if page in ("login", "register"):
            st.session_state["page"] = page
            (register if page == "register" else login).render(authenticator)
            return
    elif page in ("login", "register"):
        page = "analysis"
    st.session_state["page"] = page

    history_store = None
    service_account = get_firestore_service_account()
    if service_account is not None:
        try:
            history_store = get_history_store(service_account)
        except FirestoreHistoryError:
            st.warning(tr("Could not connect to Firestore. History is temporarily unavailable.",
                          "Firestore tidak dapat dihubungkan. Riwayat sementara tidak tersedia."))
    gallery_store = GalleryStore(history_store.client) if history_store is not None else None
    workspace_store = WorkspaceStore(history_store.client) if history_store is not None else None

    render_topbar(user)
    page_slot = st.empty()  # slot tunggal: isi halaman lama langsung terganti, tidak ada sisa pudar
    with page_slot.container():
        if page == "home":
            home.render(user, gallery_store)
        elif page == "workspace":
            workspace.render(user, workspace_store, history_store, get_predictor)
        elif page == "glossary":
            glossary.render()
        elif page in ("gallery", "work"):
            gallery.render(user, gallery_store)
        elif page == "history":
            history.render(user, history_store)
        elif page == "processing":
            processing.render(user, history_store, get_predictor)
        elif page == "results":
            results.render(history_store)
        else:
            analysis.render(user, history_store)
    render_footer()


if __name__ == "__main__":
    main()
