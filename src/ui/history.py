"""User-scoped Firestore analysis history: tabel riwayat + halaman detail."""
import html
from typing import Any

import streamlit as st

from src.firestore_history import FirestoreHistory, FirestoreHistoryError
from src.gallery_store import MAX_PEN_NAME_CHARS, GalleryError, GalleryStore
from src.ui import gallery as gallery_view
from src.ui.components import GALLERY_ENABLED, LANGUAGE_LABEL as _LANGUAGE_LABEL, format_created_at, rating_badge
from src.ui.results import copy_button, render_result_cards, summary_html
from src.ui.workspace_link import open_story, save_to_workspace_dialog
from src.workspace_store import WorkspaceError, WorkspaceStore
_COLS = [3.0, 1.2, 1.5, 0.9, 1.6]
_ALL_SOURCES, _QUICK, _WORKSPACE = "All sources", "Quick Analysis", "Workspace"


def is_workspace(item: dict[str, Any]) -> bool:
    return item.get("source") == "workspace" and bool(item.get("work_id"))


def source_html(item: dict[str, Any]) -> str:
    """Penanda sumber analisis. Analisis lama tanpa field 'source' = Quick Analysis."""
    if not is_workspace(item):
        return '<span class="src-badge src-quick">Quick Analysis</span>'
    chapter = f"Chapter {item.get('chapter_number', '?')}"
    return (f'<span class="src-badge src-ws">Workspace</span><span class="src-where">'
            f'{html.escape(str(item.get("work_title") or ""))} · {chapter}</span>')


def _open_detail(analysis_id: str) -> None:
    st.session_state["history_detail"] = analysis_id


def _close_detail() -> None:
    st.session_state.pop("history_detail", None)


@st.dialog("Delete this analysis?", icon=":material/delete:")
def _confirm_delete(user: dict[str, str], history_store: FirestoreHistory, analysis_id: str, title: str,
                    item: dict[str, Any] | None = None) -> None:
    note = " If the story is published, it stays in the gallery until you unpublish it there." if GALLERY_ENABLED else ""
    if item and is_workspace(item):
        note += (f" This analysis belongs to the Workspace story **{item.get('work_title')}**, so it also disappears "
                 "from that story's analysis log. If it is the chapter's latest analysis, the chapter becomes "
                 "\"not analyzed\" again.")
    st.markdown(f'<p class="dlg-text">This permanently removes “{html.escape(title)}” from your history. '
                "This action can’t be undone.</p>", unsafe_allow_html=True)
    if note.strip():
        st.markdown(note.strip())
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("Cancel", key="del_cancel"):
            st.rerun()
        if st.button("Delete", key="del_confirm", type="primary"):
            try:
                history_store.delete_analysis(user["uid"], analysis_id)
                if item and is_workspace(item) and item.get("chapter_id"):
                    WorkspaceStore(history_store.client).unlink_analysis(
                        user["uid"], item["work_id"], item["chapter_id"], analysis_id)
            except (FirestoreHistoryError, WorkspaceError):
                st.error("Riwayat gagal dihapus. Silakan coba lagi.")
                return
            st.session_state["history_toast"] = f'"{title}" telah dihapus.'
            st.rerun()


def _render_table(user: dict[str, str], history_store: FirestoreHistory) -> None:
    st.title("Analysis History")
    st.markdown('<p class="page-kicker">Browse, search, and recover previously processed metadata reports for your drafts.</p>', unsafe_allow_html=True)
    try:
        history = history_store.list_history(user["uid"])
    except FirestoreHistoryError:
        st.error("Riwayat analisis tidak dapat dimuat. Silakan coba lagi."); return
    if not history:
        st.info("Belum ada riwayat analisis."); return

    with st.container(border=True):
        st.markdown('<span class="hist-search-marker"></span>', unsafe_allow_html=True)
        search_col, label_col, filter_col, source_col = st.columns([3.4, .7, 1.2, 1.2], vertical_alignment="center")
        with search_col:
            search = st.text_input("Search", label_visibility="collapsed", placeholder="Search by story title...")
        with label_col:
            st.markdown('<div class="hist-filter-label">Filter:</div>', unsafe_allow_html=True)
        with filter_col:
            language_filter = st.selectbox("Filter Language", ("All Languages", "Bahasa Indonesia", "Bahasa Inggris"), label_visibility="collapsed")
        with source_col:
            source_filter = st.selectbox("Filter Source", (_ALL_SOURCES, _QUICK, _WORKSPACE), label_visibility="collapsed")

    rows = []
    for item in history:
        title = str(item.get("title") or "Untitled Draft")
        language = str(item.get("language") or "-")
        if search and search.lower() not in title.lower():
            continue
        if language_filter != "All Languages" and language != language_filter:
            continue
        if source_filter != _ALL_SOURCES and is_workspace(item) != (source_filter == _WORKSPACE):
            continue
        rows.append((item, title, language))

    with st.container(border=True):
        st.markdown('<span class="hist-table-marker"></span>', unsafe_allow_html=True)
        header = st.columns(_COLS, vertical_alignment="center")
        for col, name in zip(header, ("Story Title", "Draft Language", "Date Processed", "Rating", "Actions")):
            col.markdown(f'<div class="ht-head">{name}</div>', unsafe_allow_html=True)
        if not rows:
            st.markdown('<div class="ht-empty">Tidak ada riwayat yang cocok dengan pencarian.</div>', unsafe_allow_html=True)
        for item, title, language in rows:
            c_title, c_lang, c_date, c_rating, c_action = st.columns(_COLS, vertical_alignment="center")
            c_title.markdown(f'<div class="ht-title">{html.escape(title)}</div><div class="ht-src">{source_html(item)}</div>',
                             unsafe_allow_html=True)
            c_lang.markdown(f'<div class="ht-cell">{html.escape(_LANGUAGE_LABEL.get(language, language))}</div>', unsafe_allow_html=True)
            c_date.markdown(f'<div class="ht-cell">{format_created_at(item.get("created_at"))}</div>', unsafe_allow_html=True)
            c_rating.markdown(rating_badge(str(item.get("rating") or "")), unsafe_allow_html=True)
            with c_action:
                with st.container(horizontal=True, gap="small", vertical_alignment="center"):
                    st.button(
                        "View Details", key=f"hist_view_{item['analysis_id']}",
                        on_click=_open_detail, args=(item["analysis_id"],),
                    )
                    if st.button("Delete", key=f"hist_del_{item['analysis_id']}"):
                        _confirm_delete(user, history_store, item["analysis_id"], title, item)


def _rerun_analysis(item: dict[str, Any]) -> None:
    st.session_state["analysis_draft"] = {
        "title": str(item.get("title") or ""),
        "story": str(item.get("story") or ""),
        "language": str(item.get("language") or "Bahasa Inggris"),
    }
    st.session_state.pop("proc_job", None)
    st.session_state.pop("history_detail", None)
    st.session_state["page"] = "processing"


@st.dialog("Publish to gallery?")
def _confirm_publish(user: dict[str, str], gallery: GalleryStore, item: dict[str, Any]) -> None:
    st.write("The **full story** and its FanMeta metadata will be visible to **anyone, without login**. "
             "Logged-in readers can like and comment. You can unpublish at any time.")
    if gallery_view.is_adult(item.get("rating", "")):
        st.caption("This story is rated Mature/Explicit, so readers must confirm they are 18+ before reading.")
    pen_name = st.text_input("Pen name (shown to readers)", value=gallery_view.pen_name_for(user, gallery),
                             max_chars=MAX_PEN_NAME_CHARS)
    agree = st.checkbox("I wrote this story (or have permission) and agree to share it publicly.")
    cancel_col, ok_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", key="pub_cancel", use_container_width=True):
            st.rerun()
    with ok_col:
        if st.button("Publish", key="pub_confirm", type="primary", use_container_width=True, disabled=not agree):
            try:
                gallery.publish(user["uid"], item, pen_name)
            except GalleryError as error:
                st.error(str(error)); return
            gallery_view.refresh_gallery()
            st.session_state["history_toast"] = f'"{item.get("title") or "Untitled Draft"}" sekarang tampil di galeri.'
            st.rerun()


def _render_publish(user: dict[str, str], gallery: GalleryStore, item: dict[str, Any]) -> None:
    work_id = gallery.work_id_for(user["uid"], item["analysis_id"])
    try:
        published = gallery.is_published(user["uid"], item["analysis_id"])
    except GalleryError:
        st.caption("Status galeri tidak dapat dimuat."); return
    if published:
        st.markdown('<div class="pub-status">● Published in the gallery</div>', unsafe_allow_html=True)
        if st.button("View in Gallery", key="res_history", use_container_width=True):
            gallery_view.open_work(work_id)
            st.rerun()
        if st.button("Unpublish", key="work_unpublish", use_container_width=True):
            gallery_view.confirm_unpublish(user, gallery, work_id, str(item.get("title") or "Untitled Draft"))
    elif st.button("Publish to Gallery", key="res_another", use_container_width=True, disabled=not item.get("story")):
        _confirm_publish(user, gallery, item)


def _render_detail(user: dict[str, str], history_store: FirestoreHistory, analysis_id: str) -> None:
    st.button("← Back to History", key="hist_back", on_click=_close_detail)
    try:
        item = history_store.get_analysis(user["uid"], analysis_id)
    except FirestoreHistoryError:
        st.error("Detail riwayat tidak dapat dimuat. Silakan coba lagi."); return
    if item is None:
        st.warning("Riwayat ini tidak ditemukan. Mungkin sudah dihapus."); return

    title = html.escape(str(item.get("title") or "Untitled Draft"))
    language = str(item.get("language") or "-")
    story = str(item.get("story") or "")
    created_at = format_created_at(item.get("created_at"))

    main, side = st.columns([2.2, 1], gap="large")
    with main:
        st.markdown(
            f"""
            <span class="results-marker"></span>
            <div class="ht-src">{source_html(item)}</div>
            <div class="page-title">{title}</div>
            <p class="page-sub">Analyzed on <b>{created_at}</b> · Source Draft: {html.escape(_LANGUAGE_LABEL.get(language, language))}
            ({len(story.split())} words)</p>
            """,
            unsafe_allow_html=True,
        )
        render_result_cards(item, story)
        with st.expander("View original story"):
            st.text(story or "Tidak ada cerita tersimpan.")

    with side:
        snippet = story[:280] + ("..." if len(story) > 280 else "")
        with st.container(border=True):
            st.markdown(
                f"""
                <span class="summary-marker"></span>
                <div class="sum-title">Story Preview</div>
                <div class="sum-box sum-snippet">"{html.escape(snippet) or '-'}"</div>
                <hr class="sum-line">
                <div class="sum-title">Metadata Summary</div>
                <div class="sum-box">{summary_html(item)}</div>
                <hr class="sum-line">
                """,
                unsafe_allow_html=True,
            )
            copy_button(item)
            if is_workspace(item):
                st.button("Open in Workspace", key="res_history", use_container_width=True,
                          on_click=open_story, args=(item["work_id"],))
            else:
                st.button(
                    "Run Analysis Again", key="res_rerun", use_container_width=True,
                    on_click=_rerun_analysis, args=(item,), disabled=not story,
                )
                if st.button("Save to Workspace", key="res_ws", use_container_width=True, disabled=not story,
                             help="Turn this analysis into a chapter of a Workspace story."):
                    save_to_workspace_dialog(user, WorkspaceStore(history_store.client), history_store, item)
            if GALLERY_ENABLED:
                st.markdown('<hr class="sum-line">', unsafe_allow_html=True)
                _render_publish(user, GalleryStore(history_store.client), item)


def render(user: dict[str, str], history_store: FirestoreHistory | None) -> None:
    if history_store is None:
        st.title("Analysis History")
        st.error("Firestore belum dikonfigurasi. Riwayat analisis tidak tersedia."); return
    for key in ("history_toast", "gallery_toast"):
        if toast := st.session_state.pop(key, None):
            st.toast(toast, icon=":material/check_circle:")
    analysis_id = st.session_state.get("history_detail")
    if analysis_id:
        _render_detail(user, history_store, analysis_id)
    else:
        _render_table(user, history_store)
