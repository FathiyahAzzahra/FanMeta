"""FanMeta model API: Hugging Face Space (Gradio + ZeroGPU).

Space ini hanya menjalankan model (RoBERTa + LSTM + NLLB). Tampilan, login, dan
riwayat tetap di aplikasi Streamlit, yang memanggil fungsi ``analyze`` lewat gradio_client.

- ``use_gpu=False`` (bawaan): jalan di CPU container Space, TIDAK memakai kuota ZeroGPU.
- ``use_gpu=True``: jalan di GPU ZeroGPU. Kalau kuota habis atau GPU tidak tersedia,
  otomatis pindah ke CPU dan alasannya dikirim balik di ``info``.

Logika prediksi tidak ditulis ulang di sini: ``src/ml/predictor.py`` dan ``src/ml/fanmeta_utils.py``
(satu-satunya sumber aturan) ikut di-upload ke Space oleh script deploy.
"""

print("[fanmeta] app.py dimulai", flush=True)
import spaces  # noqa: E402  ZeroGPU: harus di-import sebelum torch

import os
import re
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import gradio as gr
import torch

ROOT = Path(__file__).resolve().parent
# Di Space, src/ dan checkpoints/ ada di samping app.py.
# Saat dites di laptop, pakai folder aplikasi (induk dari hf_space/).
if not (ROOT / "src").is_dir():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src.ml.predictor import FanMetaPredictor  # noqa: E402

ON_ZERO_GPU = os.getenv("SPACES_ZERO_GPU", "").lower() in ("1", "t", "true")
MAX_GPU_SECONDS = 120


def log(message: str) -> None:
    """Penanda progres di log Space (memuat model tidak mencetak apa pun)."""
    print(f"[fanmeta {time.strftime('%H:%M:%S')}] {message}", flush=True)


log(f"mulai memuat model (ZeroGPU={ON_ZERO_GPU})")
cpu_predictor = FanMetaPredictor(device="cpu")
log("model CPU siap")
gpu_predictor = None
if ON_ZERO_GPU or torch.cuda.is_available():
    gpu_predictor = FanMetaPredictor(device="cuda")
    log("model GPU (RoBERTa + LSTM) siap, memuat NLLB")
    # ZeroGPU: model harus sudah di cuda saat start, bukan dimuat di dalam fungsi GPU.
    gpu_predictor._load_nllb()
    log("NLLB GPU siap")


def _normalize_language(language: str) -> str:
    language = (language or "en").strip().lower()
    if language not in ("en", "id"):
        raise gr.Error("language must be 'en' or 'id'.")
    return language


def gpu_duration(text: str, language: str) -> int:
    """Perkiraan durasi GPU yang diminta ke ZeroGPU (detik). Teks Indonesia lebih lama karena NLLB."""
    words = len(text.split())
    seconds = 30 + words * 0.03 if language == "id" else 15 + words * 0.01
    return int(min(MAX_GPU_SECONDS, seconds))


@spaces.GPU(duration=gpu_duration)
def predict_on_gpu(text: str, language: str) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    result = gpu_predictor.predict(text, source_language=language)
    return result, time.perf_counter() - started


# Contoh pesan ZeroGPU (spaces/zero/client.py):
# "You have exceeded your free ZeroGPU quota (60s requested vs. 25s left). Try again in 3:12:45."
_QUOTA_LEFT = re.compile(r"\((\d+)s requested vs\. (\d+)s left\)")
_RETRY_IN = re.compile(r"Try again in (?:(\d+) days?, )?(\d+):(\d{2}):(\d{2})")


def describe_gpu_error(error: Exception) -> dict[str, Any]:
    """Ubah error ZeroGPU menjadi info yang bisa ditampilkan aplikasi."""
    title = str(getattr(error, "title", "") or "")
    message = str(getattr(error, "message", "") or error)
    is_quota = "quota" in title.lower() or "quota" in message.lower()
    info: dict[str, Any] = {"fallback_reason": "quota" if is_quota else "gpu_error", "message": message}
    if match := _QUOTA_LEFT.search(message):
        info["quota_left_seconds"] = int(match.group(2))
    if match := _RETRY_IN.search(message):
        days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
        wait = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        info["quota_reset_at"] = (datetime.now(timezone.utc) + wait).isoformat(timespec="seconds")
    return info


def analyze(text: str, language: str = "en", use_gpu: bool = False) -> dict[str, Any]:
    """Prediksi metadata. Mengembalikan {"result": hasil predictor, "info": perangkat yang dipakai}."""
    text = (text or "").strip()
    if not text:
        raise gr.Error("Text is empty.")
    language = _normalize_language(language)

    info: dict[str, Any] = {
        "requested": "gpu" if use_gpu else "cpu",
        "device": "cpu",
        "fallback_reason": None,  # None | "gpu_unavailable" | "quota" | "gpu_error"
        "gpu_seconds": 0.0,
        "quota_left_seconds": None,
        "quota_reset_at": None,  # ISO UTC, diisi kalau pesan kuota menyebut waktu reset
        "message": None,
    }

    if use_gpu and gpu_predictor is None:
        info.update(fallback_reason="gpu_unavailable", message="GPU is not available on this server.")
    elif use_gpu:
        try:
            result, seconds = predict_on_gpu(text, language)
            info.update(device="gpu", gpu_seconds=round(seconds, 2))
            return {"result": result, "info": info}
        except Exception as error:  # kuota habis, antrean penuh, atau GPU gagal -> lanjut di CPU
            traceback.print_exc()
            info.update(describe_gpu_error(error))

    result = cpu_predictor.predict(text, source_language=language)
    return {"result": result, "info": info}


demo = gr.Interface(
    fn=analyze,
    inputs=[
        gr.Textbox(label="Story text", lines=12),
        gr.Radio(["en", "id"], value="en", label="Language"),
        gr.Checkbox(value=False, label="Use GPU (ZeroGPU quota)"),
    ],
    outputs=gr.JSON(label="Result"),
    title="FanMeta model API",
    description="AO3 metadata recommendation (Content Rating, Archive Warnings, Additional Tags). "
                "Used by the FanMeta Streamlit app.",
    api_name="analyze",
    flagging_mode="never",
)

if __name__ == "__main__":
    log("menjalankan Gradio")
    demo.launch()
