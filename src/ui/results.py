"""Metadata recommendation results view (juga dipakai halaman detail riwayat)."""
import html
import json
from typing import Any

import streamlit as st

from src.firestore_history import FirestoreHistory

from src import fanmeta_utils as U
from src.ui.components import navigate

NONE_WARNING = "no archive warnings apply"

_RATING_DESC = {
    "general audiences": "Suitable for all ages. No mature or explicit material detected.",
    "teen and up audiences": "May contain mild language and thematic elements suitable for teenagers and up.",
    "mature": "Contains content intended for adult readers, such as strong violence or sexual themes.",
    "explicit": "Contains graphic sexual or violent content intended for adult readers only.",
}

_SVG = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{p}</svg>'
_ICON_SHIELD = _SVG.format(c="#5b54e6", p='<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z"/>')
_ICON_ALERT = _SVG.format(c="#9a3412", p='<path d="M12 3l10 18H2L12 3z"/><path d="M12 10v5M12 18v.01"/>')
_ICON_TAG = _SVG.format(c="#5b54e6", p='<path d="M20 12l-8 8-9-9V3h8l9 9z"/><circle cx="7.5" cy="7.5" r="1"/>')

_THRESHOLD_NOTE = (
    '<p class="cb-note">Highlighted labels passed their decision threshold '
    "(tuned on validation data), so a label below 50% can still be recommended.</p>"
)
_NO_PROB_NOTE = '<p class="cb-note">Confidence scores were not stored for this older analysis.</p>'
_LOW_RATIO = 0.6  # rasio kata EN/ID di bawah ini dianggap terjemahan terlalu pendek


def _pct(value: float | None) -> str:
    return f"{value * 100:.1f}% Confidence" if value is not None else ""


def _bars(probs: dict[str, float], chosen: list[str], order: list[str] | None = None) -> str:
    """Bar persen keyakinan per label; label yang direkomendasikan diberi warna."""
    labels = order if order is not None else list(probs)
    rows = []
    for label in labels:
        p = float(probs.get(label, 0))
        cls = "cb-row cb-on" if label in chosen else "cb-row"
        rows.append(
            f'<div class="{cls}"><span class="cb-label">{html.escape(label)}</span>'
            f'<span class="cb-track"><span style="width:{p * 100:.1f}%"></span></span>'
            f'<span class="cb-val">{p * 100:.1f}%</span></div>'
        )
    return f'<div class="cb-list">{"".join(rows)}</div>'


def split_warnings(result: dict[str, Any]) -> list[str]:
    # "No Archive Warnings Apply" adalah label model, bukan warning sungguhan
    return [w for w in result.get("warnings") or [] if w.strip().lower() != NONE_WARNING]


def sorted_tags(result: dict[str, Any]) -> list[str]:
    t_probs = result.get("tag_probabilities") or {}
    return sorted(result.get("tags") or [], key=lambda t: t_probs.get(t, 0), reverse=True)


def summary_rows(result: dict[str, Any]) -> list[tuple[str, str]]:
    warnings = split_warnings(result)
    tags = sorted_tags(result)
    return [
        ("Rating", str(result.get("rating") or "-")),
        ("Archive Warnings", ", ".join(warnings) if warnings else "No Archive Warnings Apply"),
        ("Additional Tags", ", ".join(tags) if tags else "-"),
    ]


def summary_html(result: dict[str, Any]) -> str:
    return "".join(
        f'<div class="sum-row"><span>{label}</span><b>{html.escape(value)}</b></div>'
        for label, value in summary_rows(result)
    )


def copy_button(result: dict[str, Any]) -> None:
    text = "\n".join(f"{label}: {value}" for label, value in summary_rows(result))
    payload = json.dumps(text)
    st.iframe(
        f"""<!doctype html>
        <style>
        html,body{{margin:0;padding:0;overflow:hidden;background:transparent}}
        button{{position:fixed;inset:0;width:100%;height:100%;border:0;border-radius:8px;background:#635bff;
        color:#fff;font:600 15px Inter,'Source Sans Pro',sans-serif;cursor:pointer}}
        button:hover{{background:#5149db}}
        </style>
        <button id="c">Copy Metadata to Clipboard</button>
        <script>
        const t = {payload}, b = document.getElementById('c');
        b.onclick = async () => {{
            try {{ await navigator.clipboard.writeText(t); }}
            catch (e) {{
                const a = document.createElement('textarea'); a.value = t;
                document.body.appendChild(a); a.select(); document.execCommand('copy'); a.remove();
            }}
            b.textContent = 'Copied!'; setTimeout(() => b.textContent = 'Copy Metadata to Clipboard', 1800);
        }};
        </script>
        """,
        height=42,
    )


def _render_translation(story: str, segments_en: list[str]) -> None:
    """Segmen Indonesia berdampingan dengan hasil terjemahan NLLB-nya."""
    segments_id = U.split_segments(U.preprocess_text(story)) if story else []
    if len(segments_id) != len(segments_en):
        segments_id = [""] * len(segments_en)

    with st.expander(f"View English translation (NLLB-200) · {len(segments_en)} segments"):
        st.markdown(
            '<p class="cb-note">The model was trained on English text, so Indonesian drafts are translated '
            "segment by segment (200 words, 50-word overlap) before classification. The ratio compares "
            f"English to Indonesian word counts; segments below {_LOW_RATIO:.1f} may have lost content "
            "during translation.</p>",
            unsafe_allow_html=True,
        )
        for i, (seg_id, seg_en) in enumerate(zip(segments_id, segments_en), start=1):
            n_id, n_en = len(seg_id.split()), len(seg_en.split())
            ratio = n_en / n_id if n_id else None
            low = ratio is not None and ratio < _LOW_RATIO
            ratio_html = (
                f'<span class="tr-ratio{" tr-low" if low else ""}">ratio {ratio:.2f}</span>'
                if ratio is not None else ""
            )
            st.markdown(
                f'<div class="tr-head">Segment {i} <span>{n_id} → {n_en} words</span>{ratio_html}</div>',
                unsafe_allow_html=True,
            )
            col_id, col_en = st.columns(2, gap="small")
            with col_id:
                st.markdown(
                    f'<div class="tr-box"><small>Indonesian</small>{html.escape(seg_id) or "-"}</div>',
                    unsafe_allow_html=True,
                )
            with col_en:
                st.markdown(
                    f'<div class="tr-box tr-en"><small>English (NLLB)</small>{html.escape(seg_en) or "-"}</div>',
                    unsafe_allow_html=True,
                )


def render_result_cards(result: dict[str, Any], story: str = "") -> None:
    """Kartu rating, warning, dan tags beserta bar persen keyakinan."""
    rating = str(result.get("rating") or "-")
    all_warnings = list(result.get("warnings") or [])
    warnings = split_warnings(result)
    tags = sorted_tags(result)
    r_probs = result.get("rating_probabilities") or {}
    w_probs = result.get("warning_probabilities") or {}
    t_probs = result.get("tag_probabilities") or {}

    # --- Content Rating: 4 kelas ---
    desc = _RATING_DESC.get(rating.strip().lower(), "")
    rating_bars = _bars(r_probs, [rating], order=list(U.RATINGS)) if r_probs else _NO_PROB_NOTE
    st.markdown(
        f"""
        <div class="rc-card">
            <div class="rc-head"><span class="rc-title">{_ICON_SHIELD}Content Rating</span><small>{_pct(r_probs.get(rating))}</small></div>
            <div class="rc-body"><span class="rc-pill rc-rating">{html.escape(rating)}</span>
            <p>{html.escape(desc)}</p></div>
            {rating_bars}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Archive Warning: 4 label ---
    if warnings:
        w_pills = "".join(f'<span class="rc-pill rc-warn">{html.escape(w)}</span>' for w in warnings)
        w_text = "Review these warnings before publishing your work."
    else:
        w_pills = '<span class="rc-pill rc-warn">No Archive Warnings Apply</span>'
        w_text = "No explicit triggers identified. Ready for archival tagging."
    warn_bars = _bars(w_probs, all_warnings, order=list(U.WARNING_LABELS)) + _THRESHOLD_NOTE if w_probs else _NO_PROB_NOTE
    st.markdown(
        f"""
        <div class="rc-card">
            <div class="rc-head"><span class="rc-title">{_ICON_ALERT}Archive Warning</span></div>
            <div class="rc-body">{w_pills}<p>{w_text}</p></div>
            {warn_bars}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Additional Tags: tag terpilih + semua 16 tag di expander ---
    if tags:
        tag_body = _bars(t_probs, tags, order=tags) + _THRESHOLD_NOTE if t_probs else (
            '<div class="rc-tags">'
            + "".join(f'<span class="rc-tag">{html.escape(t)}</span>' for t in tags)
            + "</div>" + _NO_PROB_NOTE
        )
    else:
        tag_body = '<span class="empty-copy">Tidak ada label di atas ambang prediksi.</span>'
    st.markdown(
        f"""
        <div class="rc-card">
            <div class="rc-head"><span class="rc-title">{_ICON_TAG}Additional Tags &amp; Tropes</span>
            <small>Recommended for Archive of Our Own (Ao3)</small></div>
            {tag_body}
        </div>
        """,
        unsafe_allow_html=True,
    )
    if t_probs:
        with st.expander(f"View confidence for all {len(t_probs)} tags"):
            order = sorted(t_probs, key=lambda t: t_probs[t], reverse=True)
            st.markdown(_bars(t_probs, tags, order=order), unsafe_allow_html=True)

    segments_en = result.get("segments_english")
    if segments_en:
        _render_translation(story, segments_en)


def render(history_store: FirestoreHistory | None = None) -> None:
    from src.ui.workspace_link import save_to_workspace_dialog  # impor di sini: hindari impor melingkar
    from src.workspace_store import WorkspaceStore
    user = st.session_state.get("firebase_user") or {}
    result = st.session_state.get("analysis_result")
    draft = st.session_state.get("analysis_draft", {})
    if not result:
        navigate("analysis")

    title = html.escape(draft.get("title") or "Untitled Draft")
    main, side = st.columns([2.2, 1], gap="large")

    with main:
        st.markdown(
            f"""
            <span class="results-marker"></span>
            <div class="page-title">Metadata Results <span class="badge-done">Analysis Complete</span></div>
            <p class="page-sub">Generated from your draft: <b>{title}</b></p>
            """,
            unsafe_allow_html=True,
        )
        render_result_cards(result, draft.get("story", ""))

    with side:
        with st.container(border=True):
            st.markdown(
                f"""
                <span class="summary-marker"></span>
                <div class="sum-title">Metadata Summary</div>
                <div class="sum-box">{summary_html(result)}</div>
                <hr class="sum-line">
                """,
                unsafe_allow_html=True,
            )
            copy_button(result)
            if st.button("Analyze Another Story", key="res_another", use_container_width=True):
                st.session_state.pop("analysis_result", None)
                st.session_state.pop("analysis_draft", None)
                navigate("analysis")
            if st.button("View Analysis History", key="res_history", use_container_width=True):
                st.session_state.pop("history_detail", None)
                navigate("history")
            if history_store is not None and st.session_state.get("analysis_id"):
                if st.button("Save to Workspace", key="res_ws", use_container_width=True,
                             help="Turn this analysis into a chapter of a Workspace story."):
                    item = {**result, "analysis_id": st.session_state["analysis_id"], "title": draft.get("title", ""),
                            "story": draft.get("story", ""), "language": draft.get("language", "Bahasa Inggris")}
                    save_to_workspace_dialog(user, WorkspaceStore(history_store.client), history_store, item)

    if st.session_state.pop("history_save_warning", False):
        st.warning("Hasil analisis tersedia, tetapi riwayat tidak dapat disimpan.")
