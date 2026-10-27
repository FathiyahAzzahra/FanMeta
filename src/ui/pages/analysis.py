"""New narrative analysis view."""
from pathlib import Path

import streamlit as st
from src.services.firestore_history import FirestoreHistory
from src.services.gpu_quota import GpuQuota
from src.core.story_file import StoryFileError, read_story_file
from src.ui import device_choice
from src.core.i18n import num
from src.ui.components import navigate, tr

_LANG_EN = {"Bahasa Indonesia": "Indonesian", "Bahasa Inggris": "English"}


def draft_language_label(value: str) -> str:
    """Pilihan bahasa draf: 'Indonesian'/'English' atau 'Bahasa Indonesia'/'Bahasa Inggris'."""
    return tr(_LANG_EN.get(value, value), value)

# panjang cerita pada data latih (scraping AO3)
TRAIN_MAX_WORDS = 3500


def _uploader_key() -> str:
    # file_uploader tidak bisa dikosongkan lewat session_state, jadi key-nya diganti
    return f"story_file_{st.session_state.get('upload_round', 0)}"


def _clear_draft() -> None:
    for key in ("story_title", "story_text"):
        st.session_state[key] = ""
    st.session_state["upload_round"] = st.session_state.get("upload_round", 0) + 1


def _load_story_file() -> None:
    file = st.session_state.get(_uploader_key())
    if file is None:
        return
    try:
        st.session_state["story_text"] = read_story_file(file.name, file.getvalue())
    except StoryFileError as error:
        st.session_state["upload_error"] = str(error)
        return
    if not st.session_state.get("story_title", "").strip():
        st.session_state["story_title"] = Path(file.name).stem


def _length_note(words: int) -> str:
    # hanya cerita yang terlalu panjang yang diberi peringatan
    if words <= TRAIN_MAX_WORDS:
        return ""
    return '<span class="len-warn">' + tr(
        f"This draft is longer than the stories the model was trained on (up to {num(TRAIN_MAX_WORDS)} words), "
        "so results may be less reliable.",
        f"Draf ini lebih panjang dari cerita yang dipakai melatih model (maksimal {num(TRAIN_MAX_WORDS)} kata), "
        "jadi hasilnya bisa kurang akurat.") + "</span>"


def render(_user: dict[str, str], history_store: FirestoreHistory | None) -> None:
    quota = GpuQuota(history_store.client) if history_store is not None else None
    main, guide = st.columns([2.2, 1], gap="large")

    with main:
        heading = tr("New Narrative Analysis", "Analisis Cerita Baru")
        sub = tr("Provide your fanfiction draft below. Our AI will analyze your plot dynamics, relationships, and "
                    "linguistic style to suggest metadata.",
                    "Masukkan draft fanfiksimu. Kami akan membaca alur, hubungan antartokoh, dan gaya "
                    "bahasanya guna rekomendasi metadata.")
        st.markdown(
            f"""
            <span class="analysis-marker"></span>
            <div class="page-title">{heading}</div>
            <p class="page-sub">{sub}</p>
            """,
            unsafe_allow_html=True,
        )

        c_title, c_lang = st.columns([3, 1], gap="medium")
        with c_title:
            title = st.text_input(tr("Story Title", "Judul Cerita"), placeholder="Of Shadows and Stardust",
                                    key="story_title")
        with c_lang:
            language = st.selectbox(tr("Draft Language", "Bahasa Draf"), ("Bahasa Indonesia", "Bahasa Inggris"),
                                    key="story_language", format_func=draft_language_label)

        st.file_uploader(
            tr("Upload story file (.txt or .docx)", "Unggah file cerita (.txt atau .docx)"), type=["txt", "docx"],
            key=_uploader_key(), on_change=_load_story_file,
            help=tr("The file content replaces the text in the editor below.",
                    "Isi file akan menggantikan teks di kotak cerita di bawah."),
        )
        if error := st.session_state.pop("upload_error", None):
            st.error(error)

        st.markdown(f'<div class="field-label">{tr("Story Text", "Teks Cerita")}</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<span class="editor-marker"></span>', unsafe_allow_html=True)
            story = st.text_area(
                tr("Story Text", "Teks Cerita"),
                height=300,
                placeholder=tr("Among the cosmic dust and the ruins of ancient stars, Kaelan stared at his terminal screen...",
                               "Di antara debu kosmik dan reruntuhan bintang lama, Kaelan menatap layar terminalnya..."),
                key="story_text",
                label_visibility="collapsed",
            )
            words = len(story.split())
            st.markdown(
                f"<div class='editor-footer'><span>{tr('Words', 'Kata')}: <b>{num(words)}</b>&nbsp;&nbsp; "
                f"{tr('Characters', 'Karakter')}: <b>{num(len(story))}</b></span>"
                f"{_length_note(words)}</div>",
                unsafe_allow_html=True,
            )

        device_choice.render("analysis_device", quota)

        _, clear_col, run_col = st.columns([2.4, 1.1, 2.5], gap="small")
        with clear_col:
            st.button(tr("Clear Draft", "Hapus Draf"), key="clear_draft", use_container_width=True,
                      on_click=_clear_draft)
        with run_col:
            if st.button(tr("Analyze Story & Generate Metadata", "Analisis Cerita & Buat Metadata"),
                         key="run_analysis", type="primary", use_container_width=True):
                if not story.strip():
                    st.warning(tr("Please fill in the story text before analyzing.",
                                  "Teks cerita wajib diisi sebelum dianalisis."))
                else:
                    st.session_state["analysis_draft"] = {
                        "title": title.strip(),
                        "story": story.strip(),
                        "language": language,
                        "use_gpu": device_choice.wants_gpu("analysis_device", quota),
                    }
                    st.session_state.pop("proc_job", None)
                    navigate("processing")

    with guide:
        items = [
            ("Content Rating", tr(
                "One of four AO3 ratings: General Audiences, Teen And Up Audiences, Mature, or Explicit.",
                "Salah satu dari empat rating AO3: General Audiences, Teen And Up Audiences, Mature, atau Explicit.")),
            ("Archive Warnings", tr(
                "Graphic Depictions Of Violence, Major Character Death, and Rape/Non-Con. If none apply, FanMeta "
                "suggests No Archive Warnings Apply.",
                "Graphic Depictions Of Violence, Major Character Death, dan Rape/Non-Con. Kalau tidak ada yang "
                "cocok, FanMeta menyarankan No Archive Warnings Apply.")),
            ("Additional Tags", tr(
                "Up to five of 16 common tag categories, such as Angst, Fluff, Hurt/Comfort, and Pining.",
                "Maksimal lima dari 16 kategori tag umum, seperti Angst, Fluff, Hurt/Comfort, dan Pining.")),
            (tr("Indonesian Drafts", "Draf Bahasa Indonesia"), tr(
                "Choose Indonesian and FanMeta translates the story to English with NLLB-200 before analysis, "
                "because the model was trained on English stories. This takes longer.",
                "Pilih Bahasa Indonesia, lalu FanMeta menerjemahkan cerita ke bahasa Inggris dengan NLLB-200 sebelum "
                "dianalisis, karena model dilatih dengan cerita berbahasa Inggris. Prosesnya lebih lama.")),
            (tr("Story Length", "Panjang Cerita"), tr(
                "The model was trained on stories of 2,000–3,500 words. Paste the text or upload a .txt or .docx file.",
                "Model dilatih dengan cerita 2.000–3.500 kata. Tempel teksnya atau unggah file .txt atau .docx.")),
        ]
        body = "".join(f'<div class="qg-item"><h5>{h}</h5><p>{t}</p></div>' for h, t in items)
        intro = tr("FanMeta reads your story and recommends the metadata you fill in when posting a work on Archive "
                   "of Our Own (AO3) or the other Publication Platforms. The title is saved, but only the story text "
                   "is analyzed.",
                   "FanMeta membaca ceritamu dan merekomendasikan metadata yang kamu isi saat mengunggah karya ke "
                   "Archive of Our Own (AO3) atau platform publikasi lainnya. Judul disimpan, tetapi hanya teks "
                   "cerita yang dianalisis.")
        st.markdown(
            f"""
            <div class="quick-guide">
                <div class="qg-head"><span class="qg-icon">▯</span><span>{tr("Writer’s Quick Guide", "Panduan Singkat Penulis")}</span></div>
                <p class="qg-intro">{intro}</p>
                <hr class="qg-divider">
                {body}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(tr("Open metadata glossary →", "Buka glosarium metadata →"), key="qg_glossary"):
            navigate("glossary")
