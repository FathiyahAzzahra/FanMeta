"""User-scoped Firestore analysis history: tabel riwayat + halaman detail."""
import html
import math
from typing import Any

import streamlit as st

from src.services.firestore_history import FirestoreHistory, FirestoreHistoryError
from src.services.gallery_store import MAX_PEN_NAME_CHARS, GalleryError, GalleryStore
from src.ui.pages import gallery as gallery_view
from src.core.i18n import language_label
from src.ui.pages.analysis import draft_language_label
from src.ui.components import (
    GALLERY_ENABLED, format_created_at, format_relative, open_dialog, page_header, rating_badge, tr,
)
from src.ui.pages.results import copy_button, render_result_cards, summary_html
from src.ui.pages.workspace_link import open_story, save_to_workspace_dialog
from src.services.workspace_store import WorkspaceError, WorkspaceStore
_COLS = [3.6, 1.25, 1.45, 1.05, 0.75]
_ALL_SOURCES, _QUICK, _WORKSPACE = "All sources", "Quick Analysis", "Workspace"
PAGE_SIZES = (10, 25, 50)  # pilihan jumlah baris per halaman; yang pertama = bawaan
_ALL_LANGUAGES = "All Languages"
_SOURCE_LABEL = {_ALL_SOURCES: ("All sources", "Semua sumber"), _QUICK: ("Quick Analysis", "Analisis Cepat"),
                 _WORKSPACE: ("Workspace", "Workspace")}


def _source_label(value: str) -> str:
    return tr(*_SOURCE_LABEL[value])


def _language_option(value: str) -> str:
    return tr("All Languages", "Semua Bahasa") if value == _ALL_LANGUAGES else draft_language_label(value)


def is_workspace(item: dict[str, Any]) -> bool:
    return item.get("source") == "workspace" and bool(item.get("work_id"))


def source_html(item: dict[str, Any], title: str | None = None) -> str:
    """Penanda sumber analisis. Analisis lama tanpa field 'source' = Quick Analysis.

    ``title``: judul yang sudah tampil; keterangan "cerita · Chapter n" tidak diulang kalau sudah ada di judul.
    """
    if not is_workspace(item):
        return f'<span class="src-badge src-quick">{_source_label(_QUICK)}</span>'
    work_title = str(item.get("work_title") or "")
    number = item.get("chapter_number", "?")
    stored = f"Chapter {number}"  # judul analisis Workspace selalu disimpan dengan kata "Chapter"
    chapter = tr(stored, f"Bab {number}")
    badge_html = '<span class="src-badge src-ws">Workspace</span>'
    if title and work_title in title:
        # nama cerita sudah ada di judul: cukup tampilkan nomor bab (kalau belum tertulis juga)
        return badge_html if stored in title else f'{badge_html}<span class="src-where">{chapter}</span>'
    return f'{badge_html}<span class="src-where">{html.escape(work_title)} · {chapter}</span>'


def _open_detail(analysis_id: str) -> None:
    st.session_state["history_detail"] = analysis_id


def _close_detail() -> None:
    st.session_state.pop("history_detail", None)


def _delete_body(user: dict[str, str], history_store: FirestoreHistory, analysis_id: str, title: str,
                 item: dict[str, Any] | None = None) -> None:
    note = tr(" If the story is published, it stays in the gallery until you unpublish it there.",
              " Kalau cerita ini dipublikasikan, cerita tetap ada di galeri sampai kamu membatalkan publikasinya."
              ) if GALLERY_ENABLED else ""
    if item and is_workspace(item):
        work = item.get("work_title")
        note += tr(f" This analysis belongs to the Workspace story **{work}**, so it also disappears from that "
                   "story's analysis log. If it is the chapter's latest analysis, the chapter becomes "
                   "\"not analyzed\" again.",
                   f" Analisis ini milik cerita Workspace **{work}**, jadi juga hilang dari log analisis cerita itu. "
                   "Kalau ini analisis terakhir babnya, bab itu kembali berstatus \"belum dianalisis\".")
    st.markdown('<p class="dlg-text">' + tr(
        f"This permanently removes “{html.escape(title)}” from your history. This action can’t be undone.",
        f"Ini menghapus “{html.escape(title)}” dari riwayatmu secara permanen. Tindakan ini tidak bisa dibatalkan."
    ) + "</p>", unsafe_allow_html=True)
    if note.strip():
        st.markdown(note.strip())
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button(tr("Cancel", "Batal"), key="del_cancel"):
            st.rerun()
        if st.button(tr("Delete", "Hapus"), key="del_confirm", type="primary"):
            try:
                history_store.delete_analysis(user["uid"], analysis_id)
                if item and is_workspace(item) and item.get("chapter_id"):
                    WorkspaceStore(history_store.client).unlink_analysis(
                        user["uid"], item["work_id"], item["chapter_id"], analysis_id)
            except (FirestoreHistoryError, WorkspaceError):
                st.error(tr("The analysis could not be deleted. Please try again.",
                            "Riwayat gagal dihapus. Silakan coba lagi."))
                return
            st.session_state["history_toast"] = tr(f'"{title}" was deleted.', f'"{title}" telah dihapus.')
            st.rerun()


def _confirm_delete(*args: Any) -> None:
    open_dialog(tr("Delete this analysis?", "Hapus analisis ini?"), ":material/delete:", _delete_body, *args)


def _set_page(page: int) -> None:
    st.session_state["hist_page"] = page


def _set_page_size() -> None:
    # disalin ke key biasa supaya pilihan tetap diingat setelah membuka halaman detail
    st.session_state["hist_page_size"] = st.session_state["hist_page_size_w"]


def _page_numbers(page: int, pages: int) -> list[int | None]:
    """Nomor halaman yang ditampilkan; None = tanda '…'. Contoh (5 dari 12): 1 … 4 5 6 … 12."""
    if pages <= 7:
        return list(range(1, pages + 1))
    middle = range(max(2, page - 1), min(pages - 1, page + 1) + 1)
    numbers: list[int | None] = [1]
    if middle[0] > 2:
        numbers.append(None)
    numbers += list(middle)
    if middle[-1] < pages - 1:
        numbers.append(None)
    return numbers + [pages]


def _render_pager(page: int, pages: int, start: int, shown: int, total: int, size: int) -> None:
    with st.container(key="ht_footer", horizontal=True, vertical_alignment="center",
                      horizontal_alignment="distribute"):
        shown_range = f"<b>{start + 1}–{start + shown}</b>"
        st.markdown('<div class="ht-count">' + tr(
            f'Showing {shown_range} of <b>{total}</b> analys{"is" if total == 1 else "es"}',
            f"Menampilkan {shown_range} dari <b>{total}</b> analisis") + "</div>",
            unsafe_allow_html=True, width="content")
        with st.container(horizontal=True, vertical_alignment="center", gap="small", width="content"):
            st.markdown(f'<div class="ht-count">{tr("Rows per page", "Baris per halaman")}</div>',
                        unsafe_allow_html=True, width="content")
            st.selectbox(tr("Rows per page", "Baris per halaman"), PAGE_SIZES, index=PAGE_SIZES.index(size), key="hist_page_size_w",
                         label_visibility="collapsed", width=84, on_change=_set_page_size)
            st.button("", key="hist_pg_prev", icon=":material/chevron_left:",
                      help=tr("Previous page", "Halaman sebelumnya"),
                      disabled=page <= 1, on_click=_set_page, args=(page - 1,))
            for n in _page_numbers(page, pages):
                if n is None:
                    st.markdown('<div class="ht-count">…</div>', unsafe_allow_html=True, width="content")
                else:
                    st.button(str(n), key=f"hist_pgc_{n}" if n == page else f"hist_pg_{n}",
                              on_click=_set_page, args=(n,))
            st.button("", key="hist_pg_next", icon=":material/chevron_right:",
                      help=tr("Next page", "Halaman berikutnya"),
                      disabled=page >= pages, on_click=_set_page, args=(page + 1,))


def _date(value: Any) -> str:
    text = format_relative(value)
    return text[:1].upper() + text[1:]


def _render_table(user: dict[str, str], history_store: FirestoreHistory) -> None:
    page_header(tr("Analysis History", "Riwayat Analisis"),
                tr("Browse, search, and recover previously processed metadata reports for your drafts.",
                   "Telusuri, cari, dan buka kembali laporan metadata dari draf-draf yang pernah kamu analisis."))
    try:
        history = history_store.list_history(user["uid"])
    except FirestoreHistoryError:
        st.error(tr("Your analysis history could not be loaded. Please try again.",
                    "Riwayat analisis tidak dapat dimuat. Silakan coba lagi.")); return
    if not history:
        st.info(tr("No analyses yet.", "Belum ada riwayat analisis.")); return

    with st.container(border=True, key="hist_search"):
        search_col, label_col, filter_col, source_col = st.columns([3.4, .7, 1.2, 1.2], vertical_alignment="center")
        with search_col:
            search = st.text_input(tr("Search", "Cari"), label_visibility="collapsed",
                                   placeholder=tr("Search by story title...", "Cari judul cerita..."),
                                   icon=":material/search:")
        with label_col:
            st.markdown(f'<div class="hist-filter-label">{tr("Filter:", "Filter:")}</div>', unsafe_allow_html=True)
        with filter_col:
            language_filter = st.selectbox(tr("Filter Language", "Filter Bahasa"),
                                           (_ALL_LANGUAGES, "Bahasa Indonesia", "Bahasa Inggris"),
                                           format_func=_language_option, label_visibility="collapsed")
        with source_col:
            source_filter = st.selectbox(tr("Filter Source", "Filter Sumber"), (_ALL_SOURCES, _QUICK, _WORKSPACE),
                                         format_func=_source_label, label_visibility="collapsed")

    rows = []
    for item in history:
        title = str(item.get("title") or tr("Untitled Draft", "Draf Tanpa Judul"))
        language = str(item.get("language") or "-")
        if search and search.lower() not in title.lower():
            continue
        if language_filter != _ALL_LANGUAGES and language != language_filter:
            continue
        if source_filter != _ALL_SOURCES and is_workspace(item) != (source_filter == _WORKSPACE):
            continue
        rows.append((item, title, language))

    # pagination: kembali ke halaman 1 setiap kali pencarian, filter, atau jumlah baris berubah
    size = st.session_state.get("hist_page_size", PAGE_SIZES[0])
    size = size if size in PAGE_SIZES else PAGE_SIZES[0]
    signature = (search, language_filter, source_filter, size)
    if st.session_state.get("hist_filter_sig") != signature:
        st.session_state["hist_filter_sig"] = signature
        st.session_state["hist_page"] = 1
    pages = max(1, math.ceil(len(rows) / size))
    page = min(max(1, int(st.session_state.get("hist_page", 1))), pages)  # mis. setelah baris terakhir dihapus
    start = (page - 1) * size

    # tabel: baris judul kolom + satu baris per analisis (garis pemisah & padding diatur di styles.py)
    with st.container(key="ht_table", gap=None):
        with st.container(key="ht_header"):
            for col, name in zip(st.columns(_COLS, vertical_alignment="center"),
                                 (tr("Story title", "Judul cerita"), tr("Draft language", "Bahasa draf"),
                                  tr("Date processed", "Tanggal analisis"), "Rating", tr("Actions", "Aksi"))):
                col.markdown(f'<div class="ht-head">{name}</div>', unsafe_allow_html=True)
        if not rows:
            st.markdown('<div class="ht-empty">' + tr("No analyses match your search.",
                                                      "Tidak ada riwayat yang cocok dengan pencarian.") + "</div>",
                        unsafe_allow_html=True)
        for item, title, language in rows[start:start + size]:
            aid = item["analysis_id"]
            with st.container(key=f"ht_row_{aid}"):
                c_title, c_lang, c_date, c_rating, c_action = st.columns(_COLS, vertical_alignment="center")
                c_title.markdown(f'<div class="ht-title">{html.escape(title)}</div>'
                                 f'<div class="ht-src">{source_html(item, title)}</div>', unsafe_allow_html=True)
                c_lang.markdown(f'<div class="ht-cell">{html.escape(language_label(language))}</div>',
                                unsafe_allow_html=True)
                c_date.markdown(f'<div class="ht-cell" title="{format_created_at(item.get("created_at"))}">'
                                f'{_date(item.get("created_at"))}</div>', unsafe_allow_html=True)
                c_rating.markdown(rating_badge(str(item.get("rating") or "")), unsafe_allow_html=True)
                with c_action:
                    with st.container(horizontal=True, gap="small", vertical_alignment="center"):
                        st.button("", key=f"hist_view_{aid}", icon=":material/visibility:", type="tertiary",
                                  help=tr("View details", "Lihat detail"), on_click=_open_detail, args=(aid,))
                        if st.button("", key=f"hist_del_{aid}", icon=":material/delete:", type="tertiary",
                                     help=tr("Delete", "Hapus")):
                            _confirm_delete(user, history_store, aid, title, item)
        if rows:
            _render_pager(page, pages, start, len(rows[start:start + size]), len(rows), size)


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
    st.button(tr("← Back to History", "← Kembali ke Riwayat"), key="hist_back", on_click=_close_detail)
    try:
        item = history_store.get_analysis(user["uid"], analysis_id)
    except FirestoreHistoryError:
        st.error(tr("The analysis details could not be loaded. Please try again.",
                    "Detail riwayat tidak dapat dimuat. Silakan coba lagi.")); return
    if item is None:
        st.warning(tr("This analysis was not found. It may have been deleted.",
                      "Riwayat ini tidak ditemukan. Mungkin sudah dihapus.")); return

    title = html.escape(str(item.get("title") or tr("Untitled Draft", "Draf Tanpa Judul")))
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
            <p class="page-sub">{tr("Analyzed on", "Dianalisis pada")} <b>{created_at}</b> · {tr("Source draft", "Bahasa draf")}: {html.escape(language_label(language))}
            ({len(story.split())} {tr("words", "kata")})</p>
            """,
            unsafe_allow_html=True,
        )
        render_result_cards(item, story)
        with st.expander(tr("View original story", "Lihat cerita asli")):
            st.text(story or tr("No story saved.", "Tidak ada cerita tersimpan."))

    with side:
        snippet = story[:280] + ("..." if len(story) > 280 else "")
        with st.container(border=True):
            st.markdown(
                f"""
                <span class="summary-marker"></span>
                <div class="sum-title">{tr("Story Preview", "Cuplikan Cerita")}</div>
                <div class="sum-box sum-snippet">"{html.escape(snippet) or '-'}"</div>
                <hr class="sum-line">
                <div class="sum-title">{tr("Metadata Summary", "Ringkasan Metadata")}</div>
                <div class="sum-box">{summary_html(item)}</div>
                <hr class="sum-line">
                """,
                unsafe_allow_html=True,
            )
            copy_button(item)
            if is_workspace(item):
                st.button(tr("Open in Workspace", "Buka di Workspace"), key="res_history", use_container_width=True,
                          on_click=open_story, args=(item["work_id"],))
            else:
                st.button(
                    tr("Run Analysis Again", "Analisis Ulang"), key="res_rerun", use_container_width=True,
                    on_click=_rerun_analysis, args=(item,), disabled=not story,
                )
                if st.button(tr("Save to Workspace", "Simpan ke Workspace"), key="res_ws", use_container_width=True,
                             disabled=not story,
                             help=tr("Turn this analysis into a chapter of a Workspace story.",
                                     "Jadikan analisis ini bab dari sebuah cerita di Workspace.")):
                    save_to_workspace_dialog(user, WorkspaceStore(history_store.client), history_store, item)
            if GALLERY_ENABLED:
                st.markdown('<hr class="sum-line">', unsafe_allow_html=True)
                _render_publish(user, GalleryStore(history_store.client), item)


def render(user: dict[str, str], history_store: FirestoreHistory | None) -> None:
    if history_store is None:
        page_header(tr("Analysis History", "Riwayat Analisis"))
        st.error(tr("Firestore is not configured, so the analysis history is unavailable.",
                    "Firestore belum dikonfigurasi. Riwayat analisis tidak tersedia.")); return
    for key in ("history_toast", "gallery_toast"):
        if toast := st.session_state.pop(key, None):
            st.toast(toast, icon=":material/check_circle:")
    analysis_id = st.session_state.get("history_detail")
    if analysis_id:
        _render_detail(user, history_store, analysis_id)
    else:
        _render_table(user, history_store)
