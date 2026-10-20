"""Landing page (mockup "Home · Welcome to FanMeta"): hero, fitur, cara kerja, dan ajakan mencoba."""
import html

import streamlit as st

from src.gallery_store import GalleryError, GalleryStore
from src.ui import gallery as gallery_view
from src.ui.components import GALLERY_ENABLED, asset_data_uri, badge, icon, icon_box, navigate, require_login

_FEATURES = [
    ("scan", "A thoughtful second reader",
     "Turn your prose into a suggested rating, archive warnings, and AO3-style tags."),
    ("layers", "Chapter by chapter", "See where each suggestion comes from. Reanalyze only what you change."),
    ("library", "A home for every story", "Keep chapters, notes, and metadata together in your private workspace."),
    ("languages", "Your words, understood",
     "Write in English or Indonesian. FanMeta translates Indonesian for analysis with NLLB-200."),
]

_HOW_IT_WORKS = [
    ("Bring your story", "Paste a chapter for a quick analysis, or create a story in your workspace."),
    ("Let us read between the lines", "We check each chapter for rating, warnings, and relevant themes."),
    ("Review the suggestions", "Explore clear recommendations with confidence scores and chapter references."),
    ("Make it your own", "Keep what fits, edit what doesn't, and post on AO3 with confidence."),
]

# contoh kartu di atas foto hero; label diambil dari label yang benar-benar bisa disarankan model
_SAMPLE = ("Salt and Thunder", ("Mature", "orange"), ("Angst", "grey"), ("Hurt/Comfort", "grey"))


def _analyze(user: dict[str, str] | None) -> None:
    if user:
        navigate("analysis")
    else:
        require_login("analysis")


def render(user: dict[str, str] | None, gallery: GalleryStore | None) -> None:
    art = asset_data_uri("gambar_register", max_px=1100)
    title, *labels = _SAMPLE
    with st.container(key="hero"):
        text, picture = st.columns([1.12, 1], gap="large", vertical_alignment="center")
        with text:
            st.markdown(
                f"""
                <div class="hero-kicker">{icon("sparkles", 15)}Less guesswork. More storytelling.</div>
                <h1 class="hero-h1">Find the perfect metadata for your fanfiction</h1>
                <p class="hero-p">You write the adventure. We help with the labels. Discover thoughtful AO3
                metadata suggestions, with your creative judgment always at the heart.</p>
                """,
                unsafe_allow_html=True,
            )
            with st.container(horizontal=True, gap="small"):
                if st.button("Analyze Now", key="home_analyze", type="primary", icon=":material/arrow_forward:"):
                    _analyze(user)
                if GALLERY_ENABLED:
                    if st.button("Read Stories", key="home_read"):
                        navigate("gallery")
                elif st.button("Learn the Metadata", key="home_read"):
                    navigate("glossary")
            st.markdown('<p class="hero-note">Free to use · Your stories stay private · You decide what fits</p>',
                        unsafe_allow_html=True)
        with picture:
            chips = "".join(badge(name, tone) for name, tone in labels)
            st.markdown(
                f"""
                <div class="hero-art" style="background-image:url('{art}')">
                  <div class="hero-sample"><div class="hero-sample-top"><span>{html.escape(title)}</span>
                    {badge("AI suggestions", "violet")}</div><div class="hero-sample-tags">{chips}</div></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    cards = "".join(f'<div class="home-feat">{icon_box(i)}<h3>{t}</h3><p>{d}</p></div>' for i, t, d in _FEATURES)
    st.markdown(
        '<div class="home-head"><div class="home-h2">Made for the stories you love to tell</div>'
        '<span>A little structure. A lot of possibility.</span></div>'
        f'<div class="home-feat-grid">{cards}</div>',
        unsafe_allow_html=True,
    )

    if GALLERY_ENABLED and gallery:
        try:
            latest = gallery_view.cached_works(gallery)[:3]
        except GalleryError:
            latest = []
        if latest:
            st.markdown('<div class="home-head"><div class="home-h2">Latest from the gallery</div></div>', unsafe_allow_html=True)
            gallery_view.render_grid(latest, key_prefix="home")
    else:
        steps = "".join(f'<div class="home-step"><div class="home-step-n">{i:02d}</div><h3>{t}</h3><p>{d}</p></div>'
                        for i, (t, d) in enumerate(_HOW_IT_WORKS, start=1))
        st.markdown(f'<div class="home-head"><div class="home-h2">How FanMeta works</div></div><div class="home-steps">{steps}</div>',
                    unsafe_allow_html=True)

    with st.container(key="home_cta", horizontal=True, vertical_alignment="center"):
        st.markdown('<div class="cta-t">Your next chapter starts here.</div>'
                    '<div class="cta-s">More time for your characters. Less time second-guessing your tags.</div>',
                    unsafe_allow_html=True)
        if st.button("Analyze your story", key="home_cta_btn", type="primary", icon=":material/arrow_forward:"):
            _analyze(user)
