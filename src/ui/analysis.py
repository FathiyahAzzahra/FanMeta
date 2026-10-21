"""New narrative analysis view."""
from pathlib import Path

import streamlit as st
from src.firestore_history import FirestoreHistory
from src.story_file import StoryFileError, read_story_file
from src.ui.components import navigate

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
    return (f'<span class="len-warn">This draft is longer than the stories the model was trained on '
            f"(up to {TRAIN_MAX_WORDS:,} words), so results may be less reliable.</span>")


def render(_user: dict[str, str], _history_store: FirestoreHistory | None) -> None:
    main, guide = st.columns([2.2, 1], gap="large")

    with main:
        st.markdown(
            """
            <span class="analysis-marker"></span>
            <div class="page-title">New Narrative Analysis</div>
            <p class="page-sub">Provide your fanfiction draft below. Our AI will analyze your plot dynamics,
            relationships, and linguistic style to suggest tags.</p>
            """,
            unsafe_allow_html=True,
        )

        c_title, c_lang = st.columns([3, 1], gap="medium")
        with c_title:
            title = st.text_input("Story Title", placeholder="Of Shadows and Stardust", key="story_title")
        with c_lang:
            language = st.selectbox("Draft Language", ("Bahasa Indonesia", "Bahasa Inggris"), key="story_language")

        st.file_uploader(
            "Upload story file (.txt or .docx)", type=["txt", "docx"],
            key=_uploader_key(), on_change=_load_story_file,
            help="The file content replaces the text in the editor below.",
        )
        if error := st.session_state.pop("upload_error", None):
            st.error(error)

        st.markdown('<div class="field-label">Story Text</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<span class="editor-marker"></span>', unsafe_allow_html=True)
            story = st.text_area(
                "Story Text",
                height=300,
                placeholder="Di antara debu kosmik dan reruntuhan bintang lama, Kaelan menatap layar terminalnya...",
                key="story_text",
                label_visibility="collapsed",
            )
            words = len(story.split())
            st.markdown(
                f"<div class='editor-footer'><span>Words: <b>{words:,}</b>&nbsp;&nbsp; Characters: <b>{len(story):,}</b></span>"
                f"{_length_note(words)}</div>",
                unsafe_allow_html=True,
            )

        _, clear_col, run_col = st.columns([2.4, 1.1, 2.5], gap="small")
        with clear_col:
            st.button("Clear Draft", key="clear_draft", use_container_width=True, on_click=_clear_draft)
        with run_col:
            if st.button("Analyze Story & Generate Metadata", key="run_analysis", type="primary", use_container_width=True):
                if not story.strip():
                    st.warning("Story Text wajib diisi sebelum dianalisis.")
                else:
                    st.session_state["analysis_draft"] = {
                        "title": title.strip(),
                        "story": story.strip(),
                        "language": language,
                    }
                    st.session_state.pop("proc_job", None)
                    navigate("processing")

    with guide:
        st.markdown(
            """
            <div class="quick-guide">
                <div class="qg-head"><span class="qg-icon">▯</span><span>Writer’s Quick Guide</span></div>
                <p class="qg-intro">FanMeta reads your story and recommends the metadata you fill in when
                posting a work on Archive of Our Own (AO3) or the other Publication Platforms. The title is saved, but only the story text is analyzed.</p>
                <hr class="qg-divider">
                <div class="qg-item"><h5>Content Rating</h5>
                    <p>One of four AO3 ratings: General Audiences, Teen And Up Audiences, Mature, or Explicit.</p></div>
                <div class="qg-item"><h5>Archive Warnings</h5>
                    <p>Graphic Depictions Of Violence, Major Character Death, and Rape/Non-Con.
                    If none apply, FanMeta suggests No Archive Warnings Apply.</p></div>
                <div class="qg-item"><h5>Additional Tags</h5>
                    <p>Up to five of 16 common tag categories, such as Angst, Fluff, Hurt/Comfort, and Pining.</p></div>
                <div class="qg-item"><h5>Indonesian Drafts</h5>
                    <p>Choose Bahasa Indonesia and FanMeta translates the story to English with NLLB-200 before
                    analysis, because the model was trained on English stories. This takes longer.</p></div>
                <div class="qg-item"><h5>Story Length</h5>
                    <p>The model was trained on stories of 2,000–3,500 words. Paste the text or upload a
                    .txt or .docx file.</p></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Open metadata glossary →", key="qg_glossary"):
            navigate("glossary")