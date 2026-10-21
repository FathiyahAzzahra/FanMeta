"""Reusable navigation and display components."""

import base64
import html
import io
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st
from PIL import Image

from src.i18n import (  # noqa: F401 - format_relative/format_date juga dipakai modul lain lewat sini
    format_date, format_relative, lang, set_lang, theme, toggle_theme, tr,
)

_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

# ubah ke False untuk menyembunyikan seluruh fitur galeri publik (menu, Publish, tombol Read)
GALLERY_ENABLED = False

LANGUAGE_LABEL = {"Bahasa Indonesia": "Indonesian", "Bahasa Inggris": "English"}  # lama; pakai i18n.language_label
RATING_BADGE = {
    "general audiences": ("General", "rb-general"),
    "teen and up audiences": ("Teen", "rb-teen"),
    "mature": ("Mature", "rb-mature"),
    "explicit": ("Explicit", "rb-explicit"),
}
ADULT_RATINGS = {"mature", "explicit"}


def navigate(page: str) -> None:
    st.session_state["page"] = page
    st.rerun()


def navigate_cb(page: str) -> None:
    """Versi callback (on_click) dari navigate: tanpa st.rerun."""
    st.session_state["page"] = page


@st.cache_data(show_spinner=False, max_entries=16)
def asset_data_uri(stem: str, max_px: int | None = None) -> str:
    """Cari src/asset/<stem>.(png|jpg|jpeg|webp) dan kembalikan sebagai data URI.

    Hasilnya di-cache. ``max_px`` memperkecil gambar (sisi terpanjang) supaya data yang dikirim
    ke browser setiap kali halaman dijalankan ulang tetap kecil (foto asli ±1 MB).
    """
    roots = [Path.cwd() / "src" / "asset", Path.cwd() / "asset"]
    roots += [p / "asset" for p in Path(__file__).resolve().parents]
    for root in roots:
        for ext, mime in _MIME.items():
            path = root / f"{stem}{ext}"
            if not path.exists():
                continue
            data = path.read_bytes()
            if max_px:
                with Image.open(io.BytesIO(data)) as img:
                    img.thumbnail((max_px, max_px))
                    out = io.BytesIO()
                    if mime == "image/png":
                        img.save(out, format="PNG", optimize=True)
                    else:
                        img.convert("RGB").save(out, format="JPEG", quality=82, optimize=True)
                    data = out.getvalue()
            return f"data:{mime};base64," + base64.b64encode(data).decode()
    return ""


def _logout() -> None:
    st.session_state.pop("firebase_user", None)
    for key in ("history_detail", "after_login"):
        st.session_state.pop(key, None)
    st.session_state["page"] = "home"


def open_dialog(title: str, icon: str, body: Any, *args: Any) -> None:
    """Buka st.dialog dengan judul sesuai bahasa (judul decorator @st.dialog tidak bisa berubah)."""
    st.dialog(title, icon=icon)(body)(*args)


def _logout_body() -> None:
    # pop-up konfirmasi agar pengguna tidak keluar tanpa sengaja
    st.markdown('<p class="dlg-text">' + tr(
        "Your stories, notes, and analysis results are safely saved in your workspace. "
        "Log in again whenever you're ready to write.",
        "Cerita, catatan, dan hasil analisismu tersimpan aman di workspace. "
        "Masuk lagi kapan pun kamu siap menulis.") + "</p>", unsafe_allow_html=True)
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button(tr("Cancel", "Batal"), key="logout_cancel"):
            st.rerun()
        if st.button(tr("Log out", "Keluar"), key="logout_confirm", type="primary"):
            _logout()
            st.rerun()


def _confirm_logout() -> None:
    open_dialog(tr("Log out of FanMeta?", "Keluar dari FanMeta?"), ":material/logout:", _logout_body)


def danger_box(title: str, lines: list[str], icon_name: str = "book") -> str:
    """Kotak merah ringkasan isi yang akan dihapus (pop-up hapus)."""
    body = "".join(f"<span>{html.escape(line)}</span>" for line in lines)
    return (f'<div class="dlg-danger">{icon(icon_name, 18, "#d04452")}<div><b>{html.escape(title)}</b>{body}</div></div>')


# ikon garis bergaya Lucide (sama dengan mockup Figma); dipakai di dalam HTML
_ICON_PATHS = {
    "library": '<path d="m16 6 4 14"/><path d="M12 6v14"/><path d="M8 8v12"/><path d="M4 4v16"/>',
    "feather": '<path d="M12.67 19a2 2 0 0 0 1.416-.588l6.154-6.172a6 6 0 0 0-8.49-8.49L5.586 9.914A2 2 0 0 0 5 '
               '11.328V18a1 1 0 0 0 1 1z"/><path d="M16 8 2 22"/><path d="M17.5 15H9"/>',
    "sparkles": '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 '
                '8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 '
                '14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/>',
    "lock": '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "files": '<path d="M20 7h-3a2 2 0 0 1-2-2V2"/><path d="M9 18a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h7l4 4v10a2 2 0 0 1-2 '
             '2Z"/><path d="M3 7.6v12.8A1.6 1.6 0 0 0 4.6 22h9.8"/>',
    "book": '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 '
            '1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "languages": '<path d="m5 8 6 6"/><path d="m4 14 6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="m22 '
                 '22-5-10-5 10"/><path d="M14 18h6"/>',
    "scan": '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 '
            '2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/><path d="M7 8h8"/><path d="M7 16h6"/>',
    "layers": '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 '
              '1 0 0 0 0-1.83z"/><path d="M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 '
              '12"/><path d="M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17"/>',
    "trash": '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 '
             '1 2 2v2"/><path d="M10 11v6"/><path d="M14 11v6"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
    "folder_plus": '<path d="M12 10v6"/><path d="M9 13h6"/><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 '
                   '1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
}


def icon(name: str, size: int = 18, color: str = "currentColor") -> str:
    return (f'<svg class="ic" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f'{_ICON_PATHS[name]}</svg>')


def icon_box(name: str, size: int = 20) -> str:
    """Ikon ungu di dalam kotak ungu lembut, seperti kartu statistik/fitur di mockup."""
    return f'<span class="ic-box">{icon(name, size, "#635BFF")}</span>'


# warna badge diambil langsung dari mockup Figma
BADGE_TONE = {
    "general audiences": "blue", "teen and up audiences": "violet", "mature": "orange", "explicit": "red",
    "draft": "grey", "ongoing": "violet", "complete": "green", "hiatus": "orange",
    "analyzed": "green", "changed": "orange", "not analyzed": "grey", "empty": "grey",
}


def badge(text: str, tone: str | None = None) -> str:
    tone = tone or BADGE_TONE.get(str(text).strip().lower(), "grey")
    return f'<span class="bdg bdg-{tone}">{html.escape(str(text))}</span>'


# status cerita disimpan dalam bahasa Inggris (Draft/Ongoing/...); ini hanya teks tampilannya
_STATUS_ID = {"Draft": "Draf", "Ongoing": "Berjalan", "Complete": "Selesai", "Hiatus": "Hiatus"}


def status_label(status: str) -> str:
    return tr(status, _STATUS_ID.get(status, status))


def status_badge(status: str) -> str:
    status = str(status or "-")
    return badge(status_label(status), BADGE_TONE.get(status.lower(), "grey"))


def page_header(title: str, sub: str = "", kicker: str = "") -> None:
    kicker_html = f'<div class="pg-kicker">{html.escape(kicker)}</div>' if kicker else ""
    sub_html = f'<p class="pg-sub">{html.escape(sub)}</p>' if sub else ""
    st.markdown(f'{kicker_html}<h1 class="pg-h1">{html.escape(title)}</h1>{sub_html}', unsafe_allow_html=True)


def breadcrumb(parts: list[tuple[str, Any]], key: str) -> None:
    """parts = [(label, callback atau None)]; bagian yang punya callback bisa diklik."""
    with st.container(horizontal=True, gap=None, vertical_alignment="center"):
        st.markdown('<span class="bc-marker"></span>', unsafe_allow_html=True)
        for i, (label, callback) in enumerate(parts):
            if i:
                st.markdown('<span class="bc-sep">/</span>', unsafe_allow_html=True)
            if callback is not None:
                st.button(label, key=f"bc_{key}_{i}", on_click=callback, type="tertiary")
            else:
                st.markdown(f'<span class="bc-current">{html.escape(label)}</span>', unsafe_allow_html=True)


def disclaimer() -> str:
    return tr("FanMeta is not affiliated with Archive of Our Own (AO3) or the Organization for Transformative "
              "Works. Metadata terms follow the AO3 schema.",
              "FanMeta tidak berafiliasi dengan Archive of Our Own (AO3) atau Organization for Transformative "
              "Works. Istilah metadata mengikuti skema AO3.")


def render_footer() -> None:
    st.markdown(f'<div class="app-footer">{disclaimer()}</div>', unsafe_allow_html=True)


def default_name(user: dict[str, str]) -> str:
    email = user.get("email", "") or ""
    return user.get("display_name") or user.get("name") or (email.split("@")[0] if email else "User")


def require_login(next_page: str) -> None:
    """Arahkan tamu ke login, lalu kembali ke next_page setelah berhasil login."""
    st.session_state["after_login"] = next_page
    navigate("login")


def rating_badge(rating: str) -> str:
    text, _ = RATING_BADGE.get(str(rating).strip().lower(), (rating or "-", ""))
    return badge(text, BADGE_TONE.get(str(rating).strip().lower(), "grey"))


# (label EN, label ID, halaman tujuan, halaman yang membuat menu ini aktif, key session yang direset saat diklik)
_NAV_USER = [
    ("Quick Analysis", "Analisis Cepat", "analysis", ("analysis", "processing", "results"), None),
    ("Workspace", "Workspace", "workspace", ("workspace",), "ws_view"),
    ("History", "Riwayat", "history", ("history",), "history_detail"),
]
# tamu: Quick Analysis meminta login dulu (seperti mockup); logo FanMeta kembali ke Home
_NAV_GUEST = [("Quick Analysis", "Analisis Cepat", "analysis", ("analysis",), None)]
GUEST_ONLY_LOGIN = {"analysis"}
_NAV_GALLERY = ("Gallery", "Galeri", "gallery", ("gallery", "work"), "gallery_work")
_NAV_GLOSSARY = ("Glossary", "Glosarium", "glossary", ("glossary",), None)


def _display_name(user: dict[str, str]) -> tuple[str, str]:
    """('Alex W.', 'AW') dari nama/email, seperti di mockup."""
    raw = default_name(user)
    parts = [p for p in re.split(r"[._\s-]+", raw) if p]
    shown = " ".join(p.capitalize() + ("." if len(p) == 1 else "") for p in parts) or raw
    initials = "".join(p[0] for p in parts[:2]).upper() or raw[:1].upper()
    return shown, initials


def _nav_button(label: str, target: str, active: bool, reset_key: str | None = None) -> None:
    if st.button(label, key=f"nav_{target}" + ("_active" if active else "")):
        if reset_key:
            st.session_state.pop(reset_key, None)  # selalu kembali ke halaman daftar
        if target in GUEST_ONLY_LOGIN and not st.session_state.get("firebase_user"):
            require_login(target)
        navigate(target)


def render_topbar(user: dict[str, str] | None) -> None:
    page = st.session_state.get("page", "analysis" if user else "home")
    items = list(_NAV_USER if user else _NAV_GUEST)
    if GALLERY_ENABLED:
        items.append(_NAV_GALLERY)
    items.append(_NAV_GLOSSARY)

    logo = asset_data_uri("logo_nobg", max_px=128)
    logo_html = f'<img src="{logo}" alt="">' if logo else '<span class="tb-logo-fallback">✦</span>'

    with st.container(key="topbar"):
        _topbar_row(user, page, items, logo_html)


def _topbar_row(user: dict[str, str] | None, page: str, items: list, logo_html: str) -> None:
    brand, nav, right = st.columns([1.15, 2.9, 1.75], vertical_alignment="center")
    with brand:
        with st.container(horizontal=True, gap="small", vertical_alignment="center"):
            st.markdown(f'<span class="topbar-marker"></span><span class="tb-logo">{logo_html}</span>',
                        unsafe_allow_html=True)
            st.button("FanMeta", key="tb_brand", type="tertiary", on_click=navigate_cb,
                      args=("analysis" if user else "home",))
    with nav:
        with st.container(horizontal=True, horizontal_alignment="center", gap="medium"):
            for label_en, label_id, target, active_pages, reset_key in items:
                _nav_button(tr(label_en, label_id), target, page in active_pages, reset_key)
            if user and st.button(tr("Logout", "Keluar"), key="nav_logout"):
                _confirm_logout()
    with right:
        with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", gap="small"):
            render_preferences("tb")
            if user:
                name, initials = _display_name(user)
                st.markdown(f'<div class="tb-user"><span>{html.escape(name)}</span>'
                            f'<span class="tb-avatar" title="{html.escape(user.get("email", ""))}">'
                            f"{html.escape(initials)}</span></div>", unsafe_allow_html=True)
            else:
                st.button(tr("Log in", "Masuk"), key="tb_login", type="tertiary", on_click=navigate_cb,
                          args=("login",))
                st.button(tr("Get started", "Daftar"), key="tb_register", type="primary", on_click=navigate_cb,
                          args=("register",))


def _on_lang_change(key: str) -> None:
    value = st.session_state.get(key)
    if value:  # klik ulang pilihan yang aktif = tidak memilih apa-apa; abaikan
        set_lang(value.lower())


def render_preferences(prefix: str) -> None:
    """Tombol EN | ID dan tombol terang/gelap (dipakai di menu atas dan halaman login/register)."""
    key = f"{prefix}_lang"
    st.session_state[key] = lang().upper()  # selalu ikut pilihan terakhir (bisa diubah dari halaman lain)
    st.segmented_control(tr("Language", "Bahasa"), ["EN", "ID"], key=key, label_visibility="collapsed",
                         on_change=_on_lang_change, args=(key,), width="content")
    dark = theme() == "dark"
    st.button("", key=f"{prefix}_theme", icon=":material/light_mode:" if dark else ":material/dark_mode:",
              type="tertiary", help=tr("Switch to light mode", "Ganti ke mode terang") if dark
              else tr("Switch to dark mode", "Ganti ke mode gelap"), on_click=toggle_theme)


def render_labels(items: list[str], kind: str = "") -> None:
    if not items:
        st.markdown('<span class="empty-copy">' + tr("No label passed the prediction threshold.",
                                                    "Tidak ada label di atas ambang prediksi.") + "</span>",
                    unsafe_allow_html=True)
        return
    class_name = f"pill {kind}".strip()
    st.markdown(
        "".join(f'<span class="{class_name}">{html.escape(str(item))}</span>' for item in items),
        unsafe_allow_html=True,
    )


def format_created_at(value: Any) -> str:
    return format_date(value, with_time=True)
