"""Proses terpisah untuk analisis CPU di Space ZeroGPU (dijalankan oleh app.py, bukan oleh Gradio).

Kenapa terpisah: ZeroGPU membuat worker GPU dengan menyalin (fork) proses utama. Setelah proses utama
dipakai menjalankan model di CPU, worker GPU yang dibuat sesudahnya gagal dengan
"RuntimeError: No CUDA GPUs are available" (diuji 3 Nov: GPU, GPU, CPU, CPU, lalu semua GPU gagal).
Jadi analisis CPU dijalankan di sini dan proses utama hanya menyimpan model GPU.

Protokol: satu baris JSON per permintaan di stdin ({"text", "language"}), satu baris jawaban di stdout
yang diawali MARK ({"result"} atau {"error"}). Baris stdout lain (log library) diteruskan ke log Space.
"""
import json
import sys
from pathlib import Path

MARK = "@@fanmeta-cpu@@"

ROOT = Path(__file__).resolve().parent
if not (ROOT / "src").is_dir():  # dites di laptop: pakai folder aplikasi (induk dari hf_space/)
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))


def send(message: dict) -> None:
    # hasil predictor berisi angka numpy; tolist() mengubahnya menjadi float/list Python biasa
    print(MARK + json.dumps(message, default=lambda value: value.tolist()), flush=True)


def main() -> None:
    from src.ml.predictor import FanMetaPredictor

    predictor = FanMetaPredictor(device="cpu")
    send({"ready": True})
    for line in sys.stdin:
        request = json.loads(line)
        try:
            send({"result": predictor.predict(request["text"], source_language=request["language"])})
        except Exception as error:
            send({"error": f"{type(error).__name__}: {error}"})


if __name__ == "__main__":
    main()
