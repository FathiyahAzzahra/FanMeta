"""FanMeta entry point. Run with: streamlit run app.py.

Isi file ini hanya tiga hal:
1. resource bersama yang di-cache (model, Firebase, Firestore),
2. aturan akses halaman (tamu vs. pengguna login),
3. router: tabel ROUTES yang menghubungkan nama halaman dengan fungsi render di src/ui/pages/.
Halaman berpindah lewat ``navigate("<nama>")`` (src/ui/components.py), yang menyimpan nama halaman
di ``st.session_state["page"]``.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import streamlit as st
from PIL import Image

from src.ml.model_api import load_predictor
from src.services.firebase_auth import FirebaseAuth
from src.services.firestore_history import FirestoreHistory, FirestoreHistoryError
from src.services.gallery_store import GalleryStore
from src.services.workspace_store import WorkspaceStore
from src.ui.components import GALLERY_ENABLED, render_footer, render_topbar, tr
from src.ui.pages import (analysis, gallery, glossary, history, home, login, processing, register, results,
                          workspace)
from src.ui.styles import apply_theme

ASSETS_DIR = Path(__file__).parent / "src" / "assets"
DEFAULT_PAGE = "home"
GUEST_PAGES = {"home", "gallery", "work", "glossary", "login", "register"}  # boleh dibuka tanpa login
AUTH_PAGES = {"login": login, "register": register}

st.set_page_config(page_title="FanMeta", page_icon=Image.open(ASSETS_DIR / "logo_nobg.png"), layout="wide")


# ---------------------------------------------------------------- resource bersama (dimuat sekali)
@st.cache_resource(show_spinner=False)
def get_predictor() -> Any:
    """Model FanMeta (lokal) atau klien Space Hugging Face; dimuat sekali selama aplikasi berjalan."""
    return load_predictor()


@st.cache_resource
def get_authenticator(api_key: str) -> FirebaseAuth:
    """Create a reusable Firebase client from a Streamlit secret."""
    return FirebaseAuth(api_key)


@st.cache_resource
def get_history_store(service_account: dict[str, str]) -> FirestoreHistory:
    """Cache the Firestore client instead of reconnecting on every rerun."""
    return FirestoreHistory.from_service_account(service_account)


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


# ---------------------------------------------------------------- router
@dataclass
class AppContext:
    """Semua yang dibutuhkan halaman; diteruskan router ke fungsi render."""
    user: dict[str, str] | None
    history_store: FirestoreHistory | None
    gallery_store: GalleryStore | None
    workspace_store: WorkspaceStore | None


ROUTES: dict[str, Callable[[AppContext], None]] = {
    "home": lambda c: home.render(c.user, c.gallery_store),
    "analysis": lambda c: analysis.render(c.user, c.history_store),
    "processing": lambda c: processing.render(c.user, c.history_store, get_predictor),
    "results": lambda c: results.render(c.history_store),
    "workspace": lambda c: workspace.render(c.user, c.workspace_store, c.history_store, get_predictor),
    "history": lambda c: history.render(c.user, c.history_store),
    "glossary": lambda c: glossary.render(),
    "gallery": lambda c: gallery.render(c.user, c.gallery_store),
    "work": lambda c: gallery.render(c.user, c.gallery_store),  # detail satu karya di galeri
}


def resolve_page(user: dict[str, str] | None) -> str:
    """Halaman yang boleh dibuka sekarang, sesuai status login."""
    page = st.session_state.get("page") or DEFAULT_PAGE
    if page not in ROUTES and page not in AUTH_PAGES:
        page = DEFAULT_PAGE
    if not GALLERY_ENABLED and page in ("gallery", "work"):
        page = DEFAULT_PAGE
    if not user and page not in GUEST_PAGES:
        st.session_state["after_login"] = page  # login dulu, lalu kembali ke halaman ini
        page = "login"
    elif user and page in AUTH_PAGES:
        page = DEFAULT_PAGE
    st.session_state["page"] = page
    return page


def connect_stores() -> AppContext:
    history_store = None
    service_account = get_firestore_service_account()
    if service_account is not None:
        try:
            history_store = get_history_store(service_account)
        except FirestoreHistoryError:
            st.warning(tr("Could not connect to Firestore. History is temporarily unavailable.",
                          "Firestore tidak dapat dihubungkan. Riwayat sementara tidak tersedia."))
    client = history_store.client if history_store is not None else None
    return AppContext(
        user=st.session_state.get("firebase_user"),
        history_store=history_store,
        gallery_store=GalleryStore(client) if client is not None else None,
        workspace_store=WorkspaceStore(client) if client is not None else None,
    )


def main() -> None:
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

    page = resolve_page(st.session_state.get("firebase_user"))
    if page in AUTH_PAGES:  # halaman login/daftar punya tata letak sendiri (tanpa topbar & footer)
        AUTH_PAGES[page].render(authenticator)
        return

    ctx = connect_stores()
    render_topbar(ctx.user)
    page_slot = st.empty()  # slot tunggal: isi halaman lama langsung terganti, tidak ada sisa pudar
    with page_slot.container():
        ROUTES[page](ctx)
    render_footer()


main()
