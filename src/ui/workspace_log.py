"""Log analisis cerita Workspace: setiap analisis + apa yang berubah dibanding sebelumnya.

Perubahan dihitung dari riwayat analisis (users/{uid}/history dengan work_id cerita ini):
- per bab   : dibanding analisis sebelumnya untuk bab yang sama;
- per cerita: metadata gabungan sebelum vs sesudah analisis ini (diputar ulang dari awal).
"""
import html
from typing import Any

import streamlit as st

from src.firestore_history import FirestoreHistory, FirestoreHistoryError
from src.workspace_metadata import NONE_WARNING, aggregate
from src.ui.components import format_created_at, rating_badge

SHOW_FIRST = 10


def _diff(label: str, before: list[str], after: list[str]) -> list[str]:
    added = [x for x in after if x not in before]
    removed = [x for x in before if x not in after]
    lines = []
    if added:
        lines.append(f"{label} added: {', '.join(added)}")
    if removed:
        lines.append(f"{label} removed: {', '.join(removed)}")
    return lines


def _specific(warnings: list[str]) -> list[str]:
    return [w for w in warnings or [] if w != NONE_WARNING]


def build_log(analyses: list[dict[str, Any]], chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """``analyses`` terlama dulu. Kembalikan entri log terbaru dulu."""
    current = {c["chapter_id"]: c for c in chapters}
    latest: dict[str, dict[str, Any]] = {}  # chapter_id -> analisis terakhir saat itu
    entries = []
    for item in analyses:
        cid = item.get("chapter_id")
        snapshot = lambda: [  # noqa: E731 - metadata gabungan pada saat itu
            {"number": a.get("chapter_number") or 0, "analysis": a} for a in latest.values()
        ]
        story_before = aggregate(snapshot())
        previous = latest.get(cid)
        latest[cid] = item
        story_after = aggregate(snapshot())

        chapter_lines, compact = [], []
        short = {r: r.split(" ")[0] for r in ("General Audiences", "Teen And Up Audiences", "Mature", "Explicit")}
        if previous is None:
            compact.append("Initial analysis")
            chapter_lines.append("First analysis of this chapter")
        else:
            if previous.get("rating") != item.get("rating"):
                chapter_lines.append(f"Rating: {previous.get('rating')} → {item.get('rating')}")
                compact.append(f"{short.get(previous.get('rating'), previous.get('rating'))} → "
                               f"{short.get(item.get('rating'), item.get('rating'))}")
            for kind, before, after in (("warning", _specific(previous.get("warnings")), _specific(item.get("warnings"))),
                                        ("tag", previous.get("tags") or [], item.get("tags") or [])):
                added = len([x for x in after if x not in before])
                removed = len([x for x in before if x not in after])
                if added:
                    compact.append(f"+{added} {kind}" + ("s" if added > 1 else ""))
                if removed:
                    compact.append(f"−{removed} {kind}" + ("s" if removed > 1 else ""))
            chapter_lines += _diff("Warning", _specific(previous.get("warnings")), _specific(item.get("warnings")))
            chapter_lines += _diff("Tag", previous.get("tags") or [], item.get("tags") or [])
            if len(chapter_lines) == 0:
                chapter_lines.append("No change compared to the previous analysis")
                compact.append("No change")

        story_lines = []
        if story_before is None:
            story_lines.append(f"Story rating set to {story_after['rating']}")
        else:
            if story_before["rating"] != story_after["rating"]:
                story_lines.append(f"Story rating: {story_before['rating']} → {story_after['rating']}")
            story_lines += _diff("Story warning", _specific(story_before["warnings"]), _specific(story_after["warnings"]))
            story_lines += _diff("Story tag", story_before["tags"], story_after["tags"])

        chapter = current.get(cid)
        if chapter is not None:
            label = f"Chapter {chapter['number']}" + (f": {chapter['title']}" if chapter.get("title") else "")
        else:
            label = f"Chapter {item.get('chapter_number', '?')} (deleted)"
        entries.append({
            "analysis_id": item["analysis_id"], "created_at": item.get("created_at"), "label": label,
            "deleted": chapter is None, "rating": item.get("rating"), "warnings": item.get("warnings") or [],
            "tags": item.get("tags") or [], "words": len(str(item.get("story") or "").split()),
            "chapter_lines": chapter_lines, "story_lines": story_lines, "compact": "; ".join(compact),
            "number": chapter["number"] if chapter is not None else item.get("chapter_number", "?"),
            "title": (chapter.get("title") if chapter is not None else item.get("chapter_title")) or "",
        })
    return list(reversed(entries))


_HEADERS = ("Date", "Chapter", "Rating", "Warnings", "Tags", "Changes")


def _date(value: Any) -> str:
    if hasattr(value, "to_datetime"):
        value = value.to_datetime()
    return value.astimezone().strftime("%d %b, %H:%M") if hasattr(value, "astimezone") else "-"


def _table_html(entries: list[dict[str, Any]]) -> str:
    rows = []
    for e in entries:
        warnings = ", ".join(_specific(e["warnings"])) or NONE_WARNING
        detail = " | ".join(e["story_lines"] + e["chapter_lines"])
        chapter = f"Ch {e['number']}" + (f" · {e['title']}" if e["title"] else "") + (" (deleted)" if e["deleted"] else "")
        rows.append(
            f'<tr class="{"lg-deleted" if e["deleted"] else ""}">'
            f'<td class="lg-date">{_date(e["created_at"])}</td>'
            f'<td class="lg-ch">{html.escape(chapter)}</td>'
            f'<td>{rating_badge(e["rating"] or "")}</td>'
            f"<td>{html.escape(warnings)}</td>"
            f'<td>{html.escape(", ".join(e["tags"])) or "-"}</td>'
            f'<td class="lg-change" title="{html.escape(detail)}">{html.escape(e["compact"])}</td></tr>'
        )
    head = "".join(f"<th>{h}</th>" for h in _HEADERS)
    return f'<div class="lg-wrap"><table class="lg-table"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def render_log(uid: str, work_id: str, chapters: list[dict[str, Any]], history_store: FirestoreHistory | None) -> None:
    with st.container(border=True):
        if history_store is None:
            st.markdown('<div class="card-title">Analysis Log</div><p class="ws-muted">Log tidak tersedia '
                        "(Firestore tidak terhubung).</p>", unsafe_allow_html=True)
            return
        try:
            entries = build_log(history_store.list_for_work(uid, work_id), chapters)
        except FirestoreHistoryError:
            st.error("Log analisis tidak dapat dimuat."); return
        count = f'<span class="lg-count">{len(entries)} record{"" if len(entries) == 1 else "s"}</span>'
        st.markdown(f'<span class="ws-section-marker"></span><div class="card-title lg-title">Analysis Log{count}</div>'
                    '<p class="lg-sub">Every analysis of this story, newest first · Changes compare with the previous '
                    "analysis of the same chapter (hover for details)</p>", unsafe_allow_html=True)
        if not entries:
            st.markdown('<p class="ws-muted">No analyses yet. Every analysis of this story will be recorded here, '
                        "together with what changed.</p>", unsafe_allow_html=True)
            return
        st.markdown(_table_html(entries[:SHOW_FIRST]), unsafe_allow_html=True)
        if len(entries) > SHOW_FIRST:
            with st.expander(f"Show {len(entries) - SHOW_FIRST} older analyses"):
                st.markdown(_table_html(entries[SHOW_FIRST:]), unsafe_allow_html=True)
