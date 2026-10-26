"""Mesin model aplikasi: lokal (FanMetaPredictor di laptop) atau Space Hugging Face (ZeroGPU).

Mode Space aktif kalau Streamlit secrets punya bagian [model_api]:

    [model_api]
    space = "ZAaraAa/fanmeta-model-api"
    hf_token = "hf_..."   # token read akun pemilik Space; kuota ZeroGPU dihitung ke akun ini

Tanpa bagian itu, model dijalankan langsung di komputer ini (butuh torch + transformers).
"""
from typing import Any

import streamlit as st


def remote_config() -> dict[str, str | None] | None:
    try:
        section = st.secrets["model_api"]
    except (KeyError, FileNotFoundError):
        return None
    space = str(section.get("space") or "").strip()
    if not space:
        return None
    return {"space": space, "hf_token": str(section.get("hf_token") or "").strip() or None}


def is_remote() -> bool:
    return remote_config() is not None


def engine_device() -> tuple[str, str] | None:
    """Perangkat model lokal: ("gpu", nama kartu) atau ("cpu", ""); None di mode Space (dipilih pengguna).

    Panggil dari thread latar SETELAH load_predictor(): impor torch/transformers sudah selesai di sana,
    jadi halaman (thread utama) tidak ikut menunggu impor yang berat itu.
    """
    if is_remote():
        return None
    from src.ml.predictor import device_summary
    return device_summary()


def load_predictor() -> Any:
    """RemotePredictor (Space) atau FanMetaPredictor (lokal); keduanya punya predict() yang sama."""
    config = remote_config()
    if config is not None:
        from src.ml.remote_predictor import RemotePredictor
        return RemotePredictor(config["space"], config["hf_token"])
    from src.ml.predictor import FanMetaPredictor  # impor di sini: mode Space tidak butuh transformers
    return FanMetaPredictor()
