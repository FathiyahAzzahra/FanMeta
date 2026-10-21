"""Landing page (mockup "Home · Welcome to FanMeta"): hero, fitur, cara kerja, dan ajakan mencoba."""
import streamlit as st

from src.gallery_store import GalleryError, GalleryStore
from src.ui import gallery as gallery_view
from src.ui.components import GALLERY_ENABLED, asset_data_uri, icon, icon_box, navigate, require_login, tr

# (ikon, (judul EN, judul ID), (isi EN, isi ID))
_FEATURES = [
    ("scan", ("A thoughtful second reader", "Pembaca kedua yang teliti"),
     ("Turn your prose into a suggested rating, archive warnings, and AO3-style tags.",
      "Ubah tulisanmu menjadi saran rating, archive warnings, dan tag ala AO3.")),
    ("layers", ("Chapter by chapter", "Bab demi bab"),
     ("See where each suggestion comes from. Reanalyze only what you change.",
      "Lihat asal setiap saran. Analisis ulang hanya bagian yang kamu ubah.")),
    ("library", ("A home for every story", "Rumah untuk setiap cerita"),
     ("Keep chapters, notes, and metadata together in your private workspace.",
      "Simpan bab, catatan, dan metadata bersama di workspace pribadimu.")),
    ("languages", ("Your words, understood", "Kata-katamu dipahami"),
     ("Write in English or Indonesian. FanMeta translates Indonesian for analysis with NLLB-200.",
      "Tulis dalam bahasa Inggris atau Indonesia. FanMeta menerjemahkan teks Indonesia dengan NLLB-200 untuk "
      "dianalisis.")),
]

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

    cards = "".join(f'<div class="home-feat">{icon_box(i)}<h3>{tr(*t)}</h3><p>{tr(*d)}</p></div>'
                    for i, t, d in _FEATURES)
    st.markdown(
        '<div class="home-head"><div class="home-h2">'
        + tr("Made for the stories you love to tell", "Dibuat untuk cerita yang kamu suka tulis") + "</div><span>"
        + tr("A little structure. A lot of possibility.", "Sedikit struktur. Banyak kemungkinan.") + "</span></div>"
        + f'<div class="home-feat-grid">{cards}</div>',
        unsafe_allow_html=True,
    )

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
