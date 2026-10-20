"""Simpan Analisis Cepat ke Workspace.

- Cerita baru      : teks analisis menjadi Bab 1, hasilnya menjadi analisis bab itu.
- Cerita yang ada  : hasil analisis dipasang ke bab yang dipilih; TEKS BAB TIDAK BERUBAH.
                     Kalau teks yang dianalisis berbeda dengan isi bab, bab itu bertanda
                     "Changed" supaya jelas hasilnya berasal dari teks lain.
"""
from datetime import datetime, timezone
from typing import Any

import streamlit as st

from src.firestore_history import FirestoreHistory, FirestoreHistoryError, probs_to_rows
from src.rich_text import text_to_html
from src.workspace_metadata import text_hash
from src.workspace_store import LIMITS, STATUSES, WorkspaceError, WorkspaceStore
from src.ui.components import LANGUAGE_LABEL

_EXISTING, _NEW = "Existing story", "New story"


def open_story(work_id: str) -> None:
    st.session_state.update(page="workspace", ws_view="detail", ws_work=work_id)
    st.session_state.pop("history_detail", None)


def _attach(user: dict[str, str], store: WorkspaceStore, history_store: FirestoreHistory, item: dict[str, Any],
            work_id: str, chapter_id: str) -> None:
    """Pasang hasil analisis ke bab dan tandai dokumen analisisnya sebagai milik bab itu."""
    uid = user["uid"]
    analyzed_html = text_to_html(str(item.get("story") or ""))
    store.set_chapter_analysis(uid, work_id, chapter_id, {
        "analysis_id": item["analysis_id"],
        "rating": item.get("rating"), "warnings": list(item.get("warnings") or []), "tags": list(item.get("tags") or []),
        "tag_probabilities": probs_to_rows(item.get("tag_probabilities") or {}),
        "rating_probabilities": probs_to_rows(item.get("rating_probabilities") or {}),
        "analyzed_at": item.get("created_at") or datetime.now(timezone.utc),
        # sidik jari teks YANG DIANALISIS, bukan isi bab: kalau berbeda, bab tampil "Changed"
        "text_hash": text_hash(analyzed_html), "word_count": len(str(item.get("story") or "").split()),
    })
    work = store.get_work(uid, work_id) or {}
    chapter = next((c for c in store.list_chapters(uid, work_id) if c["chapter_id"] == chapter_id), {})
    history_store.link_to_workspace(uid, item["analysis_id"], {
        "source": "workspace", "work_id": work_id, "work_title": work.get("title", ""), "chapter_id": chapter_id,
        "chapter_number": chapter.get("number"), "chapter_title": str(chapter.get("title") or ""),
    })


def move_to_new_story(user: dict[str, str], store: WorkspaceStore, history_store: FirestoreHistory,
                      item: dict[str, Any], work_id: str) -> str:
    """Teks analisis menjadi bab baru (Bab 1 cerita baru), lalu hasilnya dipasang ke bab itu."""
    chapter_id = store.create_chapter(user["uid"], work_id, text_to_html(str(item.get("story") or "")))
    _attach(user, store, history_store, item, work_id, chapter_id)
    return chapter_id


def attach_to_chapter(user: dict[str, str], store: WorkspaceStore, history_store: FirestoreHistory,
                      item: dict[str, Any], work_id: str, chapter_id: str) -> None:
    _attach(user, store, history_store, item, work_id, chapter_id)


def _chapter_label(c: dict[str, Any]) -> str:
    return f"Ch {c['number']} · {c.get('title') or 'Untitled chapter'}"


@st.dialog("Save to Workspace", icon=":material/create_new_folder:")
def save_to_workspace_dialog(user: dict[str, str], store: WorkspaceStore, history_store: FirestoreHistory,
                             item: dict[str, Any]) -> None:
    language = str(item.get("language") or "Bahasa Inggris")
    try:
        works = [w for w in store.list_works(user["uid"]) if w.get("language") == language]
    except WorkspaceError as error:
        st.error(str(error)); return
    st.markdown('<p class="dlg-text">Keep these results with your story so you can find them again, alongside your '
                "chapters and notes.</p>", unsafe_allow_html=True)
    options = [_EXISTING, _NEW] if works else [_NEW]
    mode = st.segmented_control("Where", options, default=options[0], key="stw_mode",
                                label_visibility="collapsed", width="stretch") or options[0]

    if mode == _NEW:
        title = st.text_input("Story title *", value=str(item.get("title") or "")[:LIMITS["title"]],
                              max_chars=LIMITS["title"])
        fandom = st.text_input("Fandom *", max_chars=LIMITS["fandom"], placeholder="e.g. One Piece")
        status = st.selectbox("Status", STATUSES, index=0)
        st.markdown(f'<p class="dlg-note">The analyzed text becomes Chapter 1. Language: '
                    f"{LANGUAGE_LABEL.get(language, language)} (same as this analysis).</p>", unsafe_allow_html=True)
        target = chapter = None
    else:
        target = st.selectbox("Story", works, format_func=lambda w: f"{w.get('title')}  ·  {w.get('fandom') or 'No fandom'}"
                              f" · {w.get('status')} · {int(w.get('chapter_count') or 0)} chapter(s)")
        try:
            chapters = store.list_chapters(user["uid"], target["work_id"])
        except WorkspaceError as error:
            st.error(str(error)); return
        if not chapters:
            st.info("This story has no chapters yet. Add a chapter first, or choose New story.")
            chapter = None
        else:
            chapter = st.selectbox("Save results to", chapters, index=len(chapters) - 1, format_func=_chapter_label)
        st.markdown('<p class="dlg-note">Updates analysis results only. Your chapter text and private notes won\'t '
                    "change. If the chapter text differs from the analyzed text, the chapter is marked "
                    "<b>Changed</b> so you can re-analyze it.</p>", unsafe_allow_html=True)

    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("Cancel", key="stw_cancel"):
            st.rerun()
        if st.button("Save to Workspace", key="stw_ok", type="primary", disabled=mode == _EXISTING and chapter is None):
            try:
                if mode == _NEW:
                    work_id = store.create_work(user["uid"], {"title": title, "fandom": fandom, "language": language,
                                                              "status": status})
                    move_to_new_story(user, store, history_store, item, work_id)
                else:
                    work_id = target["work_id"]
                    attach_to_chapter(user, store, history_store, item, work_id, chapter["chapter_id"])
            except (WorkspaceError, FirestoreHistoryError) as error:
                st.error(str(error)); return
            st.session_state["ws_toast"] = "Hasil analisis disimpan ke Workspace."
            open_story(work_id)
            st.rerun()
