"""HTML helpers for the login & register views (styles live in styles.py)."""
import streamlit as st
from src.ui.components import asset_data_uri, disclaimer, render_preferences, tr


def art_panel() -> None:
    logo = asset_data_uri("logo_nobg", max_px=128)  # sesuaikan dengan nama file logomu (tanpa ekstensi)
    background = asset_data_uri("gambar_register", max_px=1600)
    # foto latar hanya dikirim di halaman login/register (dulu ikut di setiap halaman, ±1,2 MB per klik)
    st.markdown(
        "<style>div[data-testid='stColumn']:has(.auth-art-marker), div[data-testid='column']:has(.auth-art-marker) {"
        "background: linear-gradient(180deg, rgba(10,8,30,.55) 0%, rgba(10,8,30,.35) 45%, rgba(10,8,30,.75) 100%),"
        f"url('{background}') center / cover no-repeat, linear-gradient(135deg, #1b1740, #3b2f7a); }}</style>",
        unsafe_allow_html=True,
    )
    logo_html = f'<img src="{logo}" alt="">' if logo else '<span class="logo">✦</span>'
    heading = tr("Unlock the Perfect Metadata for Your Masterpiece", "Temukan Metadata Terbaik untuk Karyamu")
    body = tr("Paste or upload your English or Indonesian fanfiction, and FanMeta recommends its Archive of Our Own "
              "content rating, archive warnings, and additional tags.",
              "Tempel atau unggah fanfiksi berbahasa Inggris atau Indonesia, lalu FanMeta merekomendasikan content "
              "rating, archive warnings, dan additional tags-nya untuk Archive of Our Own.")
    st.markdown(
        f"""
        <span class="auth-art-marker"></span>
        <div class="auth-art">
            <div class="auth-brand">{logo_html}<span class="auth-brand-name">FanMeta</span></div>
            <div class="auth-copy">
                <h1>{heading}</h1>
                <p>{body}</p>
            </div>
            <div class="auth-disclaimer">{disclaimer()}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def preferences_row() -> None:
    """Pilihan bahasa & tema di pojok kanan atas form (halaman login/register tidak punya menu atas)."""
    with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", gap="small",
                      key="auth_prefs"):
        render_preferences("auth")


def form_title(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <span class="auth-form-marker"></span>
        <div class="auth-form-title"><h2>{title}</h2><p>{subtitle}</p></div>
        """,
        unsafe_allow_html=True,
    )
