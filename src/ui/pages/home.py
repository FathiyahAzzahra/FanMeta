"""Landing page (mockup "Home · Welcome to FanMeta"): hero, fitur, cara kerja, dan ajakan mencoba."""
import streamlit as st

from src.services.gallery_store import GalleryError, GalleryStore
from src.ui.pages import gallery as gallery_view
from src.ui.components import (GALLERY_ENABLED, asset_data_uri, icon, icon_box, navigate, navigate_cb, require_login,
                               tr)

# kotak fitur yang bisa diklik: (ikon, halaman tujuan, (judul EN, ID), (isi EN, ID), (tombol EN, ID))
_FEATURES = [
    ("scan", "analysis", ("Quick Analysis", "Analisis Cepat"),
     ("Paste or upload one story in English or Indonesian and get a suggested rating, warnings, and tags.",
      "Tempel atau unggah satu cerita berbahasa Inggris atau Indonesia, lalu dapatkan saran rating, warning, "
      "dan tag."),
     ("Analyze a story", "Analisis cerita")),
    ("library", "workspace", ("Workspace", "Workspace"),
     ("Keep stories chapter by chapter, write in the editor, and reanalyze only the chapters you change.",
      "Simpan cerita per bab, tulis di editor, lalu analisis ulang hanya bab yang kamu ubah."),
     ("Open Workspace", "Buka Workspace")),
    ("clock", "history", ("History", "Riwayat"),
     ("Search, reopen, or delete every analysis you have run, from Quick Analysis or Workspace.",
      "Cari, buka lagi, atau hapus semua hasil analisis, baik dari Analisis Cepat maupun Workspace."),
     ("View history", "Lihat riwayat")),
    ("book", "glossary", ("Glossary", "Glosarium"),
     ("Learn what each AO3 rating, archive warning, and tag category suggested by FanMeta means.",
      "Pelajari arti setiap rating, archive warning, dan kategori tag AO3 yang disarankan FanMeta."),
     ("Open glossary", "Buka glosarium")),
]
# key session yang direset supaya halaman tujuan selalu terbuka di tampilan daftarnya
_RESET = {"workspace": "ws_view", "history": "history_detail"}

_HOW_IT_WORKS = [
    (("Bring your story", "Bawa ceritamu"),
     ("Paste a chapter for a quick analysis, or create a story in your workspace.",
      "Tempel satu bab untuk analisis cepat, atau buat cerita di workspace-mu.")),
    (("Let us read between the lines", "Biar kami membaca di antara baris"),
     ("We check each chapter for rating, warnings, and relevant themes.",
      "Kami memeriksa rating, warning, dan tema yang relevan di setiap bab.")),
    (("Review the suggestions", "Periksa sarannya"),
     ("Explore clear recommendations with confidence scores and chapter references.",
      "Lihat rekomendasi yang jelas lengkap dengan skor keyakinan dan sumber babnya.")),
    (("Make it your own", "Sesuaikan dengan ceritamu"),
     ("Keep what fits, edit what doesn't, and post on AO3 with confidence.",
      "Pakai yang cocok, ubah yang tidak, lalu unggah ke AO3 dengan percaya diri.")),
]


def _open_feature(target: str, user: dict[str, str] | None) -> None:
    """Callback kotak fitur: tamu diminta login dulu (kecuali Glosarium), lalu kembali ke fitur itu."""
    if target in _RESET:
        st.session_state.pop(_RESET[target], None)
    if not user and target != "glossary":
        st.session_state["after_login"] = target
        target = "login"
    navigate_cb(target)


def _analyze(user: dict[str, str] | None) -> None:
    if user:
        navigate("analysis")
    else:
        require_login("analysis")


def render(user: dict[str, str] | None, gallery: GalleryStore | None) -> None:
    art = asset_data_uri("gambar_register", max_px=1100)
    with st.container(key="hero"):
        text, picture = st.columns([1.12, 1], gap="large", vertical_alignment="center")
        with text:
            st.markdown(
                f"""
                <div class="hero-kicker">{icon("sparkles", 15)}{tr("Less guesswork. More storytelling.",
                                                                   "Lebih sedikit menebak. Lebih banyak bercerita.")}</div>
                <h1 class="hero-h1">{tr("Find the perfect metadata for your fanfiction",
                                        "Temukan metadata terbaik untuk fanfiksimu")}</h1>
                <p class="hero-p">{tr("You write the adventure. We help with the labels. Discover thoughtful AO3 "
                                      "metadata suggestions, with your creative judgment always at the heart.",
                                      "Kamu menulis petualangannya, kami bantu labelnya. Dapatkan saran metadata AO3 "
                                      "yang cermat, dengan keputusan kreatif tetap di tanganmu.")}</p>
                """,
                unsafe_allow_html=True,
            )
            with st.container(horizontal=True, gap="small"):
                if st.button(tr("Analyze Now", "Analisis Sekarang"), key="home_analyze", type="primary",
                             icon=":material/arrow_forward:"):
                    _analyze(user)
                if GALLERY_ENABLED:
                    if st.button(tr("Read Stories", "Baca Cerita"), key="home_read"):
                        navigate("gallery")
                elif st.button(tr("Learn the Metadata", "Pelajari Metadata"), key="home_read"):
                    navigate("glossary")
            st.markdown('<p class="hero-note">' + tr("Free to use · Your stories stay private · You decide what fits",
                                                     "Gratis · Ceritamu tetap pribadi · Kamu yang menentukan")
                        + "</p>", unsafe_allow_html=True)
        with picture:
            st.markdown(f'<div class="hero-art" style="background-image:url(\'{art}\')"></div>',
                        unsafe_allow_html=True)

    st.markdown(
        '<div class="home-head"><div class="home-h2">'
        + tr("Everything FanMeta can do", "Semua fitur FanMeta") + "</div><span>"
        + tr("Pick a place to start.", "Pilih tempat untuk mulai.") + "</span></div>",
        unsafe_allow_html=True,
    )
    for col, (ic, target, title, desc, cta) in zip(st.columns(len(_FEATURES), gap="medium"), _FEATURES):
        with col, st.container(key=f"home_card_{target}"):
            st.markdown(f'<div class="home-feat-body">{icon_box(ic)}<h3>{tr(*title)}</h3><p>{tr(*desc)}</p></div>',
                        unsafe_allow_html=True)
            st.button(tr(*cta), key=f"home_go_{target}", type="tertiary", icon=":material/arrow_forward:",
                      icon_position="right", on_click=_open_feature, args=(target, user))

    if GALLERY_ENABLED and gallery:
        try:
            latest = gallery_view.cached_works(gallery)[:3]
        except GalleryError:
            latest = []
        if latest:
            st.markdown('<div class="home-head"><div class="home-h2">'
                        + tr("Latest from the gallery", "Terbaru dari galeri") + "</div></div>", unsafe_allow_html=True)
            gallery_view.render_grid(latest, key_prefix="home")
    else:
        steps = "".join(f'<div class="home-step"><div class="home-step-n">{i:02d}</div><h3>{tr(*t)}</h3><p>{tr(*d)}</p></div>'
                        for i, (t, d) in enumerate(_HOW_IT_WORKS, start=1))
        st.markdown('<div class="home-head"><div class="home-h2">' + tr("How FanMeta works", "Cara kerja FanMeta")
                    + f'</div></div><div class="home-steps">{steps}</div>', unsafe_allow_html=True)

    with st.container(key="home_cta", horizontal=True, vertical_alignment="center"):
        st.markdown('<div class="cta-t">' + tr("Your next chapter starts here.", "Bab berikutnya dimulai di sini.")
                    + '</div><div class="cta-s">' + tr(
                        "More time for your characters. Less time second-guessing your tags.",
                        "Lebih banyak waktu untuk tokoh-tokohmu. Lebih sedikit waktu meragukan tag.") + "</div>",
                    unsafe_allow_html=True)
        if st.button(tr("Analyze your story", "Analisis ceritamu"), key="home_cta_btn", type="primary",
                     icon=":material/arrow_forward:"):
            _analyze(user)
