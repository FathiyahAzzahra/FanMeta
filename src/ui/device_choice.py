"""Pilihan CPU/GPU untuk analisis. Hanya tampil saat model berjalan di Space Hugging Face (ZeroGPU).

GPU adalah pilihan bawaan (lebih cepat); pengguna bisa pindah ke CPU kalau ingin menghemat kuota harian.
"""
from typing import Any

import streamlit as st

from src.services.gpu_quota import GpuQuota, parse_time
from src.core.i18n import clock
from src.ml.model_api import is_remote
from src.ui.components import tr


def _duration(seconds: int) -> str:
    minutes, secs = divmod(max(0, int(seconds)), 60)
    if minutes:
        return tr(f"{minutes} min {secs} s", f"{minutes} mnt {secs} dtk")
    return tr(f"{secs} s", f"{secs} dtk")


def _status(quota: GpuQuota | None) -> dict[str, Any] | None:
    return quota.status() if quota is not None else None


def render(key: str, quota: GpuQuota | None) -> None:
    """Toggle GPU (bawaan) / CPU beserta perkiraan sisa kuota GPU hari ini."""
    if not is_remote():
        return
    status = _status(quota)
    exhausted = bool(status and status["exhausted"])
    reset = clock(status["reset_at"]) if status and status["reset_at"] else ""
    labels = {"gpu": tr("GPU · faster", "GPU · lebih cepat"), "cpu": tr("CPU · saves quota", "CPU · hemat kuota")}
    label = tr("Run the analysis on", "Jalankan analisis dengan")
    if exhausted:
        # toggle tetap tampil tapi terkunci di CPU; key terpisah supaya pilihan pengguna tidak tertimpa
        st.segmented_control(label, ["gpu", "cpu"], format_func=labels.get, default="cpu", required=True,
                             key=f"{key}_locked", disabled=True)
        st.warning(tr(f"Today's GPU quota is used up, so analyses run on CPU (slower). GPU is available again "
                      f"around {reset}.",
                      f"Kuota GPU hari ini habis, jadi analisis memakai CPU (lebih lambat). GPU bisa dipakai lagi "
                      f"sekitar pukul {reset}."))
        return
    st.segmented_control(label, ["gpu", "cpu"], format_func=labels.get, default="gpu", required=True, key=key)
    if status is None:
        return
    note =tr(f"GPU quota left today: about {_duration(status['left_seconds'])} (estimate)",
              f"Sisa kuota GPU hari ini: sekitar {_duration(status['left_seconds'])} (perkiraan)")
    if reset:
        note += tr(f" · resets around {reset}", f" · pulih sekitar pukul {reset}")
    st.caption(note + tr(". CPU does not use the quota.", ". CPU tidak memakai kuota."))


def wants_gpu(key: str, quota: GpuQuota | None) -> bool:
    """True kalau pengguna tidak memilih CPU dan kuota belum tercatat habis."""
    if not is_remote() or st.session_state.get(key, "gpu") != "gpu":
        return False
    status = _status(quota)
    return not (status and status["exhausted"])


def fallback_notice(engine: dict[str, Any] | None) -> str | None:
    """Pesan untuk pengguna kalau GPU diminta tetapi analisis akhirnya memakai CPU."""
    if not engine or engine.get("requested") != "gpu" or engine.get("device") == "gpu":
        return None
    if engine.get("fallback_reason") == "quota":
        reset = parse_time(engine.get("quota_reset_at"))
        when = tr(f" GPU is available again around {clock(reset)}.", f" GPU bisa dipakai lagi sekitar pukul {clock(reset)}.") \
            if reset else ""
        return tr("Today's GPU quota is used up, so this analysis ran on CPU.",
                  "Kuota GPU hari ini habis, jadi analisis ini dijalankan dengan CPU.") + when
    return tr("The GPU is not available right now, so this analysis ran on CPU.",
              "GPU sedang tidak tersedia, jadi analisis ini dijalankan dengan CPU.")
