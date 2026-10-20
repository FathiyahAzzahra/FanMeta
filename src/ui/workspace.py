"""Workspace: arsip & ruang kerja pribadi penulis (daftar cerita, form, detail cerita)."""
import html
from datetime import datetime, timezone
from typing import Any

import streamlit as st

from src.rich_text import count_words, text_to_html
from src.story_file import StoryFileError, read_story_file
from src.workspace_store import LANGUAGES, LIMITS, STATUSES, WorkspaceError, WorkspaceStore
from src.ui.analysis import TRAIN_MAX_WORDS
from src.ui.components import (
    LANGUAGE_LABEL, badge, breadcrumb, danger_box, format_created_at, format_relative, icon, icon_box, navigate_cb, page_header,
    rating_badge,
)
from src.ui.editor import chapter_editor, pending_value, saved_value, set_editor_value
from src.ui import workspace_analysis as wa
from src.ui import workspace_log as wl
from src.ui.results import render_result_cards
from src.workspace_metadata import chapter_state

_ALL = "All statuses"
_SORTS = ("Recently updated", "Title A-Z", "Most words")
_LANGUAGE_OPTION = {"Bahasa Indonesia": "Indonesian — Bahasa Indonesia", "Bahasa Inggris": "English — Bahasa Inggris"}


def _go(view: str, work_id: str | None = None) -> None:
    st.session_state["ws_view"] = view
    if work_id is not None:
        st.session_state["ws_work"] = work_id


def status_badge(status: str) -> str:
    return badge(str(status or "-"))


def _rating_or_empty(work: dict[str, Any]) -> str:
    return rating_badge(work["rating"]) if work.get("rating") else badge("Not analyzed")


def _to_list() -> None:
    _go("list")
    st.session_state.pop("ws_work", None)


def _chapters_label(n: int) -> str:
    return f"{n} chapter" + ("" if n == 1 else "s")


# ---------------------------------------------------------------- daftar cerita
def _analyzed_today(history_store: Any, uid: str) -> int:
    if history_store is None:
        return 0
    try:
        items = history_store.list_history(uid)
    except Exception:  # noqa: BLE001 - statistik saja, jangan gagalkan halaman
        return 0
    return sum(1 for h in items if h.get("source") == "workspace" and format_relative(h.get("created_at")).startswith("today"))


def _render_list(user: dict[str, str], store: WorkspaceStore, ctx: dict[str, Any]) -> None:
    head, action = st.columns([4, 1], vertical_alignment="center")
    with head:
        page_header("Every story has a home.", "Keep your chapters close and your metadata in sync.",
                    kicker="Your writing space")
    with action:
        with st.container(horizontal=True, horizontal_alignment="right"):
            st.button("+ New Story", key="ws_new", type="primary", on_click=_go, args=("new",))

    try:
        works = store.list_works(user["uid"])
    except WorkspaceError:
        st.error("Daftar cerita tidak dapat dimuat. Silakan coba lagi."); return

    stats = [
        ("library", f"{len(works):,}", "Stories in your library"),
        ("feather", f"{sum(int(w.get('word_count') or 0) for w in works):,}", "Words in your library"),
        ("sparkles", f"{_analyzed_today(ctx.get('history_store'), user['uid']):,}", "Chapters analyzed today"),
    ]
    st.markdown('<div class="ws-stats">' + "".join(
        f'<div class="ws-stat">{icon_box(i)}<div><div class="ws-stat-n">{n}</div><div class="ws-stat-l">{lbl}</div></div></div>'
        for i, n, lbl in stats) + "</div>", unsafe_allow_html=True)

    if not works:
        st.markdown(f'<div class="ws-empty">{icon_box("book", 22)}<b>No stories yet</b>'
                    "<span>Create your first story project to start writing chapter by chapter.</span></div>",
                    unsafe_allow_html=True)
        return

    c_search, c_status, c_gap, c_count, c_sort = st.columns([3.1, 1.2, 1.2, .7, 1.4], vertical_alignment="center")
    with c_search:
        search = st.text_input("Search", label_visibility="collapsed", key="ws_search",
                               placeholder="Search by title or fandom", icon=":material/search:")
    with c_status:
        status = st.selectbox("Status", (_ALL, *STATUSES), key="ws_status", label_visibility="collapsed")
    query = search.strip().lower()
    shown = [
        w for w in works
        if (not query or query in str(w.get("title", "")).lower() or query in str(w.get("fandom", "")).lower())
        and (status == _ALL or w.get("status") == status)
    ]
    with c_count:
        st.markdown(f'<div class="ws-count">{len(shown)} stor{"y" if len(shown) == 1 else "ies"}</div>',
                    unsafe_allow_html=True)
    with c_sort:
        sort = st.selectbox("Sort", _SORTS, key="ws_sort", label_visibility="collapsed")
    if sort == "Title A-Z":
        shown.sort(key=lambda w: str(w.get("title", "")).lower())
    elif sort == "Most words":
        shown.sort(key=lambda w: int(w.get("word_count") or 0), reverse=True)

    if not shown:
        st.info("Tidak ada cerita yang cocok dengan pencarian.")
        return
    for start in range(0, len(shown), 3):
        cols = st.columns(3, gap="medium")
        for col, work in zip(cols, shown[start:start + 3]):
            with col, st.container(border=True):
                n = int(work.get("chapter_count") or 0)
                summary = str(work.get("summary") or "").strip() or "No summary yet."
                st.markdown(
                    f"""
                    <span class="ws-card-marker"></span>
                    <div class="wc-top">{status_badge(work.get("status"))}{_rating_or_empty(work)}</div>
                    <div class="wc-title">{html.escape(str(work.get("title") or "Untitled"))}</div>
                    <div class="wc-fandom">{html.escape(str(work.get("fandom") or "No fandom"))}</div>
                    <p class="wc-summary">{html.escape(summary)}</p>
                    <div class="wc-meta">{icon("files", 15)}<span>{_chapters_label(n)}</span>
                    <span>{int(work.get("word_count") or 0):,} words</span></div>
                    <hr class="wc-line">
                    """,
                    unsafe_allow_html=True,
                )
                foot_l, foot_r = st.columns([1.6, 1], vertical_alignment="center")
                with foot_l:
                    st.markdown(f'<div class="wc-edited">Edited {format_relative(work.get("updated_at"))}</div>',
                                unsafe_allow_html=True)
                with foot_r:
                    with st.container(horizontal=True, horizontal_alignment="right"):
                        st.button("Open", key=f"ws_open_{work['work_id']}", icon=":material/arrow_forward:",
                                  on_click=_go, args=("detail", work["work_id"]))
    st.markdown(f'<div class="ws-private">{icon("lock", 15)}Your workspace is private. '
                "Only you can see your stories and notes.</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- form cerita
def _render_form(user: dict[str, str], store: WorkspaceStore, work: dict[str, Any] | None) -> None:
    editing = work is not None
    work = work or {}
    back_view = "detail" if editing else "list"
    if editing:
        breadcrumb([("Workspace", _to_list), (str(work.get("title") or "Story"), lambda: _go("detail")), ("Edit", None)],
                   key="form")
        page_header("Edit Story", "Update the details of your story. Your chapters stay as they are.")
    else:
        breadcrumb([("Workspace", _to_list), ("New Story", None)], key="form")
        page_header("New Story", "Set the scene. Give your story a home before adding your chapters.")

    main, side = st.columns([2.15, 1], gap="medium")
    with main, st.form("ws_work_form", border=False):
        with st.container(border=True):
            st.markdown('<span class="form-card-marker"></span><div class="card-title">The essentials'
                        '<small>* Required fields</small></div>', unsafe_allow_html=True)
            title = st.text_input("Title *", value=work.get("title", ""), max_chars=LIMITS["title"],
                                  placeholder="e.g. Salt and Thunder")
            fandom = st.text_input("Fandom *", value=work.get("fandom", ""), max_chars=LIMITS["fandom"],
                                   placeholder="e.g. One Piece")
            st.markdown('<p class="field-help">Use the fandom name readers will recognize on AO3.</p>',
                        unsafe_allow_html=True)
            c_lang, c_status = st.columns([2.3, 1])
            with c_lang:
                language = st.selectbox("Language *", LANGUAGES, format_func=_LANGUAGE_OPTION.get,
                                        index=LANGUAGES.index(work["language"]) if work.get("language") in LANGUAGES else 0)
            with c_status:
                status = st.selectbox("Status", STATUSES,
                                      index=STATUSES.index(work["status"]) if work.get("status") in STATUSES else 1)
        with st.container(border=True):
            st.markdown('<span class="form-card-marker"></span><div class="card-title">The people &amp; the premise</div>',
                        unsafe_allow_html=True)
            characters = st.multiselect("Characters", options=work.get("characters", []),
                                        default=work.get("characters", []), accept_new_options=True,
                                        placeholder="Add character...")
            relationships = st.multiselect("Relationships", options=work.get("relationships", []),
                                           default=work.get("relationships", []), accept_new_options=True,
                                           placeholder="Add relationship...")
            st.markdown('<p class="field-help">Use “&amp;” for platonic relationships and “/” for romantic pairings.</p>',
                        unsafe_allow_html=True)
            summary = st.text_area("Summary", value=work.get("summary", ""), max_chars=LIMITS["summary"], height=110)
            st.markdown('<p class="field-help">A short introduction to your story. You can change this anytime.</p>',
                        unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f'<span class="form-card-marker"></span><div class="card-title start">{icon("lock", 17)} Private notes</div>',
                        unsafe_allow_html=True)
            notes = st.text_area("Notes for yourself", value=work.get("notes", ""), max_chars=LIMITS["notes"], height=90)
            st.markdown('<p class="field-help">Just for you. Notes are never included in metadata analysis.</p>',
                        unsafe_allow_html=True)
        foot_l, foot_r = st.columns([1.5, 1], vertical_alignment="center")
        with foot_l:
            st.markdown('<div class="form-foot-note">Your story is private by default.</div>', unsafe_allow_html=True)
        with foot_r:
            with st.container(horizontal=True, horizontal_alignment="right"):
                cancelled = st.form_submit_button("Cancel", key="ws_form_cancel")
                submitted = st.form_submit_button("Save Changes" if editing else "Create Story", type="primary",
                                                  icon=None if editing else ":material/arrow_forward:")
    with side:
        steps = "".join(f'<li><span>{i}</span>{t}</li>' for i, t in enumerate(
            ("Create your story", "Write or paste your chapters", "Analyze and review your metadata"), start=1))
        st.markdown(
            f"""
            <div class="side-card">{icon_box("feather", 22)}
              <div class="side-title">A home for your next chapter</div>
              <p>Start with the basics. Your story grows from here.</p>
              <hr><ol class="side-steps">{steps}</ol>
            </div>
            <div class="side-note"><b>No need to choose a rating yet.</b>
              <p>FanMeta suggests a rating, warnings, and tags after reading your chapters. Your story details help
              you stay organized.</p></div>
            """,
            unsafe_allow_html=True,
        )

    if cancelled:
        _go(back_view)
        st.rerun()
    if submitted:
        data = dict(title=title, fandom=fandom, language=language, status=status, characters=characters,
                    relationships=relationships, summary=summary, notes=notes)
        try:
            if editing:
                store.update_work(user["uid"], work["work_id"], data)
                work_id = work["work_id"]
            else:
                work_id = store.create_work(user["uid"], data)
        except WorkspaceError as error:
            st.error(str(error)); return
        st.session_state["ws_toast"] = "Perubahan cerita tersimpan." if editing else "Cerita baru dibuat."
        _go("detail", work_id)
        st.rerun()


# ---------------------------------------------------------------- detail cerita
@st.dialog("Delete this story?", icon=":material/delete:")
def _confirm_delete(user: dict[str, str], store: WorkspaceStore, work: dict[str, Any]) -> None:
    n = int(work.get("chapter_count") or 0)
    title = str(work.get("title") or "Untitled")
    st.markdown(f'<p class="dlg-text">This permanently deletes “{html.escape(title)}” and everything saved with it. '
                "This action can’t be undone.</p>"
                + danger_box(title, [f"{_chapters_label(n)} · {int(work.get('word_count') or 0):,} words",
                                     "Includes all analysis results, the analysis log, and private notes."]),
                unsafe_allow_html=True)
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("Cancel", key="wsdel_cancel"):
            st.rerun()
        if st.button("Delete story", key="wsdel_confirm", type="primary"):
            try:
                store.delete_work(user["uid"], work["work_id"])
            except WorkspaceError as error:
                st.error(str(error)); return
            st.session_state["ws_toast"] = f'"{work.get("title")}" telah dihapus.'
            _go("list")
            st.session_state.pop("ws_work", None)
            st.rerun()


def _chips(items: list[str]) -> str:
    if not items:
        return '<span class="ws-muted">-</span>'
    return "".join(f'<span class="chip">{html.escape(i)}</span>' for i in items)


def _job_running(work_id: str) -> bool:
    job = st.session_state.get("ws_job")
    return bool(job and job["work_id"] == work_id and not job["done"])


def _start_analysis(user: dict[str, str], store: WorkspaceStore, work: dict[str, Any],
                    chapters: list[dict[str, Any]], ctx: dict[str, Any]) -> None:
    if not chapters or _job_running(work["work_id"]):
        return
    if ctx.get("history_store") is None or ctx.get("load_predictor") is None:
        st.session_state["ws_error"] = "Riwayat (Firestore) tidak tersedia, jadi hasil analisis tidak bisa disimpan."
        return
    st.session_state["ws_job"] = wa.start_job(user, work, chapters, ctx["load_predictor"], ctx["history_store"], store)
    _go("analyzing")


def _open_result(analysis_id: str, chapter_id: str) -> None:
    st.session_state["ws_result"] = {"analysis_id": analysis_id, "chapter_id": chapter_id}
    _go("chapter_result")


def _render_detail(user: dict[str, str], store: WorkspaceStore, work: dict[str, Any], ctx: dict[str, Any]) -> None:
    title = str(work.get("title") or "Untitled")
    breadcrumb([("Workspace", _to_list), (title, None)], key="detail")
    language = str(work.get("language") or "")
    head, actions = st.columns([3, 1.2], vertical_alignment="center")
    with head:
        st.markdown(
            f'<div class="sd-head"><h1 class="pg-h1">{html.escape(title)}</h1>'
            f'{status_badge(work.get("status"))}{_rating_or_empty(work) if work.get("rating") else ""}</div>',
            unsafe_allow_html=True,
        )
    with actions:
        with st.container(horizontal=True, horizontal_alignment="right"):
            st.button("Edit", key="ws_edit", icon=":material/edit:", on_click=_go, args=("edit",))
            if st.button("Delete", key="ws_delete", icon=":material/delete:"):
                _confirm_delete(user, store, work)
    n = int(work.get("chapter_count") or 0)
    st.markdown(
        f'<p class="sd-sub"><span class="sd-fandom">{html.escape(str(work.get("fandom") or "No fandom"))}</span>'
        f'{html.escape(LANGUAGE_LABEL.get(language, language))} · {_chapters_label(n)} · '
        f'{int(work.get("word_count") or 0):,} words · Updated {format_relative(work.get("updated_at"))}</p>',
        unsafe_allow_html=True,
    )

    try:
        chapters = store.list_chapters(user["uid"], work["work_id"])
    except WorkspaceError:
        st.error("Daftar bab tidak dapat dimuat."); return
    running = _job_running(work["work_id"])
    if running:
        with st.container(horizontal=True, vertical_alignment="center"):
            st.info("Analysis is running in the background. Results are saved automatically.")
            st.button("View progress", key="wsa_view", on_click=_go, args=("analyzing",))

    main, side = st.columns([2.6, 1], gap="medium")
    with main:
        if not running:
            wa.render_story_metadata(work, chapters, on_analyze=lambda: _start_analysis(
                user, store, work, wa.needs_analysis(chapters), ctx))
        _render_chapter_list(user, store, work, chapters, ctx, running)
    with side:
        summary = str(work.get("summary") or "").strip()
        rels = work.get("relationships") or []
        st.markdown(
            f"""
            <div class="side-card"><div class="side-title">Summary</div>
              <p class="side-text">{html.escape(summary) if summary else '<span class="ws-muted">No summary yet.</span>'}</p></div>
            <div class="side-card"><div class="side-title">Characters</div>
              <div class="chips">{_chips(work.get("characters") or [])}</div><hr>
              <div class="side-label">Relationships</div>
              <div class="side-lines">{"".join(f"<div>{html.escape(r)}</div>" for r in rels) or '<span class="ws-muted">-</span>'}</div></div>
            <div class="side-card"><div class="side-title">{icon("lock", 17)} Private notes</div>
              <p class="side-text">{html.escape(str(work.get("notes") or "")) or '<span class="ws-muted">No notes yet.</span>'}</p>
              <div class="side-foot">Only visible to you · Not analyzed</div></div>
            """,
            unsafe_allow_html=True,
        )
        st.button("Need a hand? Explore the glossary →", key="ws_glossary", type="tertiary",
                  icon=":material/menu_book:", on_click=navigate_cb, args=("glossary",))
    wl.render_log(user["uid"], work["work_id"], chapters, ctx.get("history_store"))


# ---------------------------------------------------------------- bab
def _new_chapter(user: dict[str, str], store: WorkspaceStore, work_id: str) -> None:
    try:
        chapter_id = store.create_chapter(user["uid"], work_id)
    except WorkspaceError as error:
        st.session_state["ws_error"] = str(error); return
    st.session_state["ws_chapter"] = chapter_id
    _go("chapter")


def _open_chapter(chapter_id: str) -> None:
    st.session_state["ws_chapter"] = chapter_id
    _go("chapter")


def _move_chapter(user: dict[str, str], store: WorkspaceStore, work_id: str, chapter_id: str, step: int) -> None:
    try:
        store.move_chapter(user["uid"], work_id, chapter_id, step)
    except WorkspaceError as error:
        st.session_state["ws_error"] = str(error)


def chapter_label(chapter: dict[str, Any]) -> str:
    title = str(chapter.get("title") or "").strip()
    return f"Chapter {chapter['number']}" + (f": {title}" if title else "")


@st.dialog("Delete this chapter?", icon=":material/delete:")
def _confirm_delete_chapter(user: dict[str, str], store: WorkspaceStore, work_id: str, chapter: dict[str, Any]) -> None:
    st.markdown('<p class="dlg-text">This permanently deletes the chapter text. This action can’t be undone.</p>'
                + danger_box(chapter_label(chapter), [f"{int(chapter.get('word_count') or 0):,} words",
                                                      "Its past analyses stay in History and the Analysis Log."],
                             "files"),
                unsafe_allow_html=True)
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("Cancel", key="chdel_cancel"):
            st.rerun()
        if st.button("Delete chapter", key="chdel_confirm", type="primary"):
            try:
                store.delete_chapter(user["uid"], work_id, chapter["chapter_id"])
            except WorkspaceError as error:
                st.error(str(error)); return
            st.session_state["ws_toast"] = f"{chapter_label(chapter)} telah dihapus."
            st.rerun()


def _render_chapter_list(user: dict[str, str], store: WorkspaceStore, work: dict[str, Any],
                         chapters: list[dict[str, Any]], ctx: dict[str, Any], running: bool) -> None:
    work_id = work["work_id"]
    with st.container(border=True):
        head, action = st.columns([3, 1], vertical_alignment="center")
        with head:
            st.markdown(f'<span class="ws-section-marker"></span><div class="card-title">Chapters '
                        f'<span class="count-pill">{len(chapters)}</span></div>', unsafe_allow_html=True)
        with action:
            with st.container(horizontal=True, horizontal_alignment="right"):
                st.button("+ Add chapter", key="ws_ch_new", on_click=_new_chapter, args=(user, store, work_id))
        if not chapters:
            st.markdown('<p class="ws-muted">No chapters yet. Click + Add chapter to start writing.</p>',
                        unsafe_allow_html=True)
        for i, chapter in enumerate(chapters):
            cid = chapter["chapter_id"]
            state = chapter_state(chapter)
            analysis = chapter.get("analysis") or {}
            badges = (rating_badge(analysis["rating"]) if analysis.get("rating") else "") + wa.state_badge(state)
            title = str(chapter.get("title") or "").strip() or "Untitled chapter"
            st.markdown(
                f'<div class="ch-row{" ch-first" if i == 0 else ""}"><span class="ch-num">{chapter["number"]:02d}</span>'
                f'<div class="ch-body"><div class="ch-title">{html.escape(title)}</div>'
                f'<div class="ch-meta">{int(chapter.get("word_count") or 0):,} words · '
                f'Saved {format_relative(chapter.get("updated_at"))}</div></div>'
                f'<div class="ch-badges">{badges}</div></div>',
                unsafe_allow_html=True,
            )
            with st.container(horizontal=True, gap="small"):
                st.markdown('<span class="ch-actions-marker"></span>', unsafe_allow_html=True)
                st.button("Write", key=f"ws_ch_open_{cid}", icon=":material/edit:", on_click=_open_chapter, args=(cid,))
                st.button("Analyze", key=f"ws_ch_an_{cid}", icon=":material/auto_awesome:",
                          disabled=state == "empty" or running,
                          help="This chapter is empty." if state == "empty" else None,
                          on_click=_start_analysis, args=(user, store, work, [chapter], ctx))
                st.button("Results", key=f"ws_ch_res_{cid}", icon=":material/monitoring:",
                          disabled=not analysis.get("analysis_id"),
                          on_click=_open_result, args=(analysis.get("analysis_id"), cid))
                st.button("Up", key=f"ws_ch_up_{cid}", icon=":material/arrow_upward:", disabled=i == 0,
                          on_click=_move_chapter, args=(user, store, work_id, cid, -1))
                st.button("Down", key=f"ws_ch_down_{cid}", icon=":material/arrow_downward:",
                          disabled=i == len(chapters) - 1, on_click=_move_chapter, args=(user, store, work_id, cid, 1))
                if st.button("Delete", key=f"ws_ch_del_{cid}", icon=":material/delete:", type="tertiary"):
                    _confirm_delete_chapter(user, store, work_id, chapter)
        if len(chapters) > 1:
            st.markdown('<p class="ch-note">Use Up / Down to reorder chapters. Chapter references update with their '
                        "new position.</p>", unsafe_allow_html=True)


def _save_title(user: dict[str, str], store: WorkspaceStore, work_id: str, chapter_id: str) -> None:
    try:
        store.update_chapter(user["uid"], work_id, chapter_id, title=st.session_state[f"ch_title_{chapter_id}"])
    except WorkspaceError as error:
        st.session_state["ws_error"] = str(error)


def _saved_status(value: Any) -> dict[str, str]:
    return {"kind": "saved", "text": "Saved", "when": f"Last saved {format_relative(value)}"}


def _import_file(user: dict[str, str], store: WorkspaceStore, work_id: str, chapter_id: str, key: str) -> None:
    file = st.session_state.get(key)
    st.session_state["ch_import_round"] = st.session_state.get("ch_import_round", 0) + 1  # kosongkan uploader
    if file is None:
        return
    try:
        content = text_to_html(read_story_file(file.name, file.getvalue()))
        store.update_chapter(user["uid"], work_id, chapter_id, content_html=content)
    except (StoryFileError, WorkspaceError) as error:
        st.session_state["ws_error"] = str(error); return
    set_editor_value(chapter_id, content)
    st.session_state[f"ch_saved_{chapter_id}"] = content
    st.session_state[f"ch_status_{chapter_id}"] = {"kind": "saved", "text": "Saved",
                                                   "when": f"Imported from {file.name}"}
    st.session_state["ws_toast"] = f"Isi bab diganti dengan {file.name}."


def _save_and_close(uid: str, store: WorkspaceStore, work_id: str, chapter_id: str) -> None:
    """Callback tombol Save: simpan isi + judul bab sekarang juga, lalu kembali ke halaman cerita."""
    content = saved_value(chapter_id)
    if content is None:
        return
    try:
        store.update_chapter(uid, work_id, chapter_id, content_html=content,
                             title=st.session_state.get(f"ch_title_{chapter_id}"))
    except WorkspaceError as error:
        st.session_state["ws_error"] = str(error)
        st.session_state[f"ch_status_{chapter_id}"] = {"kind": "error", "text": "Not saved, please try again"}
        return
    # samakan semua penanda supaya isi lama tidak tersimpan ulang saat bab dibuka lagi
    set_editor_value(chapter_id, content)
    st.session_state[f"ch_saved_{chapter_id}"] = content
    st.session_state[f"ch_status_{chapter_id}"] = _saved_status(datetime.now(timezone.utc))
    st.session_state["ws_toast"] = "Bab tersimpan."
    _go("detail")


@st.fragment
def _editor_fragment(uid: str, store: WorkspaceStore, work: dict[str, Any], chapter: dict[str, Any]) -> None:
    """Hanya bagian ini yang dijalankan ulang saat simpan otomatis, supaya halaman tidak berkedip."""
    if st.session_state.get("ws_view") != "chapter":
        st.rerun()  # tombol Save sudah menyimpan (di callback); tampilkan halaman cerita
    cid, work_id = chapter["chapter_id"], work["work_id"]
    saved_key, status_key = f"ch_saved_{cid}", f"ch_status_{cid}"
    if saved_key not in st.session_state:
        st.session_state[saved_key] = chapter.get("content_html", "")
        st.session_state[status_key] = _saved_status(chapter.get("updated_at"))

    # simpan dulu isi terbaru dari browser, baru tampilkan editor dengan status yang sudah benar
    latest = pending_value(cid)
    if latest is not None and latest != st.session_state[saved_key]:
        try:
            store.update_chapter(uid, work_id, cid, content_html=latest)
            st.session_state[saved_key] = latest
            st.session_state[status_key] = _saved_status(datetime.now(timezone.utc))
        except WorkspaceError as error:
            st.session_state[status_key] = {"kind": "error", "text": "Not saved, retrying on the next change"}
            st.error(str(error))

    language = str(work.get("language") or "")
    chapter_title = str(st.session_state.get(f"ch_title_{cid}") or chapter.get("title") or "").strip()
    value = chapter_editor(
        cid, chapter.get("content_html", ""), st.session_state[status_key],
        placeholder="Start writing your chapter here...",
        meta=f"{LANGUAGE_LABEL.get(language, language)} · Rich text",
        doc_left=str(work.get("title") or ""),
        doc_right=(f"{chapter_title} · " if chapter_title else "") + f"Chapter {chapter['number']}",
        on_save=lambda: _save_and_close(uid, store, work_id, cid),
    )
    words = count_words(value)
    if words > TRAIN_MAX_WORDS:
        st.markdown(f'<span class="len-warn">This chapter is longer than the stories the model was trained on '
                    f"(up to {TRAIN_MAX_WORDS:,} words), so its analysis may be less reliable. "
                    "Consider splitting it into two chapters.</span>", unsafe_allow_html=True)


def _render_chapter(user: dict[str, str], store: WorkspaceStore, work: dict[str, Any]) -> None:
    work_id = work["work_id"]
    try:
        chapters = store.list_chapters(user["uid"], work_id)
    except WorkspaceError:
        st.error("Bab tidak dapat dimuat."); return
    index = next((i for i, c in enumerate(chapters) if c["chapter_id"] == st.session_state.get("ws_chapter")), None)
    story = str(work.get("title") or "Story")
    crumb, nav = st.columns([3, 1], vertical_alignment="center")
    with crumb:
        breadcrumb([("Workspace", _to_list), (story, lambda: _go("detail")),
                    (f"Chapter {chapters[index]['number']}" if index is not None else "Chapter", None)], key="chapter")
    if index is None:
        st.warning("Bab ini tidak ditemukan. Mungkin sudah dihapus."); return
    chapter = chapters[index]
    cid = chapter["chapter_id"]
    with nav:
        with st.container(horizontal=True, gap="small", horizontal_alignment="right"):
            st.button("Previous", key="ch_prev", icon=":material/chevron_left:", disabled=index == 0,
                      on_click=_open_chapter, args=(chapters[index - 1]["chapter_id"],) if index > 0 else (cid,))
            st.button("Next", key="ch_next", icon=":material/chevron_right:", icon_position="right",
                      disabled=index == len(chapters) - 1, on_click=_open_chapter,
                      args=(chapters[index + 1]["chapter_id"],) if index < len(chapters) - 1 else (cid,))

    title_key = f"ch_title_{cid}"
    if title_key not in st.session_state:
        st.session_state[title_key] = chapter.get("title", "")
    with st.container(key="ch_head", horizontal=True, vertical_alignment="center", gap="medium"):
        st.markdown(f'<div class="ch-bignum">{chapter["number"]:02d}</div>', unsafe_allow_html=True, width="content")
        with st.container(gap=None, width="stretch"):
            st.markdown('<div class="ch-kicker">Chapter title</div>', unsafe_allow_html=True)
            st.text_input("Chapter title", key=title_key, max_chars=LIMITS["title"], label_visibility="collapsed",
                          placeholder="Untitled chapter", on_change=_save_title, args=(user, store, work_id, cid))
        st.markdown(f'<span class="ch-of-pill">Chapter {chapter["number"]} of {len(chapters)}</span>',
                    unsafe_allow_html=True, width="content")

    _editor_fragment(user["uid"], store, work, chapter)
    st.markdown(f'<p class="ch-save-note">{icon("info", 15)}Saving updates your chapter text. Run analysis from your '
                "story to refresh its metadata suggestions.</p>", unsafe_allow_html=True)

    upload_key = f"ch_import_{cid}_{st.session_state.get('ch_import_round', 0)}"
    with st.expander("Import from a .txt or .docx file", icon=":material/upload_file:"):
        st.caption("The file's text replaces everything currently in this chapter.")
        st.file_uploader("Chapter file", type=["txt", "docx"], key=upload_key, label_visibility="collapsed",
                         on_change=_import_file, args=(user, store, work_id, cid, upload_key))


def _finish_job() -> None:
    st.session_state.pop("ws_job", None)
    _go("detail")


def _render_analyzing(work: dict[str, Any]) -> None:
    job = st.session_state.get("ws_job")
    breadcrumb([("Workspace", _to_list), (str(work.get("title") or "Story"), lambda: _go("detail")), ("Analysis", None)],
               key="analyzing")
    if not job or job["work_id"] != work["work_id"]:
        st.info("Tidak ada analisis yang sedang berjalan.")
        st.button("Back to story", key="wsa_back", icon=":material/arrow_back:", on_click=_go, args=("detail",))
        return
    wa.render_progress(job, on_finish=_finish_job)
    left, _ = st.columns([2.6, 1], gap="medium")
    with left, st.container(horizontal=True, vertical_alignment="center"):
        st.button("Back to story", key="wsa_back", icon=":material/arrow_back:", on_click=_go, args=("detail",))
        st.markdown('<div class="ap-leave">You can leave this page. Analysis continues in your workspace.</div>',
                    unsafe_allow_html=True)


def _render_chapter_result(user: dict[str, str], work: dict[str, Any], ctx: dict[str, Any]) -> None:
    st.button(f"← Back to {work.get('title') or 'story'}", key="hist_back", on_click=_go, args=("detail",))
    ref = st.session_state.get("ws_result") or {}
    history_store = ctx.get("history_store")
    item = None
    if history_store is not None and ref.get("analysis_id"):
        try:
            item = history_store.get_analysis(user["uid"], ref["analysis_id"])
        except Exception:  # noqa: BLE001
            item = None
    if item is None:
        st.warning("Hasil analisis ini tidak ditemukan. Mungkin sudah dihapus dari History."); return
    label = f"Chapter {item.get('chapter_number', '?')}" + (f": {item['chapter_title']}" if item.get("chapter_title") else "")
    st.markdown(
        f'<div class="ws-crumb">{html.escape(str(work.get("title") or ""))}</div>'
        f'<div class="page-title">{html.escape(label)} · results</div>'
        f'<p class="page-sub">Analyzed on <b>{format_created_at(item.get("created_at"))}</b> · '
        f'{len(str(item.get("story") or "").split()):,} words. The chapter may have changed since then.</p>',
        unsafe_allow_html=True,
    )
    render_result_cards(item, str(item.get("story") or ""))


def render(user: dict[str, str], store: WorkspaceStore | None, history_store: Any = None,
           load_predictor: Any = None) -> None:
    if store is None:
        st.title("Workspace")
        st.error("Firestore belum dikonfigurasi. Workspace tidak tersedia."); return
    if toast := st.session_state.pop("ws_toast", None):
        st.toast(toast, icon=":material/check_circle:")
    if error := st.session_state.pop("ws_error", None):
        st.error(error)

    view = st.session_state.get("ws_view", "list")
    if view == "new":
        _render_form(user, store, None); return
    if view == "list" or not st.session_state.get("ws_work"):
        _render_list(user, store, {"history_store": history_store}); return

    try:
        work = store.get_work(user["uid"], st.session_state["ws_work"])
    except WorkspaceError:
        st.error("Cerita tidak dapat dimuat. Silakan coba lagi."); return
    if work is None:
        st.warning("Cerita ini tidak ditemukan. Mungkin sudah dihapus.")
        st.button("← Back to Workspace", key="hist_back", on_click=_go, args=("list",))
        return
    ctx = {"history_store": history_store, "load_predictor": load_predictor}
    if view == "edit":
        _render_form(user, store, work)
    elif view == "chapter":
        _render_chapter(user, store, work)
    elif view == "analyzing":
        _render_analyzing(work)
    elif view == "chapter_result":
        _render_chapter_result(user, work, ctx)
    else:
        _render_detail(user, store, work, ctx)
