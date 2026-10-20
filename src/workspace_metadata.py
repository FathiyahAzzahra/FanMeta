"""Metadata cerita Workspace = gabungan hasil analisis setiap bab.

Aturan penggabungan (disepakati dengan penulis):
- Rating   : rating TERTINGGI di antara bab yang sudah dianalisis (Bab 3 Mature -> cerita Mature).
- Warning  : GABUNGAN warning semua bab. "No Archive Warnings Apply" hanya kalau tidak ada bab
             yang punya warning lain.
- Tag      : GABUNGAN tag semua bab, diurutkan dari yang muncul di paling banyak bab, lalu dari
             rata-rata persen keyakinannya. 5 teratas ditampilkan, sisanya bisa dibuka.
"""

import hashlib
from typing import Any

from src import fanmeta_utils as U
from src.rich_text import html_to_text

NONE_WARNING = "No Archive Warnings Apply"
TOP_TAGS = 5


def text_hash(content_html: str) -> str:
    """Sidik jari teks yang dibaca model. Format (bold/italic) dan spasi tidak memengaruhi."""
    normalized = " ".join(html_to_text(content_html).split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def chapter_state(chapter: dict[str, Any]) -> str:
    """'empty' | 'new' (belum pernah dianalisis) | 'changed' (teks berubah) | 'analyzed'."""
    if not int(chapter.get("word_count") or 0):
        return "empty"
    analysis = chapter.get("analysis")
    if not analysis:
        return "new"
    return "changed" if analysis.get("text_hash") != text_hash(chapter.get("content_html", "")) else "analyzed"


def needs_analysis(chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [c for c in chapters if chapter_state(c) in ("new", "changed")]


def _probs(analysis: dict[str, Any], field: str) -> dict[str, float]:
    rows = analysis.get(field) or []
    if isinstance(rows, dict):
        return rows
    return {row["label"]: float(row["prob"]) for row in rows}


def aggregate(chapters: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Gabungkan hasil analisis bab. ``chapters`` harus punya field 'number' (urutan bab)."""
    analyzed = [c for c in chapters if c.get("analysis")]
    if not analyzed:
        return None

    # rating tertinggi + bab penyebabnya
    rank = {r: i for i, r in enumerate(U.RATINGS)}
    top = max(rank.get(c["analysis"].get("rating"), 0) for c in analyzed)
    rating = U.RATINGS[top]
    rating_from = [c["number"] for c in analyzed if rank.get(c["analysis"].get("rating"), 0) == top]

    # gabungan warning (urutan mengikuti skema AO3)
    warning_from: dict[str, list[int]] = {}
    for c in analyzed:
        for w in c["analysis"].get("warnings") or []:
            if w != NONE_WARNING:
                warning_from.setdefault(w, []).append(c["number"])
    warnings = [w for w in U.WARNING_LABELS if w in warning_from] or [NONE_WARNING]

    # gabungan tag: urut dari jumlah bab, lalu rata-rata persen keyakinan di bab yang dianalisis
    tag_rows = []
    for tag in U.TAGS:
        from_chapters = [c["number"] for c in analyzed if tag in (c["analysis"].get("tags") or [])]
        if not from_chapters:
            continue
        mean = sum(_probs(c["analysis"], "tag_probabilities").get(tag, 0.0) for c in analyzed) / len(analyzed)
        tag_rows.append({"tag": tag, "chapters": from_chapters, "mean_prob": round(mean, 4)})
    tag_rows.sort(key=lambda r: (-len(r["chapters"]), -r["mean_prob"]))

    return {
        "rating": rating,
        "rating_from": rating_from,
        "warnings": warnings,
        # daftar, bukan dict: nama label seperti "Rape/Non-Con" tidak aman dipakai sebagai nama field Firestore
        "warning_from": [{"warning": w, "chapters": warning_from[w]} for w in warnings if w != NONE_WARNING],
        "tags": [r["tag"] for r in tag_rows],
        "tag_details": tag_rows,
        "analyzed_chapters": len(analyzed),
        "total_chapters": len(chapters),
    }
