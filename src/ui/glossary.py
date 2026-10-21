"""Glossary: penjelasan setiap metadata yang direkomendasikan FanMeta (bisa dibuka tamu).

Satu halaman berisi semua bagian (mengikuti mockup Figma). Hanya label yang benar-benar
direkomendasikan model yang ditampilkan. Nama label & contoh tag AO3 tetap bahasa Inggris
(istilah resmi AO3); penjelasannya tersedia dalam dua bahasa: (English, Indonesia).
"""
import html

import streamlit as st

from src.ui.components import BADGE_TONE, badge, icon, page_header, tr

# Arti rating & warning mengikuti definisi AO3. Contoh tag AO3 per kategori mengikuti
# aturan rule-based label v2 di fanmeta_utils.py (label yang dipakai model aplikasi).
# Kalau model final memakai label v3, perbarui contoh tag di bawah.
RATINGS = [
    ("General Audiences", "General",
     ("Suitable for all readers. No violence, adult themes, or sexual content that would be inappropriate for a "
      "general audience.",
      "Cocok untuk semua pembaca. Tidak ada kekerasan, tema dewasa, atau konten seksual yang tidak pantas untuk "
      "pembaca umum."),
     ("a lighthearted reunion between old friends.", "reuni hangat antara teman lama.")),
    ("Teen And Up Audiences", "Teen",
     ("May be inappropriate for readers under 13. Can include some swearing, mild violence, or non-graphic "
      "romantic and sexual references.",
      "Mungkin tidak cocok untuk pembaca di bawah 13 tahun. Bisa berisi umpatan, kekerasan ringan, atau "
      "singgungan romantis dan seksual yang tidak grafis."),
     ("a tense fight with no graphic injuries.", "perkelahian menegangkan tanpa luka yang digambarkan detail.")),
    ("Mature", "Mature",
     ("Adult themes such as sex, violence, or heavy subject matter, described less graphically than Explicit works.",
      "Tema dewasa seperti seks, kekerasan, atau topik berat, tetapi digambarkan tidak segrafis karya Explicit."),
     ("a bloody battle, or a love scene that fades to black.",
      "pertempuran berdarah, atau adegan cinta yang tidak digambarkan sampai tuntas.")),
    ("Explicit", "Explicit",
     ("Graphic content intended for adult readers only, such as explicit sex or very graphic violence.",
      "Konten grafis khusus pembaca dewasa, seperti seks eksplisit atau kekerasan yang sangat grafis."),
     ("an explicitly described sex scene.", "adegan seks yang digambarkan secara eksplisit.")),
]

WARNINGS = [
    ("Graphic Depictions Of Violence", ("Violence is described in a gory, graphic, or detailed way.",
                                        "Kekerasan digambarkan secara sadis, grafis, atau detail.")),
    ("Major Character Death", ("A main character of the story dies.", "Tokoh utama dalam cerita meninggal.")),
    ("Rape/Non-Con", ("The story depicts sexual activity without consent.",
                      "Cerita menggambarkan aktivitas seksual tanpa persetujuan.")),
    ("No Archive Warnings Apply", ("None of the three warnings above apply to the story.",
                                   "Tidak ada satu pun dari tiga warning di atas yang berlaku.")),
]

_CATEGORY = {
    "Emotion": "Emosi", "Tone": "Nada", "Romance": "Romansa", "Relationships": "Hubungan",
    "Setting": "Latar", "Theme": "Tema", "Sensitive content": "Konten sensitif",
}

# (kategori, nama tag, (arti EN, arti ID), contoh tag AO3)
TAGS = [
    ("Emotion", "Angst", ("Emotional pain, sadness, or heartbreak drives the story.",
                          "Rasa sakit emosional, kesedihan, atau patah hati menggerakkan cerita."),
     "Angst, Hurt No Comfort, Angst with a Happy Ending, Heartbreak"),
    ("Emotion", "Fluff", ("Light, sweet, feel-good moments with little conflict.",
                          "Momen ringan, manis, dan menyenangkan dengan sedikit konflik."),
     "Fluff, Tooth-Rotting Fluff, Domestic Fluff, Fluff and Angst"),
    ("Emotion", "Hurt/Comfort", ("One character suffers and another cares for them.",
                                 "Satu tokoh menderita dan tokoh lain merawat atau menghiburnya."),
     "Hurt/Comfort, Emotional Hurt/Comfort, Needs a Hug, Touch-Starved"),
    ("Emotion", "Whump", ("A character is put through suffering, and the story lingers on their pain.",
                          "Seorang tokoh mengalami penderitaan, dan cerita berlama-lama pada rasa sakitnya."),
     "Whump"),
    ("Tone", "Humor", ("The story is meant to be funny.", "Cerita dimaksudkan untuk lucu."),
     "Humor, Humour, Attempt at Humor, Fluff and Humor"),
    ("Romance", "Established Relationship", ("The main couple is already together when the story begins.",
                                             "Pasangan utama sudah bersama sejak awal cerita."),
     "Established Relationship"),
    ("Romance", "Pining", ("A character longs for someone they love, often unsure if it is returned.",
                           "Seorang tokoh merindukan orang yang dicintainya, sering tanpa tahu perasaannya berbalas."),
     "Pining, Mutual Pining, Unrequited Love, Lovesick"),
    ("Relationships", "Family", ("Family bonds are an important theme: parents, children, or siblings.",
                                 "Ikatan keluarga menjadi tema penting: orang tua, anak, atau saudara."),
     "Family, Found Family, Siblings, Parent-Child Relationship"),
    ("Relationships", "Friendship", ("A platonic friendship sits at the heart of the story.",
                                     "Persahabatan platonis menjadi inti cerita."),
     "Friendship, Bonding"),
    ("Setting", "Mythical Creatures", ("Supernatural or mythical beings appear in the story.",
                                       "Makhluk gaib atau makhluk mitos muncul dalam cerita."),
     "Vampire, Werewolf, Mermaid, Fae, Demon, Ghost, Elf, Siren"),
    ("Theme", "Mental Health", ("The story deals with mental health issues or their treatment.",
                                "Cerita membahas masalah kesehatan mental atau penanganannya."),
     "Mental Health Issues, Depression, Anxiety, Trauma, Therapy, PTSD"),
    ("Sensitive content", "Alcohol", ("Drinking, being drunk, hangovers, or alcoholism plays a part.",
                                      "Minum alkohol, mabuk, pengar, atau kecanduan alkohol ikut berperan."),
     "Alcohol, Alcoholism, Drunk, Drunkenness, Hangover"),
    ("Sensitive content", "Blood/Injury", ("Characters bleed or get physically injured.",
                                           "Tokoh berdarah atau mengalami luka fisik."),
     "Blood, Injury, Injured Character, Minor Injuries"),
    ("Sensitive content", "Character Death", ("A character dies, whether on-page or off-screen.",
                                              "Ada tokoh yang meninggal, baik diceritakan langsung maupun tidak."),
     "Character Death, Major Character Death, Off-Screen Death"),
    ("Sensitive content", "Suicide", ("Suicide, suicidal thoughts, or a suicide attempt is mentioned or shown.",
                                      "Bunuh diri, pikiran bunuh diri, atau percobaan bunuh diri disebut atau "
                                      "ditampilkan."),
     "Suicide, Suicidal Thoughts, Suicide Attempt, Implied/Referenced Suicide"),
    ("Sensitive content", "Smut", ("Sexual content. Usually comes with a Mature or Explicit rating.",
                                   "Konten seksual. Biasanya disertai rating Mature atau Explicit."),
     "Smut, NSFW, and tags naming specific sexual acts or kinks"),
]

STEPS = [
    (("Reads the whole story", "Membaca seluruh cerita"),
     ("The story is read in overlapping parts of 200 words. Indonesian text is translated to English with NLLB-200 "
      "first. The title is not analyzed.",
      "Cerita dibaca per bagian 200 kata yang saling tumpang tindih. Teks Indonesia diterjemahkan dulu ke bahasa "
      "Inggris dengan NLLB-200. Judul tidak ikut dianalisis.")),
    (("Scores every label", "Memberi skor setiap label"),
     ("A RoBERTa model reads each part and an LSTM combines them. Every rating, warning, and tag gets a confidence "
      "score from 0% to 100%.",
      "Model RoBERTa membaca setiap bagian, lalu LSTM menggabungkannya. Setiap rating, warning, dan tag mendapat "
      "skor keyakinan dari 0% sampai 100%.")),
    (("Picks the suggestions", "Memilih rekomendasi"),
     ("The rating with the highest score is chosen. A warning or tag is suggested when its score passes a "
      "threshold tuned on validation data, with at most five tags.",
      "Rating dengan skor tertinggi yang dipilih. Warning atau tag direkomendasikan kalau skornya melewati ambang yang "
      "diatur dari data validasi, dengan maksimal lima tag.")),
    (("Combines chapters", "Menggabungkan bab"),
     ("In Workspace, the story uses the highest chapter rating. Warnings and tags keep the chapters they came from.",
      "Di Workspace, cerita memakai rating bab yang tertinggi. Warning dan tag tetap mencatat bab asalnya.")),
]


def _section(title: str, count: str = "", anchor: str = "") -> str:
    # <div>, bukan <h2>: Streamlit mengganti id setiap judul, jadi link lompat tidak menemukan tujuannya
    pill = f'<span class="gl-count">{html.escape(count)}</span>' if count else ""
    return f'<div class="gl-h2" id="{anchor}">{html.escape(title)}{pill}</div>'


def _rating_cards() -> str:
    cards = "".join(
        f'<div class="gl-card">{badge(short, BADGE_TONE[name.lower()])}<p class="gl-desc">{html.escape(tr(*desc))}</p>'
        f'<div class="gl-example">{tr("Example", "Contoh")}: {html.escape(tr(*example))}</div></div>'
        for name, short, desc, example in RATINGS
    )
    return f'<div class="gl-grid">{cards}</div>'


def _warning_card() -> str:
    items = "".join(
        f'<div class="gl-warn"><div class="gl-warn-name">{html.escape(name)}</div>'
        f'<p>{html.escape(tr(*desc))}</p></div>'
        for name, desc in WARNINGS
    )
    note = (f'<div class="gl-note">{icon("info", 16)}<span>' + tr(
        "A story can have more than one warning. <b>No Archive Warnings Apply</b> is only suggested when none of the "
        "other three are found. It does not mean the story has no sensitive content, so check the rating and tags too.",
        "Satu cerita bisa punya lebih dari satu warning. <b>No Archive Warnings Apply</b> hanya disarankan kalau tidak "
        "ada satu pun dari tiga warning lainnya. Artinya bukan berarti cerita bebas konten sensitif, jadi tetap periksa "
        "rating dan tag-nya.") + "</span></div>")
    lead = tr("Warnings flag specific sensitive content, not the overall maturity of a story. Review them separately "
              "from the rating.",
              "Warning menandai konten sensitif tertentu, bukan tingkat kedewasaan cerita secara keseluruhan. Periksa "
              "terpisah dari rating.")
    return (f'<div class="gl-panel">{_section("Archive Warnings", tr("4 warnings", "4 warning"), "gl-warnings")}'
            f'<p class="gl-lead">{lead}</p><div class="gl-warn-grid">{items}</div>{note}</div>')


def _tag_cards(tags: list[tuple[str, str, tuple[str, str], str]]) -> str:
    cards = "".join(
        f'<div class="gl-card"><div class="gl-cat">{html.escape(tr(cat, _CATEGORY[cat]))}</div>'
        f'<div class="gl-name">{html.escape(name)}</div><p class="gl-desc">{html.escape(tr(*desc))}</p>'
        f'<div class="gl-ex-label">{tr("Example AO3 tags", "Contoh tag AO3")}</div><div class="gl-ex">{html.escape(ex)}</div></div>'
        for cat, name, desc, ex in tags
    )
    return f'<div class="gl-grid">{cards}</div>'


def _steps_panel() -> str:
    steps = "".join(
        f'<div class="gl-step"><span class="gl-step-n">{i}</span><div><div class="gl-step-t">{html.escape(tr(*t))}</div>'
        f"<p>{html.escape(tr(*d))}</p></div></div>"
        for i, (t, d) in enumerate(STEPS, start=1)
    )
    intro = tr("Suggestions are a starting point, not a verdict. You know your story best, so always review them "
                "before posting on AO3.",
                "Rekomendasi adalah titik awal, bukan keputusan akhir. Kamu yang paling mengenal ceritamu, jadi selalu periksa "
                "dulu sebelum mengunggah ke AO3.")
    return (f'<div class="gl-how" id="gl-how"><div class="gl-how-left">{icon("sparkles", 22, "#635BFF")}'
            f'<div class="gl-h2">{tr("Behind the suggestions", "Di balik rekomendasi")}</div>'
            f'<p>{intro}</p></div><div class="gl-how-right">{steps}</div></div>')


def render() -> None:
    page_header(tr("A little clarity for every tag.", "Sedikit penjelasan untuk setiap tag."),
                tr("What each piece of metadata suggested by FanMeta means. Ratings and warnings follow the "
                    "definitions used by Archive of Our Own (AO3).",
                    "Arti setiap metadata yang disarankan FanMeta. Rating dan warning mengikuti definisi yang dipakai "
                    "Archive of Our Own (AO3)."),
                kicker=tr("The FanMeta field guide", "Panduan FanMeta"))
    st.markdown(
        '<nav class="gl-jump"><a href="#gl-rating" target="_self">Content Rating</a>'
        '<a href="#gl-warnings" target="_self">Archive Warnings</a>'
        '<a href="#gl-tags" target="_self">Additional Tags</a>'
        f'<a href="#gl-how" target="_self">{tr("Behind the suggestions", "Di balik saran")}</a></nav>',
        unsafe_allow_html=True,
    )

    lead = tr("Every story gets exactly <b>one</b> rating. It tells readers how mature the content is.",
                "Setiap cerita mendapat tepat <b>satu</b> rating. Rating memberi tahu pembaca seberapa dewasa isinya.")
    st.markdown(_section("Content Rating", tr("4 ratings", "4 rating"), "gl-rating")
                + f'<p class="gl-lead">{lead}</p>' + _rating_cards(), unsafe_allow_html=True)

    st.markdown(_warning_card(), unsafe_allow_html=True)

    head, search = st.columns([2, 1], vertical_alignment="bottom")
    with head:
        st.markdown(_section("Additional Tags", tr("16 categories", "16 kategori"), "gl-tags")
                    + '<p class="gl-lead">' + tr(
                        "AO3 authors write thousands of different tags. FanMeta groups them into 16 categories and "
                        "suggests up to five per story.",
                        "Penulis AO3 menulis ribuan tag yang berbeda. FanMeta mengelompokkannya menjadi 16 kategori "
                        "dan menyarankan maksimal lima per cerita.") + "</p>", unsafe_allow_html=True)
    with search:
        query = st.text_input(tr("Search tags", "Cari tag"), placeholder=tr("Search tags or meanings", "Cari tag atau artinya"),
                                key="gl_search", icon=":material/search:", label_visibility="collapsed").strip().lower()
    # pencarian mencocokkan kedua bahasa, jadi "sedih" maupun "sad" sama-sama ketemu
    shown = [t for t in TAGS if not query
             or query in " ".join((t[0], _CATEGORY[t[0]], t[1], *t[2], t[3])).lower()]
    if shown:
        st.markdown(_tag_cards(shown), unsafe_allow_html=True)
    else:
        st.info(tr("No tags match your search.", "Tidak ada tag yang cocok."))

    st.markdown(_steps_panel(), unsafe_allow_html=True)
