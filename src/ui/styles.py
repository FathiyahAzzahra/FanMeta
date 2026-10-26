"""Shared visual language derived from the FanMeta mockups.

CSS-nya ada di folder ``css/``: ``theme.css`` (mode terang + struktur halaman) dan
``dark_widgets.css`` (tambahan mode gelap untuk widget bawaan Streamlit). File ini hanya
memuat CSS tersebut dan menyusun warna mode gelap.
"""

from pathlib import Path

import streamlit as st

from src.core.i18n import theme

_CSS_DIR = Path(__file__).resolve().parent / "css"


def _read_css(name: str) -> str:
    return (_CSS_DIR / name).read_text(encoding="utf-8")


# CSS utama. Warna ditulis var(--<jenis>-<hex>, <warna asli>), lihat MODE GELAP di bawah.
_THEME_CSS = "\n<style>\n" + _read_css("theme.css") + "</style>\n"


# ===== MODE GELAP =====
# Semua warna di theme.css ditulis sebagai var(--<jenis>-<hex>, <warna asli>):
#   bg = latar, fg = teks, bd = garis. Mode terang tidak mengisi variabel ini (pakai warna asli),
#   mode gelap mengisinya dengan warna di bawah. Warna yang tidak ada di sini tetap sama di kedua mode.
_DARK_COLORS = {
    "bg": {
        "#181a2e": ("ffffff",),
        "#0f1020": ("f7f8fc",),
        "#1f2238": ("f8f9fc", "fafbfd", "fafaff", "f9fafc", "f7f6ff", "f6f7fb", "f5f5fb", "f5f4ff", "f4f5fa", "eef2f8"),
        "#262a43": ("f1f3f7", "f3f4f6", "eef0f5", "e5e7eb"),
        "#2a2752": ("efeeff", "ebeaff", "ede9fe"),
        "#3a2a17": ("ffefdc", "fff3e5", "fff7ed", "fff0e8", "fef3c7"),
        "#3b1d24": ("fff0f1", "fee2e2", "fff1f2"),
        "#172a45": ("eff6ff", "edf7ff", "e0f2fe", "dbeafe"),
        "#15322a": ("dcfce7", "eaf7f1"),
        "#4a4f70": ("c9ccd6",),
    },
    "fg": {
        "#e8e9f5": ("202033", "111827", "1f2937"),
        "#c9cbe0": ("374151", "3c3c4d", "4b5563"),
        "#a3a6c2": ("505365", "6b6e80", "5b6475"),
        "#8b8fae": ("6b7280", "8a8fa3", "9ca3af", "94a3b8"),
        "#f5b06a": ("b4470f", "b86010", "c2410c", "b45309"),
        "#ff8a96": ("d04452", "dc2626", "b91c1c", "e11d48"),
        "#7fb0ff": ("2563eb", "1d4ed8", "0369a1", "2563a8"),
        "#6fd3a8": ("237c64", "15803d", "16a34a"),
        "#a5a0ff": ("635bff", "5b54e6", "4d46be", "5b5fef", "6d28d9"),
    },
    "bd": {
        "#3a3f63": ("d9d7e5", "cbd5e1"),
        "#2c3050": ("eeedf4", "e5e7eb", "eeeff3"),
        "#4a4590": ("c7c3ff", "dcd9ff", "cfd2ff", "7c74ff"),
        "#5a4020": ("fed7aa",),
        "#5a2a33": ("fecdd3", "fecaca"),
        "#181a2e": ("ffffff",),
    },
}
_DARK_ROOT = ("--ink:#e8e9f5; --muted:#a3a6c2; --line:#2c3050; --surface:#181a2e; --canvas:#0f1020; "
              "--violet:#7c75ff; --violet-dark:#6b63f0; --violet-soft:#2a2752;")

# komponen bawaan Streamlit yang warnanya diambil dari tema terang di config.toml
_DARK_WIDGETS = "\n" + _read_css("dark_widgets.css")


def _dark_css() -> str:
    tokens = " ".join(f"--{ns}-{hex_}:{dark};" for ns, colors in _DARK_COLORS.items()
                      for dark, light in colors.items() for hex_ in light)
    return f"<style>:root {{ {_DARK_ROOT} {tokens} }}{_DARK_WIDGETS}</style>"


_DARK_CSS = _dark_css()


def apply_theme() -> None:
    # foto latar login dipasang di auth_layout.art_panel (hanya di halaman login/register)
    st.markdown(_THEME_CSS, unsafe_allow_html=True)
    # slot CSS gelap SELALU ada (kosong di mode terang). Kalau elemen ini hanya muncul di mode gelap,
    # semua elemen di bawahnya bergeser satu posisi saat ganti tema, dan halaman sempat "melompat".
    st.markdown(_DARK_CSS if theme() == "dark" else "<style></style>", unsafe_allow_html=True)
