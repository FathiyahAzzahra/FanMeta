"""Analisis Workspace: jalankan model per bab di latar belakang + tampilkan metadata cerita gabungan."""
import html
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

from src.firestore_history import FirestoreHistory, probs_to_rows
from src.predictor import FanMetaPredictor
from src.rich_text import html_to_text
from src.workspace_metadata import NONE_WARNING, TOP_TAGS, chapter_state, needs_analysis, text_hash
from src.workspace_store import WorkspaceStore
from src.ui.components import BADGE_TONE, badge, icon, icon_box, rating_badge


def start_job(user: dict[str, str], work: dict[str, Any], chapters: list[dict[str, Any]],
              load_predictor: Callable[[], FanMetaPredictor], history_store: FirestoreHistory,
              store: WorkspaceStore) -> dict[str, Any]:
    """Analisis bab satu per satu di thread latar. Hasil tiap bab langsung disimpan oleh thread,
    jadi tetap aman walaupun penulis pindah halaman."""
    is_id = work.get("language") == "Bahasa Indonesia"
    items = [{
        "chapter_id": c["chapter_id"], "number": c["number"], "title": str(c.get("title") or ""),
        "content_html": c.get("content_html", ""), "word_count": int(c.get("word_count") or 0),
        "stage": "waiting", "rating": None, "error": None, "completed_at": None,
    } for c in chapters]
    job: dict[str, Any] = {
        "work_id": work["work_id"], "items": items, "done": False, "started_at": datetime.now(timezone.utc),
        "title": str(work.get("title") or "Untitled"), "fandom": str(work.get("fandom") or ""), "translate": is_id,
    }
    work_title = str(work.get("title") or "Untitled")

    def run() -> None:
        try:
            predictor = None
            for item in items:
                try:
                    item["stage"] = "loading"
                    predictor = predictor or load_predictor()
                    text = html_to_text(item["content_html"])

                    def on_stage(name: str, item: dict[str, Any] = item) -> None:
                        if name in ("translating", "classifying"):
                            item["stage"] = name
                    item["stage"] = "translating" if is_id else "classifying"
                    result = predictor.predict(text, source_language="id" if is_id else "en", on_stage=on_stage)

                    item["stage"] = "saving"
                    label = f"Chapter {item['number']}" + (f": {item['title']}" if item["title"] else "")
                    analysis_id = history_store.save_analysis(
                        firebase_uid=user["uid"], email=user.get("email", ""),
                        title=f"{work_title} · {label}", language=work.get("language", "Bahasa Inggris"),
                        story=text, rating=result["rating"], warnings=result["warnings"], tags=result["tags"],
                        rating_probabilities=result.get("rating_probabilities"),
                        warning_probabilities=result.get("warning_probabilities"),
                        tag_probabilities=result.get("tag_probabilities"),
                        segments_english=result.get("segments_english"),
                        extra={"source": "workspace", "work_id": work["work_id"], "work_title": work_title,
                               "chapter_id": item["chapter_id"], "chapter_number": item["number"],
                               "chapter_title": item["title"]},
                    )
                    store.set_chapter_analysis(user["uid"], work["work_id"], item["chapter_id"], {
                        "analysis_id": analysis_id,
                        "rating": result["rating"], "warnings": list(result["warnings"]), "tags": list(result["tags"]),
                        "tag_probabilities": probs_to_rows(result.get("tag_probabilities") or {}),
                        "rating_probabilities": probs_to_rows(result.get("rating_probabilities") or {}),
                        "analyzed_at": datetime.now(timezone.utc),
                        "text_hash": text_hash(item["content_html"]), "word_count": item["word_count"],
                    })
                    item["rating"] = result["rating"]
                    item["completed_at"] = datetime.now(timezone.utc)
                    item["stage"] = "done"
                except Exception as error:  # noqa: BLE001 - bab lain tetap dianalisis
                    item["stage"] = "error"
                    item["error"] = str(error) or "unknown error"
        finally:
            job["done"] = True

    thread = threading.Thread(target=run, daemon=True)
    add_script_run_ctx(thread, get_script_run_ctx())
    thread.start()
    return job


# urutan tahap per bab: 1 = baca bab, 2 = terjemahkan (hanya Indonesia), 3 = analisis, 4 = selesai
_STAGE_STEP = {"waiting": 0, "loading": 1, "translating": 2, "classifying": 3, "saving": 3, "done": 4, "error": 0}
_STAGE_DONE = {"waiting": 0, "loading": .1, "translating": .35, "classifying": .7, "saving": .9, "done": 1, "error": 1}
_STAGE_BADGE = {"waiting": ("Waiting", "grey"), "loading": ("Reading", "violet"), "translating": ("Translating", "violet"),
                "classifying": ("Analyzing", "violet"), "saving": ("Saving", "violet"), "done": ("Done", "green"),
                "error": ("Failed", "red")}
_CHECK = '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>'


def _clock(value: Any) -> str:
    return value.astimezone().strftime("%H:%M") if isinstance(value, datetime) else ""


def _svg(paths: str, size: int = 14) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{paths}</svg>')


def _activity(item: dict[str, Any] | None, translate: bool) -> str:
    if item is None:
        return "Starting…"
    ch = f"Chapter {item['number']}"
    return {"loading": f"Reading {ch} (the first run also loads the model)",
            "translating": f"Translating {ch} with NLLB-200",
            "classifying": f"Analyzing {ch}", "saving": f"Saving results for {ch}"}.get(item["stage"], "")


def _chapter_row(item: dict[str, Any], previous: dict[str, Any] | None, translate: bool) -> str:
    stage = item["stage"]
    step = _STAGE_STEP[stage]
    words = f"{item['word_count']:,} words"
    if stage == "done":
        meta = f"{words} · Completed at {_clock(item['completed_at'])}"
    elif stage == "error":
        meta = f"{words} · {item['error']}"
    elif stage == "translating":
        meta = f"{words} · Indonesian → English · NLLB-200"
    elif stage == "waiting":
        meta = f"{words} · " + (f"Starts after Chapter {previous['number']}" if previous else "Starting soon")
    else:
        meta = words
    state = {"done": "done", "error": "error", "waiting": "waiting"}.get(stage, "active")
    lead = {"done": icon("check", 18), "error": "!",
            "waiting": icon("clock", 18)}.get(state, "")
    steps = [("Read chapter", 1)] + ([("Translate", 2)] if translate else []) + [("Analyze", 3)]
    step_html = ""
    for name, n in steps:
        st_state = "done" if step > n else ("active" if step == n else "waiting")
        mark = _svg(_CHECK) if st_state == "done" else '<span class="ap-ring"></span>'
        step_html += f'<span class="ap-step ap-step-{st_state}">{mark}{name}</span>'
    if stage == "done" and item.get("rating"):
        step_html += rating_badge(item["rating"])
    label, tone = _STAGE_BADGE[stage]
    title = f"Ch {item['number']}" + (f" · {item['title']}" if item["title"] else "")
    return (f'<div class="ap-row ap-{state}"><span class="ap-lead">{lead}</span><div class="ap-main">'
            f'<div class="ap-head"><div><div class="ap-title">{html.escape(title)}</div>'
            f'<div class="ap-meta">{html.escape(meta)}</div></div>{badge(label, tone)}</div>'
            f'<div class="ap-steps">{step_html}</div></div></div>')


@st.fragment(run_every=1.0)
def render_progress(job: dict[str, Any], on_finish: Callable[[], None]) -> None:
    if st.session_state.get("ws_view") != "analyzing":
        st.rerun()  # penulis pindah halaman lewat breadcrumb/tombol: tampilkan halaman baru
    items = job["items"]
    translate = bool(job.get("translate"))
    finished = sum(1 for i in items if i["stage"] in ("done", "error"))
    running = next((i for i in items if i["stage"] not in ("waiting", "done", "error")), None)
    percent = int(100 * sum(_STAGE_DONE[i["stage"]] for i in items) / max(len(items), 1))
    errors = [i for i in items if i["stage"] == "error"]
    if not job["done"]:
        status = badge("Analysis in progress", "violet")
    else:
        status = badge("Finished with errors", "red") if errors else badge("Analysis complete", "green")

    st.markdown(
        f'<div class="ap-top"><div><h1 class="pg-h1">Reading between your lines.</h1>'
        f'<p class="pg-sub">We\'re analyzing your chapters to find the metadata that fits your story.</p></div>'
        f"{status}</div>", unsafe_allow_html=True)

    started = job.get("started_at")
    started_text = started.astimezone().strftime("%d %b %Y, %H:%M") if isinstance(started, datetime) else "-"
    n = len(items)
    info = " · ".join(x for x in (job.get("fandom"), f"{n} chapter" + ("" if n == 1 else "s"),
                                  f"{sum(i['word_count'] for i in items):,} words") if x)
    activity = "All chapters analyzed" if job["done"] else _activity(running, translate)
    rows = "".join(_chapter_row(item, items[k - 1] if k else None, translate) for k, item in enumerate(items))
    side_steps = ([("languages", "Translate", "NLLB-200 prepares the text.")] if translate else []) + [
        ("scan", "Find the signals", "Ratings, warnings, and story themes."),
        ("layers", "Bring it together", "One story view with chapter sources."),
    ]
    intro = ("We translate your Indonesian prose for analysis. Your original chapter text stays exactly as you "
             "wrote it." if translate else
             "FanMeta reads your English prose directly. Your chapter text stays exactly as you wrote it.")

    main, side = st.columns([2.6, 1], gap="medium")
    with main:
        st.markdown(
            f"""
            <div class="ap-card">
              <div class="ap-story">{icon_box("sparkles", 22)}<div class="ap-story-t">
                <div class="ap-story-title">{html.escape(job.get("title") or "Untitled")}</div>
                <div class="ap-story-meta">{html.escape(info)}</div></div>
                <div class="ap-percent">{percent}%</div></div>
              <div class="ap-bar"><div style="width:{percent}%"></div></div>
              <div class="ap-status"><b>{finished} of {n} chapter{"" if n == 1 else "s"} complete</b>
                <span>{html.escape(activity)}</span></div>
              <div class="ap-foot">Analysis of {n} chapter{"" if n == 1 else "s"} · Started {started_text}</div>
            </div>
            <div class="ap-card"><div class="ap-card-title">Chapter-by-chapter progress</div>{rows}</div>
            """,
            unsafe_allow_html=True,
        )
    with side:
        steps = "".join(f'<div class="ap-side-step">{icon(i, 18, "#635BFF")}<div><b>{t}</b><span>{d}</span></div></div>'
                        for i, t, d in side_steps)
        st.markdown(
            f"""
            <div class="ap-side"><div class="ap-side-title">A careful read takes a moment</div>
              <p>{intro}</p><hr>{steps}</div>
            <div class="ap-note">{icon("info", 20, "#635BFF")}<div class="ap-note-title">Not the final results yet</div>
              <p>The combined story rating, warnings, and tags will appear after all {n} chapter{"" if n == 1 else "s"}
              finish. Completed results are saved in your Analysis Log.</p></div>
            """,
            unsafe_allow_html=True,
        )

    if job["done"]:
        if errors:
            st.error(f"{len(errors)} bab gagal dianalisis. Bab lain sudah tersimpan.")
        else:
            st.session_state["ws_toast"] = f"{n} bab selesai dianalisis."
            on_finish()
            st.rerun()


# ---------------------------------------------------------------- tampilan metadata
_STATE_LABEL = {"analyzed": "Analyzed", "changed": "Changed", "new": "Not analyzed", "empty": "Empty"}


def state_badge(state: str) -> str:
    return badge(_STATE_LABEL.get(state, state), BADGE_TONE.get(_STATE_LABEL.get(state, "").lower(), "grey"))


def chapter_status_html(chapter: dict[str, Any]) -> str:
    """Badge rating terakhir + status analisis bab (dipakai di beberapa tempat)."""
    state = chapter_state(chapter)
    analysis = chapter.get("analysis") or {}
    return (rating_badge(analysis["rating"]) if analysis.get("rating") else "") + state_badge(state)


def _from(numbers: list[int]) -> str:
    return ("from " + ", ".join(f"Ch {n}" for n in numbers)) if numbers else ""


def render_story_metadata(work: dict[str, Any], chapters: list[dict[str, Any]], on_analyze: Callable[[], None]) -> None:
    meta = work.get("metadata")
    pending = needs_analysis(chapters)
    writable = [c for c in chapters if chapter_state(c) != "empty"]
    analyzed = sum(1 for c in writable if chapter_state(c) == "analyzed")
    with st.container(border=True):
        progress = badge(f"{analyzed} / {len(writable)} analyzed", "green" if writable and analyzed == len(writable) else "grey")
        st.markdown(f'<span class="ws-section-marker"></span><div class="card-title">Story Metadata{progress}</div>',
                    unsafe_allow_html=True)
        if not meta:
            st.markdown('<p class="ws-muted sm-empty">Not analyzed yet. Write a chapter, then analyze it to get the '
                        "story's metadata.</p>", unsafe_allow_html=True)
        else:
            warn_from = {row["warning"]: row["chapters"] for row in meta.get("warning_from") or []}
            warnings = meta.get("warnings") or [NONE_WARNING]
            warn_html = "".join(
                f'<span class="sm-warn">{badge(w, "orange")}<small>{_from(warn_from.get(w, []))}</small></span>'
                for w in warnings
            )
            details = meta.get("tag_details") or []

            def tag_html(rows: list[dict[str, Any]]) -> str:
                return "".join(
                    f'<span class="sm-tag" title="Average confidence {r["mean_prob"] * 100:.0f}%">{html.escape(r["tag"])}'
                    f'<b>{"Ch " + ", ".join(str(n) for n in r["chapters"])}</b></span>' for r in rows
                ) or '<span class="ws-muted">No tags</span>'
            st.markdown(
                f"""
                <div class="sm-rating"><div><div class="sm-label">Combined content rating</div>
                  <div class="sm-hint">Highest rating across all analyzed chapters</div></div>
                  <div class="sm-rating-val">{rating_badge(meta["rating"])}<small>{_from(meta.get("rating_from") or [])}</small></div></div>
                <hr class="sm-line">
                <div class="sm-sub">Archive Warnings</div><div class="sm-row">{warn_html}</div>
                <div class="sm-sub">Additional Tags</div><div class="sm-row">{tag_html(details[:TOP_TAGS])}</div>
                """,
                unsafe_allow_html=True,
            )
            if len(details) > TOP_TAGS:
                with st.expander(f"Show {len(details) - TOP_TAGS} more tag(s)"):
                    st.markdown(f'<div class="sm-row">{tag_html(details[TOP_TAGS:])}</div>', unsafe_allow_html=True)

        foot_l, foot_r = st.columns([1.6, 1], vertical_alignment="center")
        with foot_l:
            if pending:
                changed = sum(1 for c in pending if chapter_state(c) == "changed")
                new = len(pending) - changed
                parts = ([f"{new} new"] if new else []) + ([f"{changed} changed"] if changed else [])
                note = f'<span class="sm-note-warn">{" and ".join(parts)} chapter(s) need analysis.</span>'
            elif meta:
                note = "Suggestions are up to date. Review them before publishing on AO3."
            else:
                note = "Add text to a chapter to analyze it."
            st.markdown(f'<div class="sm-foot">{note}</div>', unsafe_allow_html=True)
        with foot_r:
            with st.container(horizontal=True, horizontal_alignment="right"):
                st.button("Analyze changed chapters", key="wsa_all", type="primary", icon=":material/auto_awesome:",
                          disabled=not pending, on_click=on_analyze)
