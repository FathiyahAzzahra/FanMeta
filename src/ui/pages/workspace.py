"""Workspace: arsip & ruang kerja pribadi penulis (daftar cerita, form, detail cerita)."""
import html
from datetime import datetime, timezone
from typing import Any

import streamlit as st

from src.core.rich_text import count_words, text_to_html
from src.services.gpu_quota import GpuQuota
from src.core.story_file import StoryFileError, read_story_file
from src.services.workspace_store import LANGUAGES, LIMITS, STATUSES, WorkspaceError, WorkspaceStore
from src.ui.pages.analysis import TRAIN_MAX_WORDS
from src.core.i18n import language_label, num
from src.ui.components import (
    badge, breadcrumb, danger_box, format_created_at, format_relative, icon, icon_box, navigate_cb, open_dialog,
    page_header, rating_badge, status_badge, status_label, tr,
)
from src.ui.editor import chapter_editor, pending_value, saved_value, set_editor_value
from src.ui import device_choice
from src.ui.pages import workspace_analysis as wa
from src.ui.pages import workspace_log as wl
from src.ui.pages.results import render_result_cards
from src.core.workspace_metadata import chapter_state

_ALL = "All statuses"
_SORTS = ("Recently updated", "Title A-Z", "Most words")
_SORT_ID = {"Recently updated": "Terakhir diubah", "Title A-Z": "Judul A-Z", "Most words": "Kata terbanyak"}
_LANGUAGE_OPTION = {"Bahasa Indonesia": ("Indonesian — Bahasa Indonesia", "Bahasa Indonesia"),
                    "Bahasa Inggris": ("English — Bahasa Inggris", "Bahasa Inggris")}


def _status_option(value: str) -> str:
    return tr("All statuses", "Semua status") if value == _ALL else status_label(value)


def _go(view: str, work_id: str | None = None) -> None:
    st.session_state["ws_view"] = view
    if work_id is not None:
        st.session_state["ws_work"] = work_id


def _rating_or_empty(work: dict[str, Any]) -> str:
    return rating_badge(work["rating"]) if work.get("rating") else badge(tr("Not analyzed", "Belum dianalisis"), "grey")


def _to_list() -> None:
    _go("list")
    st.session_state.pop("ws_work", None)


def _chapters_label(n: int) -> str:
    return tr(f"{n} chapter" + ("" if n == 1 else "s"), f"{n} bab")


def _words(n: int) -> str:
    return tr(f"{n:,} words", f"{num(n)} kata")


# ---------------------------------------------------------------- daftar cerita
def _analyzed_today(history_store: Any, uid: str) -> int:
    if history_store is None:
        return 0
    try:
        items = history_store.list_history(uid)
    except Exception:  # noqa: BLE001 - statistik saja, jangan gagalkan halaman
        return 0
    today = datetime.now().astimezone().date()

    def day(value: Any) -> Any:
        value = value.to_datetime() if hasattr(value, "to_datetime") else value
        return value.astimezone().date() if isinstance(value, datetime) else None
    return sum(1 for h in items if h.get("source") == "workspace" and day(h.get("created_at")) == today)


def _render_list(user: dict[str, str], store: WorkspaceStore, ctx: dict[str, Any]) -> None:
    head, action = st.columns([4, 1], vertical_alignment="center")
    with head:
        page_header(tr("Every story has a home.", "Setiap cerita punya rumah."),
                    tr("Keep your chapters close and your metadata in sync.",
                       "Simpan bab-babmu di satu tempat dan jaga metadatanya tetap sesuai."),
                    kicker=tr("Your writing space", "Ruang menulismu"))
    with action:
        with st.container(horizontal=True, horizontal_alignment="right"):
            st.button(tr("+ New Story", "+ Cerita Baru"), key="ws_new", type="primary", on_click=_go, args=("new",))

    try:
        works = store.list_works(user["uid"])
    except WorkspaceError:
        st.error(tr("Your stories could not be loaded. Please try again.",
                    "Daftar cerita tidak dapat dimuat. Silakan coba lagi.")); return

    stats = [
        ("library", num(len(works)), tr("Stories in your library", "Cerita di perpustakaanmu")),
        ("feather", num(sum(int(w.get('word_count') or 0) for w in works)),
         tr("Words in your library", "Kata di perpustakaanmu")),
        ("sparkles", num(_analyzed_today(ctx.get('history_store'), user['uid'])),
         tr("Chapters analyzed today", "Bab dianalisis hari ini")),
    ]
    st.markdown('<div class="ws-stats">' + "".join(
        f'<div class="ws-stat">{icon_box(i)}<div><div class="ws-stat-n">{n}</div><div class="ws-stat-l">{lbl}</div></div></div>'
        for i, n, lbl in stats) + "</div>", unsafe_allow_html=True)

    if not works:
        st.markdown(f'<div class="ws-empty">{icon_box("book", 22)}<b>{tr("No stories yet", "Belum ada cerita")}</b>'
                    "<span>" + tr("Create your first story project to start writing chapter by chapter.",
                                  "Buat proyek cerita pertamamu untuk mulai menulis bab demi bab.") + "</span></div>",
                    unsafe_allow_html=True)
        return

    c_search, c_status, c_gap, c_count, c_sort = st.columns([3.1, 1.2, 1.2, .7, 1.4], vertical_alignment="center")
    with c_search:
        search = st.text_input(tr("Search", "Cari"), label_visibility="collapsed", key="ws_search",
                               placeholder=tr("Search by title or fandom", "Cari judul atau fandom"),
                               icon=":material/search:")
    with c_status:
        status = st.selectbox("Status", (_ALL, *STATUSES), key="ws_status", label_visibility="collapsed",
                              format_func=_status_option)
    query = search.strip().lower()
    shown = [
        w for w in works
        if (not query or query in str(w.get("title", "")).lower() or query in str(w.get("fandom", "")).lower())
        and (status == _ALL or w.get("status") == status)
    ]
    with c_count:
        count = tr(f'{len(shown)} stor{"y" if len(shown) == 1 else "ies"}', f"{len(shown)} cerita")
        st.markdown(f'<div class="ws-count">{count}</div>', unsafe_allow_html=True)
    with c_sort:
        sort = st.selectbox(tr("Sort", "Urutkan"), _SORTS, key="ws_sort", label_visibility="collapsed",
                            format_func=lambda v: tr(v, _SORT_ID[v]))
    if sort == "Title A-Z":
        shown.sort(key=lambda w: str(w.get("title", "")).lower())
    elif sort == "Most words":
        shown.sort(key=lambda w: int(w.get("word_count") or 0), reverse=True)

    if not shown:
        st.info(tr("No stories match your search.", "Tidak ada cerita yang cocok dengan pencarian."))
        return
    for start in range(0, len(shown), 3):
        cols = st.columns(3, gap="medium")
        for col, work in zip(cols, shown[start:start + 3]):
            with col, st.container(border=True):
                n = int(work.get("chapter_count") or 0)
                summary = str(work.get("summary") or "").strip() or tr("No summary yet.", "Belum ada ringkasan.")
                st.markdown(
                    f"""
                    <span class="ws-card-marker"></span>
                    <div class="wc-top">{status_badge(work.get("status"))}{_rating_or_empty(work)}</div>
                    <div class="wc-title">{html.escape(str(work.get("title") or tr("Untitled", "Tanpa judul")))}</div>
                    <div class="wc-fandom">{html.escape(str(work.get("fandom") or tr("No fandom", "Tanpa fandom")))}</div>
                    <p class="wc-summary">{html.escape(summary)}</p>
                    <div class="wc-meta">{icon("files", 15)}<span>{_chapters_label(n)}</span>
                    <span>{_words(int(work.get("word_count") or 0))}</span></div>
                    <hr class="wc-line">
                    """,
                    unsafe_allow_html=True,
                )
                foot_l, foot_r = st.columns([1.6, 1], vertical_alignment="center")
                with foot_l:
                    st.markdown(f'<div class="wc-edited">{tr("Edited", "Diubah")} '
                                f'{format_relative(work.get("updated_at"))}</div>', unsafe_allow_html=True)
                with foot_r:
                    with st.container(horizontal=True, horizontal_alignment="right"):
                        st.button(tr("Open", "Buka"), key=f"ws_open_{work['work_id']}", icon=":material/arrow_forward:",
                                  on_click=_go, args=("detail", work["work_id"]))
    st.markdown(f'<div class="ws-private">{icon("lock", 15)}' + tr(
        "Your workspace is private. Only you can see your stories and notes.",
        "Workspace-mu bersifat pribadi. Hanya kamu yang bisa melihat cerita dan catatanmu.") + "</div>",
        unsafe_allow_html=True)


# ---------------------------------------------------------------- form cerita
def _render_form(user: dict[str, str], store: WorkspaceStore, work: dict[str, Any] | None) -> None:
    editing = work is not None
    work = work or {}
    back_view = "detail" if editing else "list"
    if editing:
        breadcrumb([("Workspace", _to_list), (str(work.get("title") or tr("Story", "Cerita")), lambda: _go("detail")),
                    (tr("Edit", "Ubah"), None)], key="form")
        page_header(tr("Edit Story", "Ubah Cerita"),
                    tr("Update the details of your story. Your chapters stay as they are.",
                       "Perbarui detail ceritamu. Bab-babmu tidak berubah."))
    else:
        breadcrumb([("Workspace", _to_list), (tr("New Story", "Cerita Baru"), None)], key="form")
        page_header(tr("New Story", "Cerita Baru"),
                    tr("Set the scene. Give your story a home before adding your chapters.",
                       "Siapkan panggungnya. Beri ceritamu rumah sebelum menambahkan bab."))

    main, side = st.columns([2.15, 1], gap="medium")
    with main, st.form("ws_work_form", border=False):
        with st.container(border=True):
            st.markdown(f'<span class="form-card-marker"></span><div class="card-title">{tr("The essentials", "Yang utama")}'
                        f'<small>{tr("* Required fields", "* Wajib diisi")}</small></div>', unsafe_allow_html=True)
            title = st.text_input(tr("Title *", "Judul *"), value=work.get("title", ""), max_chars=LIMITS["title"],
                                  placeholder=tr("e.g. Salt and Thunder", "mis. Salt and Thunder"))
            fandom = st.text_input("Fandom *", value=work.get("fandom", ""), max_chars=LIMITS["fandom"],
                                   placeholder=tr("e.g. One Piece", "mis. One Piece"))
            st.markdown('<p class="field-help">' + tr("Use the fandom name readers will recognize on AO3.",
                                                      "Pakai nama fandom yang dikenali pembaca di AO3.") + "</p>",
                        unsafe_allow_html=True)
            c_lang, c_status = st.columns([2.3, 1])
            with c_lang:
                language = st.selectbox(tr("Language *", "Bahasa *"), LANGUAGES,
                                        format_func=lambda v: tr(*_LANGUAGE_OPTION[v]),
                                        index=LANGUAGES.index(work["language"]) if work.get("language") in LANGUAGES else 0)
            with c_status:
                status = st.selectbox("Status", STATUSES, format_func=status_label,
                                      index=STATUSES.index(work["status"]) if work.get("status") in STATUSES else 1)
        with st.container(border=True):
            st.markdown('<span class="form-card-marker"></span><div class="card-title">'
                        + tr("The people &amp; the premise", "Tokoh &amp; premis") + "</div>", unsafe_allow_html=True)
            characters = st.multiselect(tr("Characters", "Tokoh"), options=work.get("characters", []),
                                        default=work.get("characters", []), accept_new_options=True,
                                        placeholder=tr("Add character...", "Tambah tokoh..."))
            relationships = st.multiselect("Relationships", options=work.get("relationships", []),
                                           default=work.get("relationships", []), accept_new_options=True,
                                           placeholder=tr("Add relationship...", "Tambah relationship..."))
            st.markdown('<p class="field-help">' + tr(
                "Use “&amp;” for platonic relationships and “/” for romantic pairings.",
                "Pakai “&amp;” untuk hubungan platonis dan “/” untuk pasangan romantis.") + "</p>",
                unsafe_allow_html=True)
            summary = st.text_area(tr("Summary", "Ringkasan"), value=work.get("summary", ""),
                                   max_chars=LIMITS["summary"], height=110)
            st.markdown('<p class="field-help">' + tr(
                "A short introduction to your story. You can change this anytime.",
                "Perkenalan singkat ceritamu. Bisa diubah kapan saja.") + "</p>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f'<span class="form-card-marker"></span><div class="card-title start">{icon("lock", 17)} '
                        f'{tr("Private notes", "Catatan pribadi")}</div>', unsafe_allow_html=True)
            notes = st.text_area(tr("Notes for yourself", "Catatan untuk dirimu"), value=work.get("notes", ""),
                                 max_chars=LIMITS["notes"], height=90)
            st.markdown('<p class="field-help">' + tr(
                "Just for you. Notes are never included in metadata analysis.",
                "Hanya untukmu. Catatan tidak pernah ikut dianalisis.") + "</p>", unsafe_allow_html=True)
        foot_l, foot_r = st.columns([1.5, 1], vertical_alignment="center")
        with foot_l:
            st.markdown('<div class="form-foot-note">' + tr("Your story is private by default.",
                                                            "Ceritamu bersifat pribadi.") + "</div>",
                        unsafe_allow_html=True)
        with foot_r:
            with st.container(horizontal=True, horizontal_alignment="right"):
                cancelled = st.form_submit_button(tr("Cancel", "Batal"), key="ws_form_cancel")
                submitted = st.form_submit_button(
                    tr("Save Changes", "Simpan Perubahan") if editing else tr("Create Story", "Buat Cerita"),
                    type="primary", icon=None if editing else ":material/arrow_forward:")
    with side:
        steps = "".join(f'<li><span>{i}</span>{t}</li>' for i, t in enumerate((
            tr("Create your story", "Buat ceritamu"), tr("Write or paste your chapters", "Tulis atau tempel bab-babmu"),
            tr("Analyze and review your metadata", "Analisis dan periksa metadatanya")), start=1))
        st.markdown(
            f"""
            <div class="side-card">{icon_box("feather", 22)}
              <div class="side-title">{tr("A home for your next chapter", "Rumah untuk bab berikutnya")}</div>
              <p>{tr("Start with the basics. Your story grows from here.", "Mulai dari hal dasar. Ceritamu tumbuh dari sini.")}</p>
              <hr><ol class="side-steps">{steps}</ol>
            </div>
            <div class="side-note"><b>{tr("No need to choose a rating yet.", "Belum perlu memilih rating.")}</b>
              <p>{tr("FanMeta suggests a rating, warnings, and tags after reading your chapters. Your story details "
                     "help you stay organized.",
                     "FanMeta menyarankan rating, warning, dan tag setelah membaca bab-babmu. Detail cerita membantumu "
                     "tetap teratur.")}</p></div>
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
        st.session_state["ws_toast"] = (tr("Story changes saved.", "Perubahan cerita tersimpan.") if editing
                                        else tr("New story created.", "Cerita baru dibuat."))
        _go("detail", work_id)
        st.rerun()


# ---------------------------------------------------------------- detail cerita
def _delete_story_body(user: dict[str, str], store: WorkspaceStore, work: dict[str, Any]) -> None:
    n = int(work.get("chapter_count") or 0)
    title = str(work.get("title") or tr("Untitled", "Tanpa judul"))
    st.markdown('<p class="dlg-text">' + tr(
        f"This permanently deletes “{html.escape(title)}” and everything saved with it. This action can’t be undone.",
        f"Ini menghapus “{html.escape(title)}” beserta semua isinya secara permanen. Tindakan ini tidak bisa "
        "dibatalkan.") + "</p>"
                + danger_box(title, [f"{_chapters_label(n)} · {_words(int(work.get('word_count') or 0))}",
                                     tr("Includes all analysis results, the analysis log, and private notes.",
                                        "Termasuk semua hasil analisis, log analisis, dan catatan pribadi.")]),
                unsafe_allow_html=True)
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button(tr("Cancel", "Batal"), key="wsdel_cancel"):
            st.rerun()
        if st.button(tr("Delete story", "Hapus cerita"), key="wsdel_confirm", type="primary"):
            try:
                store.delete_work(user["uid"], work["work_id"])
            except WorkspaceError as error:
                st.error(str(error)); return
            st.session_state["ws_toast"] = tr(f'"{work.get("title")}" was deleted.', f'"{work.get("title")}" telah dihapus.')
            _go("list")
            st.session_state.pop("ws_work", None)
            st.rerun()


def _confirm_delete(*args: Any) -> None:
    open_dialog(tr("Delete this story?", "Hapus cerita ini?"), ":material/delete:", _delete_story_body, *args)


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
        st.session_state["ws_error"] = tr("History (Firestore) is unavailable, so analysis results can't be saved.",
                                          "Riwayat (Firestore) tidak tersedia, jadi hasil analisis tidak bisa disimpan.")
        return
    use_gpu = device_choice.wants_gpu("wsa_device", GpuQuota(ctx["history_store"].client))
    st.session_state["ws_job"] = wa.start_job(user, work, chapters, ctx["load_predictor"], ctx["history_store"], store,
                                              use_gpu=use_gpu)
    _go("analyzing")


def _open_result(analysis_id: str, chapter_id: str) -> None:
    st.session_state["ws_result"] = {"analysis_id": analysis_id, "chapter_id": chapter_id}
    _go("chapter_result")


def _render_detail(user: dict[str, str], store: WorkspaceStore, work: dict[str, Any], ctx: dict[str, Any]) -> None:
    title = str(work.get("title") or tr("Untitled", "Tanpa judul"))
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
            st.button(tr("Edit", "Ubah"), key="ws_edit", icon=":material/edit:", on_click=_go, args=("edit",))
            if st.button(tr("Delete", "Hapus"), key="ws_delete", icon=":material/delete:"):
                _confirm_delete(user, store, work)
    n = int(work.get("chapter_count") or 0)
    st.markdown(
        f'<p class="sd-sub"><span class="sd-fandom">{html.escape(str(work.get("fandom") or tr("No fandom", "Tanpa fandom")))}</span>'
        f'{html.escape(language_label(language))} · {_chapters_label(n)} · '
        f'{_words(int(work.get("word_count") or 0))} · {tr("Updated", "Diperbarui")} '
        f'{format_relative(work.get("updated_at"))}</p>',
        unsafe_allow_html=True,
    )

    try:
        chapters = store.list_chapters(user["uid"], work["work_id"])
    except WorkspaceError:
        st.error(tr("The chapters could not be loaded.", "Daftar bab tidak dapat dimuat.")); return
    running = _job_running(work["work_id"])
    if running:
        with st.container(horizontal=True, vertical_alignment="center"):
            st.info(tr("Analysis is running in the background. Results are saved automatically.",
                       "Analisis sedang berjalan di latar belakang. Hasilnya tersimpan otomatis."))
            st.button(tr("View progress", "Lihat progres"), key="wsa_view", on_click=_go, args=("analyzing",))

    main, side = st.columns([2.6, 1], gap="medium")
    with main:
        if not running:
            quota = GpuQuota(ctx["history_store"].client) if ctx.get("history_store") is not None else None
            wa.render_story_metadata(work, chapters, on_analyze=lambda: _start_analysis(
                user, store, work, wa.needs_analysis(chapters), ctx), quota=quota)
        _render_chapter_list(user, store, work, chapters, ctx, running)
    with side:
        summary = str(work.get("summary") or "").strip()
        rels = work.get("relationships") or []
        st.markdown(
            f"""
            <div class="side-card"><div class="side-title">{tr("Summary", "Ringkasan")}</div>
              <p class="side-text">{html.escape(summary) if summary else '<span class="ws-muted">' + tr("No summary yet.", "Belum ada ringkasan.") + '</span>'}</p></div>
            <div class="side-card"><div class="side-title">{tr("Characters", "Tokoh")}</div>
              <div class="chips">{_chips(work.get("characters") or [])}</div><hr>
              <div class="side-label">Relationships</div>
              <div class="side-lines">{"".join(f"<div>{html.escape(r)}</div>" for r in rels) or '<span class="ws-muted">-</span>'}</div></div>
            <div class="side-card"><div class="side-title">{icon("lock", 17)} {tr("Private notes", "Catatan pribadi")}</div>
              <p class="side-text">{html.escape(str(work.get("notes") or "")) or '<span class="ws-muted">' + tr("No notes yet.", "Belum ada catatan.") + '</span>'}</p>
              <div class="side-foot">{tr("Only visible to you · Not analyzed", "Hanya terlihat olehmu · Tidak dianalisis")}</div></div>
            """,
            unsafe_allow_html=True,
        )
        st.button(tr("Need a hand? Explore the glossary →", "Butuh bantuan? Buka glosarium →"), key="ws_glossary",
                  type="tertiary",
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
    return tr("Chapter", "Bab") + f" {chapter['number']}" + (f": {title}" if title else "")


def _delete_chapter_body(user: dict[str, str], store: WorkspaceStore, work_id: str, chapter: dict[str, Any]) -> None:
    st.markdown('<p class="dlg-text">' + tr("This permanently deletes the chapter text. This action can’t be undone.",
                                            "Ini menghapus teks bab secara permanen. Tindakan ini tidak bisa dibatalkan.")
                + "</p>"
                + danger_box(chapter_label(chapter), [_words(int(chapter.get("word_count") or 0)),
                                                      tr("Its past analyses stay in History and the Analysis Log.",
                                                         "Analisis sebelumnya tetap ada di Riwayat dan Log Analisis.")],
                             "files"),
                unsafe_allow_html=True)
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button(tr("Cancel", "Batal"), key="chdel_cancel"):
            st.rerun()
        if st.button(tr("Delete chapter", "Hapus bab"), key="chdel_confirm", type="primary"):
            try:
                store.delete_chapter(user["uid"], work_id, chapter["chapter_id"])
            except WorkspaceError as error:
                st.error(str(error)); return
            st.session_state["ws_toast"] = tr(f"{chapter_label(chapter)} was deleted.",
                                              f"{chapter_label(chapter)} telah dihapus.")
            st.rerun()


def _confirm_delete_chapter(*args: Any) -> None:
    open_dialog(tr("Delete this chapter?", "Hapus bab ini?"), ":material/delete:", _delete_chapter_body, *args)


def _render_chapter_list(user: dict[str, str], store: WorkspaceStore, work: dict[str, Any],
                         chapters: list[dict[str, Any]], ctx: dict[str, Any], running: bool) -> None:
    work_id = work["work_id"]
    with st.container(border=True):
        head, action = st.columns([3, 1], vertical_alignment="center")
        with head:
            st.markdown(f'<span class="ws-section-marker"></span><div class="card-title">{tr("Chapters", "Bab")} '
                        f'<span class="count-pill">{len(chapters)}</span></div>', unsafe_allow_html=True)
        with action:
            with st.container(horizontal=True, horizontal_alignment="right"):
                st.button(tr("+ Add chapter", "+ Tambah bab"), key="ws_ch_new", on_click=_new_chapter,
                          args=(user, store, work_id))
        if not chapters:
            st.markdown('<p class="ws-muted">' + tr("No chapters yet. Click + Add chapter to start writing.",
                                                    "Belum ada bab. Klik + Tambah bab untuk mulai menulis.") + "</p>",
                        unsafe_allow_html=True)
        for i, chapter in enumerate(chapters):
            cid = chapter["chapter_id"]
            state = chapter_state(chapter)
            analysis = chapter.get("analysis") or {}
            badges = (rating_badge(analysis["rating"]) if analysis.get("rating") else "") + wa.state_badge(state)
            title = str(chapter.get("title") or "").strip() or tr("Untitled chapter", "Bab tanpa judul")
            st.markdown(
                f'<div class="ch-row{" ch-first" if i == 0 else ""}"><span class="ch-num">{chapter["number"]:02d}</span>'
                f'<div class="ch-body"><div class="ch-title">{html.escape(title)}</div>'
                f'<div class="ch-meta">{_words(int(chapter.get("word_count") or 0))} · '
                f'{tr("Saved", "Disimpan")} {format_relative(chapter.get("updated_at"))}</div></div>'
                f'<div class="ch-badges">{badges}</div></div>',
                unsafe_allow_html=True,
            )
            with st.container(horizontal=True, gap="small"):
                st.markdown('<span class="ch-actions-marker"></span>', unsafe_allow_html=True)
                st.button(tr("Write", "Tulis"), key=f"ws_ch_open_{cid}", icon=":material/edit:",
                          on_click=_open_chapter, args=(cid,))
                st.button(tr("Analyze", "Analisis"), key=f"ws_ch_an_{cid}", icon=":material/auto_awesome:",
                          disabled=state == "empty" or running,
                          help=tr("This chapter is empty.", "Bab ini masih kosong.") if state == "empty" else None,
                          on_click=_start_analysis, args=(user, store, work, [chapter], ctx))
                st.button(tr("Results", "Hasil"), key=f"ws_ch_res_{cid}", icon=":material/monitoring:",
                          disabled=not analysis.get("analysis_id"),
                          on_click=_open_result, args=(analysis.get("analysis_id"), cid))
                st.button(tr("Up", "Naik"), key=f"ws_ch_up_{cid}", icon=":material/arrow_upward:", disabled=i == 0,
                          on_click=_move_chapter, args=(user, store, work_id, cid, -1))
                st.button(tr("Down", "Turun"), key=f"ws_ch_down_{cid}", icon=":material/arrow_downward:",
                          disabled=i == len(chapters) - 1, on_click=_move_chapter, args=(user, store, work_id, cid, 1))
                if st.button(tr("Delete", "Hapus"), key=f"ws_ch_del_{cid}", icon=":material/delete:", type="tertiary"):
                    _confirm_delete_chapter(user, store, work_id, chapter)
        if len(chapters) > 1:
            st.markdown('<p class="ch-note">' + tr(
                "Use Up / Down to reorder chapters. Chapter references update with their new position.",
                "Pakai Naik / Turun untuk mengubah urutan bab. Nomor bab ikut menyesuaikan.") + "</p>",
                unsafe_allow_html=True)


def _save_title(user: dict[str, str], store: WorkspaceStore, work_id: str, chapter_id: str) -> None:
    try:
        store.update_chapter(user["uid"], work_id, chapter_id, title=st.session_state[f"ch_title_{chapter_id}"])
    except WorkspaceError as error:
        st.session_state["ws_error"] = str(error)


def _saved_status(value: Any) -> dict[str, str]:
    return {"kind": "saved", "text": tr("Saved", "Tersimpan"),
            "when": tr(f"Last saved {format_relative(value)}", f"Terakhir disimpan {format_relative(value)}")}


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
    st.session_state[f"ch_status_{chapter_id}"] = {"kind": "saved", "text": tr("Saved", "Tersimpan"),
                                                   "when": tr(f"Imported from {file.name}", f"Diimpor dari {file.name}")}
    st.session_state["ws_toast"] = tr(f"Chapter text replaced with {file.name}.", f"Isi bab diganti dengan {file.name}.")


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
        st.session_state[f"ch_status_{chapter_id}"] = {"kind": "error",
                                                       "text": tr("Not saved, please try again",
                                                                  "Belum tersimpan, coba lagi")}
        return
    # samakan semua penanda supaya isi lama tidak tersimpan ulang saat bab dibuka lagi
    set_editor_value(chapter_id, content)
    st.session_state[f"ch_saved_{chapter_id}"] = content
    st.session_state[f"ch_status_{chapter_id}"] = _saved_status(datetime.now(timezone.utc))
    st.session_state["ws_toast"] = tr("Chapter saved.", "Bab tersimpan.")
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
            st.session_state[status_key] = {"kind": "error",
                                            "text": tr("Not saved, retrying on the next change",
                                                       "Belum tersimpan, dicoba lagi saat ada perubahan")}
            st.error(str(error))

    language = str(work.get("language") or "")
    chapter_title = str(st.session_state.get(f"ch_title_{cid}") or chapter.get("title") or "").strip()
    value = chapter_editor(
        cid, chapter.get("content_html", ""), st.session_state[status_key],
        placeholder=tr("Start writing your chapter here...", "Mulai tulis babmu di sini..."),
        meta=f"{language_label(language)} · " + tr("Rich text", "Teks berformat"),
        doc_left=str(work.get("title") or ""),
        doc_right=(f"{chapter_title} · " if chapter_title else "") + tr("Chapter", "Bab") + f" {chapter['number']}",
        on_save=lambda: _save_and_close(uid, store, work_id, cid),
    )
    words = count_words(value)
    if words > TRAIN_MAX_WORDS:
        st.markdown('<span class="len-warn">' + tr(
            f"This chapter is longer than the stories the model was trained on (up to {num(TRAIN_MAX_WORDS)} words), so "
            "its analysis may be less reliable. Consider splitting it into two chapters.",
            f"Bab ini lebih panjang dari cerita yang dipakai melatih model (maksimal {num(TRAIN_MAX_WORDS)} kata), jadi "
            "hasil analisisnya bisa kurang akurat. Pertimbangkan untuk membaginya menjadi dua bab.") + "</span>",
            unsafe_allow_html=True)


def _render_chapter(user: dict[str, str], store: WorkspaceStore, work: dict[str, Any]) -> None:
    work_id = work["work_id"]
    try:
        chapters = store.list_chapters(user["uid"], work_id)
    except WorkspaceError:
        st.error(tr("The chapter could not be loaded.", "Bab tidak dapat dimuat.")); return
    index = next((i for i, c in enumerate(chapters) if c["chapter_id"] == st.session_state.get("ws_chapter")), None)
    story = str(work.get("title") or tr("Story", "Cerita"))
    word = tr("Chapter", "Bab")
    crumb, nav = st.columns([3, 1], vertical_alignment="center")
    with crumb:
        breadcrumb([("Workspace", _to_list), (story, lambda: _go("detail")),
                    (f"{word} {chapters[index]['number']}" if index is not None else word, None)], key="chapter")
    if index is None:
        st.warning(tr("This chapter was not found. It may have been deleted.",
                      "Bab ini tidak ditemukan. Mungkin sudah dihapus.")); return
    chapter = chapters[index]
    cid = chapter["chapter_id"]
    with nav:
        with st.container(horizontal=True, gap="small", horizontal_alignment="right"):
            st.button(tr("Previous", "Sebelumnya"), key="ch_prev", icon=":material/chevron_left:", disabled=index == 0,
                      on_click=_open_chapter, args=(chapters[index - 1]["chapter_id"],) if index > 0 else (cid,))
            st.button(tr("Next", "Berikutnya"), key="ch_next", icon=":material/chevron_right:", icon_position="right",
                      disabled=index == len(chapters) - 1, on_click=_open_chapter,
                      args=(chapters[index + 1]["chapter_id"],) if index < len(chapters) - 1 else (cid,))

    title_key = f"ch_title_{cid}"
    if title_key not in st.session_state:
        st.session_state[title_key] = chapter.get("title", "")
    with st.container(key="ch_head", horizontal=True, vertical_alignment="center", gap="medium"):
        st.markdown(f'<div class="ch-bignum">{chapter["number"]:02d}</div>', unsafe_allow_html=True, width="content")
        with st.container(gap=None, width="stretch"):
            st.markdown(f'<div class="ch-kicker">{tr("Chapter title", "Judul bab")}</div>', unsafe_allow_html=True)
            st.text_input(tr("Chapter title", "Judul bab"), key=title_key, max_chars=LIMITS["title"],
                          label_visibility="collapsed", placeholder=tr("Untitled chapter", "Bab tanpa judul"),
                          on_change=_save_title, args=(user, store, work_id, cid))
        of = tr(f"Chapter {chapter['number']} of {len(chapters)}", f"Bab {chapter['number']} dari {len(chapters)}")
        st.markdown(f'<span class="ch-of-pill">{of}</span>', unsafe_allow_html=True, width="content")

    _editor_fragment(user["uid"], store, work, chapter)
    st.markdown(f'<p class="ch-save-note">{icon("info", 15)}' + tr(
        "Saving updates your chapter text. Run analysis from your story to refresh its metadata suggestions.",
        "Menyimpan hanya memperbarui teks bab. Jalankan analisis dari halaman cerita untuk memperbarui saran "
        "metadatanya.") + "</p>", unsafe_allow_html=True)

    upload_key = f"ch_import_{cid}_{st.session_state.get('ch_import_round', 0)}"
    with st.expander(tr("Import from a .txt or .docx file", "Impor dari file .txt atau .docx"),
                     icon=":material/upload_file:"):
        st.caption(tr("The file's text replaces everything currently in this chapter.",
                      "Teks dari file akan menggantikan seluruh isi bab ini."))
        st.file_uploader(tr("Chapter file", "File bab"), type=["txt", "docx"], key=upload_key,
                         label_visibility="collapsed",
                         on_change=_import_file, args=(user, store, work_id, cid, upload_key))


def _finish_job() -> None:
    st.session_state.pop("ws_job", None)
    _go("detail")


def _render_analyzing(work: dict[str, Any]) -> None:
    job = st.session_state.get("ws_job")
    breadcrumb([("Workspace", _to_list), (str(work.get("title") or tr("Story", "Cerita")), lambda: _go("detail")),
                (tr("Analysis", "Analisis"), None)], key="analyzing")
    back = tr("Back to story", "Kembali ke cerita")
    if not job or job["work_id"] != work["work_id"]:
        st.info(tr("No analysis is running.", "Tidak ada analisis yang sedang berjalan."))
        st.button(back, key="wsa_back", icon=":material/arrow_back:", on_click=_go, args=("detail",))
        return
    wa.render_progress(job, on_finish=_finish_job)
    left, _ = st.columns([2.6, 1], gap="medium")
    with left, st.container(horizontal=True, vertical_alignment="center"):
        st.button(back, key="wsa_back", icon=":material/arrow_back:", on_click=_go, args=("detail",))
        st.markdown('<div class="ap-leave">' + tr("You can leave this page. Analysis continues in your workspace.",
                                                  "Kamu boleh meninggalkan halaman ini. Analisis tetap berjalan.")
                    + "</div>", unsafe_allow_html=True)


def _render_chapter_result(user: dict[str, str], work: dict[str, Any], ctx: dict[str, Any]) -> None:
    story = work.get("title") or tr("story", "cerita")
    st.button(tr(f"← Back to {story}", f"← Kembali ke {story}"), key="hist_back", on_click=_go, args=("detail",))
    ref = st.session_state.get("ws_result") or {}
    history_store = ctx.get("history_store")
    item = None
    if history_store is not None and ref.get("analysis_id"):
        try:
            item = history_store.get_analysis(user["uid"], ref["analysis_id"])
        except Exception:  # noqa: BLE001
            item = None
    if item is None:
        st.warning(tr("This analysis was not found. It may have been deleted from History.",
                      "Hasil analisis ini tidak ditemukan. Mungkin sudah dihapus dari Riwayat.")); return
    label = (tr("Chapter", "Bab") + f" {item.get('chapter_number', '?')}"
             + (f": {item['chapter_title']}" if item.get("chapter_title") else ""))
    words = _words(len(str(item.get("story") or "").split()))
    st.markdown(
        f'<div class="ws-crumb">{html.escape(str(work.get("title") or ""))}</div>'
        f'<div class="page-title">{html.escape(label)} · {tr("results", "hasil")}</div>'
        f'<p class="page-sub">{tr("Analyzed on", "Dianalisis pada")} <b>{format_created_at(item.get("created_at"))}</b> · '
        + tr(f"{words}. The chapter may have changed since then.", f"{words}. Isi bab mungkin sudah berubah sejak itu.")
        + "</p>",
        unsafe_allow_html=True,
    )
    render_result_cards(item, str(item.get("story") or ""))


def render(user: dict[str, str], store: WorkspaceStore | None, history_store: Any = None,
           load_predictor: Any = None) -> None:
    if store is None:
        page_header("Workspace")
        st.error(tr("Firestore is not configured, so Workspace is unavailable.",
                    "Firestore belum dikonfigurasi. Workspace tidak tersedia.")); return
    if toast := st.session_state.pop("ws_toast", None):
        st.toast(toast, icon=":material/check_circle:")
    if error := st.session_state.pop("ws_error", None):
        st.error(error)
    if notice := st.session_state.pop("ws_engine_notice", None):
        st.warning(notice)  # GPU diminta tetapi analisis dijalankan dengan CPU

    view = st.session_state.get("ws_view", "list")
    if view == "new":
        _render_form(user, store, None); return
    if view == "list" or not st.session_state.get("ws_work"):
        _render_list(user, store, {"history_store": history_store}); return

    try:
        work = store.get_work(user["uid"], st.session_state["ws_work"])
    except WorkspaceError:
        st.error(tr("The story could not be loaded. Please try again.",
                    "Cerita tidak dapat dimuat. Silakan coba lagi.")); return
    if work is None:
        st.warning(tr("This story was not found. It may have been deleted.",
                      "Cerita ini tidak ditemukan. Mungkin sudah dihapus."))
        st.button(tr("← Back to Workspace", "← Kembali ke Workspace"), key="hist_back", on_click=_go, args=("list",))
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
