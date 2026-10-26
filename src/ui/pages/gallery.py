"""Public story gallery: daftar cerita, halaman baca, like, dan komentar."""
import html
import time
from typing import Any

import streamlit as st

from src.ml import fanmeta_utils as U
from src.services.gallery_store import MAX_COMMENT_CHARS, MAX_PEN_NAME_CHARS, GalleryError, GalleryStore
from src.ui.components import (
    ADULT_RATINGS, LANGUAGE_LABEL, default_name, format_created_at, navigate,
    rating_badge, require_login,
)
from src.ui.pages.results import render_result_cards, summary_html

PAGE_SIZE = 12
COMMENT_COOLDOWN_SECONDS = 10
_ALL = "All"


@st.cache_data(ttl=60, show_spinner=False)
def cached_works(_gallery: GalleryStore) -> list[dict[str, Any]]:
    return _gallery.list_works()


def refresh_gallery() -> None:
    """Panggil setelah publish/unpublish/like/komentar agar daftar galeri langsung terbarui."""
    cached_works.clear()


def open_work(work_id: str) -> None:
    st.session_state["gallery_work"] = work_id
    st.session_state["page"] = "work"


def is_adult(rating: str) -> bool:
    return str(rating).strip().lower() in ADULT_RATINGS


def pen_name_for(user: dict[str, str], gallery: GalleryStore) -> str:
    try:
        return gallery.get_pen_name(user["uid"]) or default_name(user)
    except GalleryError:
        return default_name(user)


@st.dialog("Remove from gallery?")
def confirm_unpublish(user: dict[str, str], gallery: GalleryStore, work_id: str, title: str) -> None:
    st.write(f"**{title}** will be removed from the public gallery, including all of its likes and "
             "comments. Your private analysis history is not affected.")
    cancel_col, ok_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", key="unpub_cancel", use_container_width=True):
            st.rerun()
    with ok_col:
        if st.button("Unpublish", key="unpub_confirm", type="primary", use_container_width=True):
            try:
                gallery.unpublish(user["uid"], work_id)
            except GalleryError as error:
                st.error(str(error)); return
            refresh_gallery()
            if st.session_state.get("page") == "work":
                st.session_state.pop("gallery_work", None)
                st.session_state["page"] = "gallery"
            st.session_state["gallery_toast"] = f'"{title}" telah dihapus dari galeri.'
            st.rerun()


# ---------------------------------------------------------------- daftar galeri
def work_card(work: dict[str, Any], key_prefix: str = "gal") -> None:
    adult = is_adult(work.get("rating", ""))
    hidden = adult and not st.session_state.get("age_ok")
    warnings = [w for w in work.get("warnings") or [] if w.strip().lower() != "no archive warnings apply"]
    tags = list(work.get("tags") or [])
    tag_html = "".join(f'<span class="gc-tag">{html.escape(t)}</span>' for t in tags[:4])
    if len(tags) > 4:
        tag_html += f'<span class="gc-tag gc-more">+{len(tags) - 4}</span>'
    warn_html = "".join(f'<span class="gc-warn">{html.escape(w)}</span>' for w in warnings)
    snippet = (
        '<p class="gc-snippet gc-hidden">Mature content. Confirm you are 18+ to read this story.</p>'
        if hidden else
        f'<p class="gc-snippet">{html.escape(str(work.get("snippet") or ""))}…</p>'
    )
    with st.container(border=True):
        st.markdown(
            f"""
            <span class="gallery-card-marker"></span>
            <div class="gc-title">{html.escape(str(work.get("title") or "Untitled Draft"))}</div>
            <div class="gc-meta">by <b>{html.escape(str(work.get("pen_name") or "Anonymous"))}</b>
            · {format_created_at(work.get("published_at"))}</div>
            <div class="gc-badges">{rating_badge(work.get("rating", ""))}{warn_html}</div>
            {snippet}
            <div class="gc-tags">{tag_html}</div>
            <div class="gc-stats"><span>♥ {int(work.get("like_count") or 0)}</span>
            <span>💬 {int(work.get("comment_count") or 0)}</span>
            <span>{int(work.get("word_count") or 0):,} words</span>
            <span>{html.escape(LANGUAGE_LABEL.get(work.get("language", ""), str(work.get("language", ""))))}</span></div>
            """,
            unsafe_allow_html=True,
        )
        st.button("Read story →", key=f"{key_prefix}_read_{work['work_id']}",
                  on_click=open_work, args=(work["work_id"],))


def render_grid(works: list[dict[str, Any]], key_prefix: str = "gal", columns: int = 3) -> None:
    for start in range(0, len(works), columns):
        cols = st.columns(columns, gap="medium")
        for col, work in zip(cols, works[start:start + columns]):
            with col:
                work_card(work, key_prefix)


def _render_list(gallery: GalleryStore) -> None:
    st.title("Story Gallery")
    st.markdown('<p class="page-kicker">Read fanfiction shared by FanMeta writers, together with the '
                "metadata FanMeta recommended for each story.</p>", unsafe_allow_html=True)
    try:
        works = cached_works(gallery)
    except GalleryError:
        st.error("Galeri tidak dapat dimuat. Silakan coba lagi."); return

    with st.container(border=True):
        st.markdown('<span class="hist-search-marker"></span>', unsafe_allow_html=True)
        c_search, c_rating, c_warn, c_sort = st.columns([2.4, 1.2, 1.6, 1.2], vertical_alignment="bottom")
        with c_search:
            search = st.text_input("Search", placeholder="Search by title or pen name...", key="gal_search")
        with c_rating:
            rating = st.selectbox("Rating", [_ALL, *U.RATINGS], key="gal_rating")
        with c_warn:
            warning = st.selectbox("Archive warning", [_ALL, *U.WARNING_LABELS], key="gal_warning")
        with c_sort:
            sort = st.selectbox("Sort by", ("Newest", "Most liked", "Most discussed"), key="gal_sort")
        tags = st.pills("Tags", list(U.TAGS), selection_mode="multi", key="gal_tags")

    query = search.strip().lower()
    filtered = [
        w for w in works
        if (not query or query in str(w.get("title", "")).lower() or query in str(w.get("pen_name", "")).lower())
        and (rating == _ALL or w.get("rating") == rating)
        and (warning == _ALL or warning in (w.get("warnings") or []))
        and all(t in (w.get("tags") or []) for t in tags or [])
    ]
    if sort == "Most liked":
        filtered.sort(key=lambda w: int(w.get("like_count") or 0), reverse=True)
    elif sort == "Most discussed":
        filtered.sort(key=lambda w: int(w.get("comment_count") or 0), reverse=True)

    if not works:
        st.info("Belum ada cerita di galeri. Publikasikan ceritamu dari halaman History.")
        return
    if not filtered:
        st.info("Tidak ada cerita yang cocok dengan filter.")
        return

    st.caption(f"{len(filtered)} stor{'y' if len(filtered) == 1 else 'ies'}")
    limit = st.session_state.get("gallery_limit", PAGE_SIZE)
    render_grid(filtered[:limit])
    if len(filtered) > limit:
        if st.button("Load more", key="gal_more"):
            st.session_state["gallery_limit"] = limit + PAGE_SIZE
            st.rerun()


# ---------------------------------------------------------------- halaman cerita
def _confirm_age() -> None:
    st.session_state["age_ok"] = True


def _back_to_list() -> None:
    st.session_state.pop("gallery_work", None)
    st.session_state["page"] = "gallery"


def _render_like(user: dict[str, str] | None, gallery: GalleryStore, work: dict[str, Any]) -> None:
    likes = int(work.get("like_count") or 0)
    if user is None:
        if st.button(f"♡ Like · {likes}", key="work_like", use_container_width=True):
            require_login("work")
        return
    try:
        liked = gallery.has_liked(work["work_id"], user["uid"])
    except GalleryError:
        liked = False
    label = f"♥ Liked · {likes}" if liked else f"♡ Like · {likes}"
    if st.button(label, key="work_liked" if liked else "work_like", use_container_width=True):
        try:
            gallery.toggle_like(work["work_id"], user["uid"])
        except GalleryError as error:
            st.error(str(error)); return
        refresh_gallery()
        st.rerun()


@st.dialog("Delete this comment?")
def _confirm_delete_comment(user: dict[str, str], gallery: GalleryStore, work_id: str, comment_id: str) -> None:
    st.write("This comment will be permanently removed.")
    cancel_col, ok_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", key="cdel_cancel", use_container_width=True):
            st.rerun()
    with ok_col:
        if st.button("Delete", key="cdel_confirm", type="primary", use_container_width=True):
            try:
                gallery.delete_comment(work_id, comment_id, user["uid"])
            except GalleryError as error:
                st.error(str(error)); return
            refresh_gallery()
            st.rerun()


def _render_comments(user: dict[str, str] | None, gallery: GalleryStore, work: dict[str, Any]) -> None:
    try:
        comments = gallery.list_comments(work["work_id"])
    except GalleryError:
        st.error("Komentar tidak dapat dimuat."); return

    st.markdown(f'<div class="cm-title">Comments ({len(comments)})</div>', unsafe_allow_html=True)
    if not comments:
        st.markdown('<p class="empty-copy">No comments yet. Be the first to leave one!</p>', unsafe_allow_html=True)
    for comment in comments:
        with st.container(border=True):
            st.markdown(
                f"""
                <span class="comment-marker"></span>
                <div class="cm-head"><b>{html.escape(str(comment.get("pen_name") or "Anonymous"))}</b>
                {'<span class="cm-author">Author</span>' if comment.get("uid") == work.get("owner_uid") else ""}
                <small>{format_created_at(comment.get("created_at"))}</small></div>
                <div class="cm-text">{html.escape(str(comment.get("text") or ""))}</div>
                """,
                unsafe_allow_html=True,
            )
            if user and user["uid"] in (comment.get("uid"), work.get("owner_uid")):
                if st.button("Delete", key=f"cm_del_{comment['comment_id']}"):
                    _confirm_delete_comment(user, gallery, work["work_id"], comment["comment_id"])

    if user is None:
        st.markdown('<p class="empty-copy">Login to like and comment on this story.</p>', unsafe_allow_html=True)
        if st.button("Login to comment", key="work_login_comment"):
            require_login("work")
        return

    with st.form("comment_form", clear_on_submit=True, border=True):
        pen_name = st.text_input("Display name", value=pen_name_for(user, gallery), max_chars=MAX_PEN_NAME_CHARS)
        text = st.text_area("Write a comment", max_chars=MAX_COMMENT_CHARS, height=110,
                            placeholder="Share what you liked about this story...")
        submitted = st.form_submit_button("Post comment")
    if submitted:
        wait = COMMENT_COOLDOWN_SECONDS - (time.time() - st.session_state.get("last_comment_at", 0))
        if wait > 0:
            st.warning(f"Tunggu {wait:.0f} detik sebelum mengirim komentar lagi."); return
        try:
            gallery.add_comment(work["work_id"], user["uid"], pen_name, text)
        except GalleryError as error:
            st.error(str(error)); return
        st.session_state["last_comment_at"] = time.time()
        refresh_gallery()
        st.rerun()


def _render_work(user: dict[str, str] | None, gallery: GalleryStore, work_id: str) -> None:
    st.button("← Back to Gallery", key="hist_back", on_click=_back_to_list)
    try:
        work = gallery.get_work(work_id)
    except GalleryError:
        st.error("Cerita tidak dapat dimuat. Silakan coba lagi."); return
    if work is None:
        st.warning("Cerita ini sudah tidak ada di galeri."); return

    title = str(work.get("title") or "Untitled Draft")
    story = str(work.get("story") or "")
    language = str(work.get("language") or "")
    st.markdown(
        f"""
        <span class="results-marker"></span>
        <div class="page-title">{html.escape(title)}</div>
        <p class="page-sub">by <b>{html.escape(str(work.get("pen_name") or "Anonymous"))}</b>
        · Published {format_created_at(work.get("published_at"))}
        · {html.escape(LANGUAGE_LABEL.get(language, language))} · {int(work.get("word_count") or 0):,} words</p>
        """,
        unsafe_allow_html=True,
    )

    if is_adult(work.get("rating", "")) and not st.session_state.get("age_ok"):
        with st.container(border=True):
            st.markdown(
                f"""
                <span class="age-gate-marker"></span>
                <div class="ag-title">This story is rated {html.escape(str(work.get("rating")))}</div>
                <p class="ag-text">It may contain content intended for adult readers only.
                Please confirm that you are 18 years or older to continue.</p>
                """,
                unsafe_allow_html=True,
            )
            with st.container(horizontal=True):
                st.button("I am 18 or older", key="age_yes", type="primary", on_click=_confirm_age)
                st.button("Back to Gallery", key="age_no", on_click=_back_to_list)
        return

    main, side = st.columns([2.2, 1], gap="large")
    with main:
        story_tab, analysis_tab = st.tabs(["Story", "FanMeta analysis"])
        with story_tab:
            paragraphs = [p.strip() for p in story.split("\n") if p.strip()]
            body = "".join(f"<p>{html.escape(p)}</p>" for p in paragraphs) or "<p>-</p>"
            st.markdown(f'<div class="story-body">{body}</div>', unsafe_allow_html=True)
        with analysis_tab:
            render_result_cards(work, story)
        _render_comments(user, gallery, work)

    with side:
        with st.container(border=True):
            st.markdown(
                f"""
                <span class="summary-marker"></span>
                <div class="sum-title">Metadata by FanMeta</div>
                <div class="sum-box">{summary_html(work)}</div>
                <hr class="sum-line">
                """,
                unsafe_allow_html=True,
            )
            _render_like(user, gallery, work)
            if user and user["uid"] == work.get("owner_uid"):
                if st.button("Unpublish", key="work_unpublish", use_container_width=True):
                    confirm_unpublish(user, gallery, work["work_id"], title)


def render(user: dict[str, str] | None, gallery: GalleryStore | None) -> None:
    if gallery is None:
        st.title("Story Gallery")
        st.error("Firestore belum dikonfigurasi. Galeri tidak tersedia."); return
    if toast := st.session_state.pop("gallery_toast", None):
        st.toast(toast, icon=":material/check_circle:")
    work_id = st.session_state.get("gallery_work")
    if st.session_state.get("page") == "work" and work_id:
        _render_work(user, gallery, work_id)
    else:
        _render_list(gallery)
