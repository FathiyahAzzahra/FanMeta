"""Processing state between draft submission and final metadata results."""
import html
import inspect
import re
import threading
from collections.abc import Callable

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

from src.firestore_history import FirestoreHistory, FirestoreHistoryError
from src.predictor import FanMetaPredictor
from src.ui.analysis import draft_language_label
from src.ui.components import navigate, tr


def _panel_html(items: list[tuple[str, str, str]], percent: int) -> str:
    rows = "".join(
        f'<div class="ps ps-{status}"><span class="ps-icon">{"✓" if status == "done" else ""}</span>'
        f'<div><div class="ps-title">{html.escape(title)}</div>'
        f'<div class="ps-desc">{html.escape(desc)}</div></div></div>'
        for status, title, desc in items
    )
    return (
        '<div class="processing-panel">'
        f'<div class="pp-head"><span class="pp-spin"></span><b>{tr("Processing Narrative", "Memproses Cerita")}</b></div>'
        f'<div class="pp-sub">{percent}% {tr("complete", "selesai")}</div>'
        f'<div class="pp-bar"><div style="width:{percent}%"></div></div>'
        '<hr class="pp-line">'
        f"{rows}</div>"
    )


def _start_job(draft: dict, load_predictor: Callable[[], FanMetaPredictor]) -> dict:
    """Jalankan prediksi di thread latar belakang; progres dibaca lewat dict `job`."""
    is_id = draft["language"] == "Bahasa Indonesia"
    # Judul hanya disimpan; yang dianalisis isi cerita saja (sama seperti data latih).
    text = draft.get("story", "")
    job = {"active": 1, "result": None, "error": None, "done": False, "saved": False}

    def work() -> None:
        try:
            predictor = load_predictor()  # pertama kali lambat, berikutnya instan (cache)
            job["active"] = 2 if is_id else 3
            kwargs = {"source_language": "id" if is_id else "en"}
            if "on_stage" in inspect.signature(predictor.predict).parameters:
                def on_stage(name: str) -> None:
                    if name == "translating":
                        job["active"] = 2
                    elif name == "classifying":
                        job["active"] = 3
                kwargs["on_stage"] = on_stage
            job["result"] = predictor.predict(text, **kwargs)
            job["active"] = 4
        except Exception as error:  # noqa: BLE001
            job["error"] = str(error) or "unknown error"
        finally:
            job["done"] = True

    thread = threading.Thread(target=work, daemon=True)
    add_script_run_ctx(thread, get_script_run_ctx())
    thread.start()
    return job


@st.fragment(run_every=0.7)
def _progress(job: dict, steps: list, draft: dict, user: dict, history_store: FirestoreHistory | None) -> None:
    if job["error"]:
        st.error(tr("The analysis could not be run. Please try again.", "Analisis gagal dijalankan. Silakan coba lagi."))
        st.caption(job["error"])
        if st.button(tr("Back to editor", "Kembali ke editor"), key="proc_back"):
            st.session_state.pop("proc_job", None)
            navigate("analysis")
        return

    if job["done"] and job["result"] is not None:
        result = job["result"]
        if not job["saved"]:
            job["saved"] = True
            st.session_state.pop("analysis_id", None)
            if history_store is not None:
                try:
                    # id dipakai halaman hasil untuk tombol "Save to Workspace"
                    st.session_state["analysis_id"] = history_store.save_analysis(
                        firebase_uid=user["uid"], email=user["email"], title=draft.get("title", ""),
                        language=draft["language"], story=draft.get("story", ""),
                        rating=result["rating"], warnings=result["warnings"], tags=result["tags"],
                        rating_probabilities=result.get("rating_probabilities"),
                        warning_probabilities=result.get("warning_probabilities"),
                        tag_probabilities=result.get("tag_probabilities"),
                        segments_english=result.get("segments_english"),
                    )
                except FirestoreHistoryError:
                    st.session_state["history_save_warning"] = True
            else:
                st.session_state["history_save_warning"] = True
        st.session_state["analysis_result"] = result
        st.session_state.pop("proc_job", None)
        navigate("results")
        return

    active = job["active"]
    items = []
    for i, (name, done_desc, todo_desc) in enumerate(steps):
        state = "done" if i < active else "active" if i == active else "pending"
        items.append((state, name, done_desc if state == "done" else todo_desc))
    st.markdown(_panel_html(items, active * 25 + 10), unsafe_allow_html=True)


def render(user: dict[str, str], history_store: FirestoreHistory | None,
           load_predictor: Callable[[], FanMetaPredictor]) -> None:
    draft = st.session_state.get("analysis_draft")
    if not draft:
        navigate("analysis")

    title = draft.get("title", "")
    story = draft.get("story", "")
    is_id = draft["language"] == "Bahasa Indonesia"
    words = len(story.split())
    paragraphs = len([p for p in re.split(r"\n\s*\n", story) if p.strip()])

    steps = [
        (tr("Reading Draft Story Content", "Membaca Isi Draf"),
         tr(f"Loaded {words} words successfully.", f"{words} kata berhasil dimuat."),
         tr("Loading your draft.", "Memuat drafmu.")),
        (tr("Processing Text Structures", "Memproses Struktur Teks"),
         tr(f"Parsed {paragraphs} paragraph(s).", f"{paragraphs} paragraf diproses."),
         tr("Parsing text and loading the AI engine (first run takes longer).",
            "Memecah teks dan memuat mesin AI (proses pertama lebih lama).")),
        (
            tr("Translating Indonesian Phrases", "Menerjemahkan Teks Indonesia") if is_id
            else tr("Translation Check", "Pemeriksaan Terjemahan"),
            tr("Translation complete.", "Terjemahan selesai.") if is_id
            else tr("Draft is already in English.", "Draf sudah berbahasa Inggris."),
            tr("Standardizing terminology into English fandom tropes...",
               "Menerjemahkan istilah ke trope fandom bahasa Inggris...") if is_id
            else tr("Checking draft language.", "Memeriksa bahasa draf."),
        ),
        (tr("Generating Metadata Recommendations", "Membuat Rekomendasi Metadata"),
         tr("Metadata ready.", "Metadata siap."),
         tr("Extracting fandom targets, ratings, and tags.", "Menentukan rating, warning, dan tag.")),
    ]

    job = st.session_state.get("proc_job")
    if job is None:
        job = _start_job(draft, load_predictor)
        st.session_state["proc_job"] = job

    main, status_col = st.columns([2.2, 1], gap="large")
    with main:
        st.markdown(
            f"""
            <span class="analysis-marker"></span><span class="processing-marker"></span>
            <div class="page-title proc-title">{html.escape(title or tr('Untitled Draft', 'Draf Tanpa Judul'))} <span>({tr('Analyzing...', 'Menganalisis...')})</span></div>
            <p class="page-sub">{tr('Draft editor is locked while the semantic engine processes your narrative structure.',
                                     'Editor draf dikunci selama mesin AI memproses ceritamu.')}</p>
            """,
            unsafe_allow_html=True,
        )
        c_title, c_lang = st.columns([3, 1], gap="medium")
        with c_title:
            st.text_input(tr("Story Title", "Judul Cerita"), value=title, disabled=True, key="proc_title")
        with c_lang:
            st.text_input(tr("Draft Language", "Bahasa Draf"), value=draft_language_label(draft["language"]),
                          disabled=True, key="proc_language")
        st.text_area(tr("Story Text", "Teks Cerita"), value=story, height=300, disabled=True, key="proc_story")

    with status_col:
        _progress(job, steps, draft, user, history_store)