"""Glossary: penjelasan setiap metadata yang direkomendasikan FanMeta (bisa dibuka tamu).

Satu halaman berisi semua bagian (mengikuti mockup Figma). Hanya label yang benar-benar
direkomendasikan model yang ditampilkan.
"""
import html

import streamlit as st

from src.ui.components import BADGE_TONE, badge, icon, page_header

# Arti rating & warning mengikuti definisi AO3. Contoh tag AO3 per kategori mengikuti
# aturan rule-based label v2 di fanmeta_utils.py (label yang dipakai model aplikasi).
# Kalau model final memakai label v3, perbarui contoh tag di bawah.
RATINGS = [
    ("General Audiences", "General", "Suitable for all readers. No violence, adult themes, or sexual content "
     "that would be inappropriate for a general audience.", "a lighthearted reunion between old friends."),
    ("Teen And Up Audiences", "Teen", "May be inappropriate for readers under 13. Can include some swearing, "
     "mild violence, or non-graphic romantic and sexual references.", "a tense fight with no graphic injuries."),
    ("Mature", "Mature", "Adult themes such as sex, violence, or heavy subject matter, described less "
     "graphically than Explicit works.", "a bloody battle, or a love scene that fades to black."),
    ("Explicit", "Explicit", "Graphic content intended for adult readers only, such as explicit sex or very "
     "graphic violence.", "an explicitly described sex scene."),
]

WARNINGS = [
    ("Graphic Depictions Of Violence", "Violence is described in a gory, graphic, or detailed way."),
    ("Major Character Death", "A main character of the story dies."),
    ("Rape/Non-Con", "The story depicts sexual activity without consent."),
    ("No Archive Warnings Apply", "None of the three warnings above apply to the story."),
]

# (kategori, nama, arti, contoh tag AO3)
TAGS = [
    ("Emotion", "Angst", "Emotional pain, sadness, or heartbreak drives the story.",
     "Angst, Hurt No Comfort, Angst with a Happy Ending, Heartbreak"),
    ("Emotion", "Fluff", "Light, sweet, feel-good moments with little conflict.",
     "Fluff, Tooth-Rotting Fluff, Domestic Fluff, Fluff and Angst"),
    ("Emotion", "Hurt/Comfort", "One character suffers and another cares for them.",
     "Hurt/Comfort, Emotional Hurt/Comfort, Needs a Hug, Touch-Starved"),
    ("Emotion", "Whump", "A character is put through suffering, and the story lingers on their pain.",
     "Whump"),
    ("Tone", "Humor", "The story is meant to be funny.",
     "Humor, Humour, Attempt at Humor, Fluff and Humor"),
    ("Romance", "Established Relationship", "The main couple is already together when the story begins.",
     "Established Relationship"),
    ("Romance", "Pining", "A character longs for someone they love, often unsure if it is returned.",
     "Pining, Mutual Pining, Unrequited Love, Lovesick"),
    ("Relationships", "Family", "Family bonds are an important theme: parents, children, or siblings.",
     "Family, Found Family, Siblings, Parent-Child Relationship"),
    ("Relationships", "Friendship", "A platonic friendship sits at the heart of the story.",
     "Friendship, Bonding"),
    ("Setting", "Mythical Creatures", "Supernatural or mythical beings appear in the story.",
     "Vampire, Werewolf, Mermaid, Fae, Demon, Ghost, Elf, Siren"),
    ("Theme", "Mental Health", "The story deals with mental health issues or their treatment.",
     "Mental Health Issues, Depression, Anxiety, Trauma, Therapy, PTSD"),
    ("Sensitive content", "Alcohol", "Drinking, being drunk, hangovers, or alcoholism plays a part.",
     "Alcohol, Alcoholism, Drunk, Drunkenness, Hangover"),
    ("Sensitive content", "Blood/Injury", "Characters bleed or get physically injured.",
     "Blood, Injury, Injured Character, Minor Injuries"),
    ("Sensitive content", "Character Death", "A character dies, whether on-page or off-screen.",
     "Character Death, Major Character Death, Off-Screen Death"),
    ("Sensitive content", "Suicide", "Suicide, suicidal thoughts, or a suicide attempt is mentioned or shown.",
     "Suicide, Suicidal Thoughts, Suicide Attempt, Implied/Referenced Suicide"),
    ("Sensitive content", "Smut", "Sexual content. Usually comes with a Mature or Explicit rating.",
     "Smut, NSFW, and tags naming specific sexual acts or kinks"),
]

STEPS = [
    ("Reads the whole story", "The story is read in overlapping parts of 200 words. Indonesian text is "
     "translated to English with NLLB-200 first. The title is not analyzed."),
    ("Scores every label", "A RoBERTa model reads each part and an LSTM combines them. Every rating, "
     "warning, and tag gets a confidence score from 0% to 100%."),
    ("Picks the suggestions", "The rating with the highest score is chosen. A warning or tag is suggested "
     "when its score passes a threshold tuned on validation data, with at most five tags."),
    ("Combines chapters", "In Workspace, the story uses the highest chapter rating. Warnings and tags keep "
     "the chapters they came from."),
]


def _section(title: str, count: str = "", anchor: str = "") -> str:
    pill = f'<span class="gl-count">{html.escape(count)}</span>' if count else ""
    return f'<div class="gl-h2" id="{anchor}">{html.escape(title)}{pill}</div>'


def _rating_cards() -> str:
    cards = "".join(
        f'<div class="gl-card">{badge(short, BADGE_TONE[name.lower()])}<p class="gl-desc">{html.escape(desc)}</p>'
        f'<div class="gl-example">Example: {html.escape(example)}</div></div>'
        for name, short, desc, example in RATINGS
    )
    return f'<div class="gl-grid">{cards}</div>'


def _warning_card() -> str:
    items = "".join(
        f'<div class="gl-warn"><div class="gl-warn-name">{html.escape(name)}</div>'
        f'<p>{html.escape(desc)}</p></div>'
        for name, desc in WARNINGS
    )
    note = (f'<div class="gl-note">{icon("info", 16)}<span>A story can have more than one warning. '
            "<b>No Archive Warnings Apply</b> is only suggested when none of the other three are found. "
            "It does not mean the story has no sensitive content, so check the rating and tags too.</span></div>")
    return (f'<div class="gl-panel">{_section("Archive Warnings", "4 warnings", "gl-warnings")}'
            '<p class="gl-lead">Warnings flag specific sensitive content, not the overall maturity of a story. '
            f'Review them separately from the rating.</p><div class="gl-warn-grid">{items}</div>{note}</div>')


def _tag_cards(tags: list[tuple[str, str, str, str]]) -> str:
    cards = "".join(
        f'<div class="gl-card"><div class="gl-cat">{html.escape(cat)}</div>'
        f'<div class="gl-name">{html.escape(name)}</div><p class="gl-desc">{html.escape(desc)}</p>'
        f'<div class="gl-ex-label">Example AO3 tags</div><div class="gl-ex">{html.escape(ex)}</div></div>'
        for cat, name, desc, ex in tags
    )
    return f'<div class="gl-grid">{cards}</div>'


def _steps_panel() -> str:
    steps = "".join(
        f'<div class="gl-step"><span class="gl-step-n">{i}</span><div><div class="gl-step-t">{html.escape(t)}</div>'
        f"<p>{html.escape(d)}</p></div></div>"
        for i, (t, d) in enumerate(STEPS, start=1)
    )
    return (f'<div class="gl-how" id="gl-how"><div class="gl-how-left">{icon("sparkles", 22, "#635BFF")}'
            '<div class="gl-h2">Behind the suggestions</div>'
            "<p>Suggestions are a starting point, not a verdict. You know your story best, so always review "
            f'them before posting on AO3.</p></div><div class="gl-how-right">{steps}</div></div>')


def render() -> None:
    page_header("A little clarity for every tag.",
                "What each piece of metadata suggested by FanMeta means. Ratings and warnings follow the "
                "definitions used by Archive of Our Own (AO3).", kicker="The FanMeta field guide")
    st.markdown(
        '<nav class="gl-jump"><a href="#gl-rating" target="_self">Content Rating</a>'
        '<a href="#gl-warnings" target="_self">Archive Warnings</a>'
        '<a href="#gl-tags" target="_self">Additional Tags</a>'
        '<a href="#gl-how" target="_self">Behind the suggestions</a></nav>',
        unsafe_allow_html=True,
    )

    st.markdown(_section("Content Rating", "4 ratings", "gl-rating")
                + '<p class="gl-lead">Every story gets exactly <b>one</b> rating. It tells readers how mature '
                "the content is.</p>" + _rating_cards(), unsafe_allow_html=True)

    st.markdown(_warning_card(), unsafe_allow_html=True)

    head, search = st.columns([2, 1], vertical_alignment="bottom")
    with head:
        st.markdown(_section("Additional Tags", "16 categories", "gl-tags")
                    + '<p class="gl-lead">AO3 authors write thousands of different tags. FanMeta groups them '
                    "into 16 categories and suggests up to five per story.</p>", unsafe_allow_html=True)
    with search:
        query = st.text_input("Search tags", placeholder="Search tags or meanings", key="gl_search",
                              icon=":material/search:", label_visibility="collapsed").strip().lower()
    shown = [t for t in TAGS if not query or query in " ".join(t).lower()]
    if shown:
        st.markdown(_tag_cards(shown), unsafe_allow_html=True)
    else:
        st.info("Tidak ada tag yang cocok.")

    st.markdown(_steps_panel(), unsafe_allow_html=True)
