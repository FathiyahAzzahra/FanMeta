"""Bahasa tampilan (English / Bahasa Indonesia) dan tema (light / dark).

Pilihan disimpan di session_state dan di alamat halaman (?lang=id&theme=dark), jadi tetap
teringat setelah halaman di-refresh. Label metadata AO3 (rating, warning, tag) SENGAJA tidak
diterjemahkan karena harus sama persis dengan istilah resmi AO3.

Pemakaian: ``tr("English text", "Teks Indonesia")``.
"""
from datetime import datetime, timezone
from typing import Any

import streamlit as st
from streamlit import runtime

LANGS = ("en", "id")
THEMES = ("light", "dark")
_MONTHS_ID = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")


def _read(key: str, param: str, options: tuple[str, ...]) -> str:
    if not runtime.exists():  # di luar Streamlit (mis. skrip tes) pakai bawaan tanpa peringatan
        return options[0]
    try:
        value = st.session_state.get(key)
        if value not in options:
            value = st.query_params.get(param)
            value = value if value in options else options[0]
            st.session_state[key] = value
        return value
    except Exception:  # noqa: BLE001 - di luar Streamlit (mis. tes) pakai bawaan
        return options[0]


def lang() -> str:
    return _read("ui_lang", "lang", LANGS)


def theme() -> str:
    return _read("ui_theme", "theme", THEMES)


def is_id() -> bool:
    return lang() == "id"


def tr(en: str, id_: str) -> str:
    """Pilih teks sesuai bahasa tampilan."""
    return id_ if is_id() else en


def _remember(param: str, value: str, default: str) -> None:
    if value == default:
        st.query_params.pop(param, None)  # alamat tetap bersih untuk pilihan bawaan
    else:
        st.query_params[param] = value


def set_lang(value: str) -> None:
    if value in LANGS:
        st.session_state["ui_lang"] = value
        _remember("lang", value, LANGS[0])


def toggle_theme() -> None:
    value = "light" if theme() == "dark" else "dark"
    st.session_state["ui_theme"] = value
    _remember("theme", value, THEMES[0])


def num(n: int) -> str:
    """Angka dengan pemisah ribuan: 18,594 (EN) / 18.594 (ID)."""
    text = f"{int(n):,}"
    return text.replace(",", ".") if is_id() else text


def pct(p: float) -> str:
    """Peluang 0–1 sebagai persen satu desimal: 69.6% (EN) / 69,6% (ID). Jangan dipakai untuk CSS."""
    text = f"{p * 100:.1f}%"
    return text.replace(".", ",") if is_id() else text


def language_label(value: str) -> str:
    """Nilai bahasa yang disimpan ("Bahasa Indonesia"/"Bahasa Inggris") -> teks tampilan."""
    names = {"Bahasa Indonesia": ("Indonesian", "Indonesia"), "Bahasa Inggris": ("English", "Inggris")}
    en, id_ = names.get(value, (value, value))
    return tr(en, id_)


def _local(value: Any) -> datetime | None:
    if hasattr(value, "to_datetime"):
        value = value.to_datetime()
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone()


def format_date(value: Any, with_time: bool = False) -> str:
    """'18 Oct 2026' / '18 Okt 2026' (opsional dengan jam)."""
    local = _local(value)
    if local is None:
        return tr("Date not available", "Tanggal tidak tersedia")
    month = _MONTHS_ID[local.month - 1] if is_id() else f"{local:%b}"
    text = f"{local.day:02d} {month} {local.year}"
    if with_time:
        text += f", {local:%H.%M}" if is_id() else f", {local:%H:%M}"
    return text


def format_relative(value: Any) -> str:
    """'today, 10:36' / 'hari ini, 10.36', 'yesterday' / 'kemarin', atau tanggal."""
    local = _local(value)
    if local is None:
        return "-"
    days = (datetime.now().astimezone().date() - local.date()).days
    if days == 0:
        return tr(f"today, {local:%H:%M}", f"hari ini, {local:%H.%M}")
    if days == 1:
        return tr("yesterday", "kemarin")
    return format_date(local)


def clock(value: Any) -> str:
    local = _local(value)
    if local is None:
        return ""
    return f"{local:%H.%M}" if is_id() else f"{local:%H:%M}"
