"""Upload kode aplikasi ke Hugging Face Space (SDK: Docker).

Jalankan dari folder ini (setelah `hf auth login`):
    python deploy_hf_space.py

Space menolak file gambar yang di-push lewat git biasa, jadi upload memakai
huggingface_hub (gambar otomatis ditangani). File rahasia dan model TIDAK ikut.
"""

import os
from pathlib import Path

from huggingface_hub import HfApi

SPACE_ID = os.environ.get("FANMETA_SPACE", "ZAaraAa/fanmeta")
ROOT = Path(__file__).resolve().parent

IGNORE_PATTERNS = [
    # Rahasia: JANGAN pernah di-upload (isinya dimasukkan lewat Settings Space > Secrets)
    ".streamlit/secrets.toml",
    ".env",
    "*.env",
    "*serviceAccount*.json",
    "*firebase-adminsdk*.json",
    "*.pem",
    # Model: diunduh dari repo model Hugging Face saat container start
    "checkpoints/*.pt",
    # Tidak dibutuhkan aplikasi
    ".venv/*",
    "venv/*",
    "*__pycache__*",
    "mock_up/*",
    ".claude/*",
    ".agents/*",
    ".vscode/*",
    "*.log",
    # README GitHub diganti space_README.md (berisi pengaturan Space)
    "README.md",
    "space_README.md",
]


def main() -> None:
    api = HfApi()
    api.create_repo(SPACE_ID, repo_type="space", space_sdk="docker", exist_ok=True)
    api.upload_folder(
        repo_id=SPACE_ID,
        repo_type="space",
        folder_path=ROOT,
        ignore_patterns=IGNORE_PATTERNS,
        commit_message="Deploy FanMeta",
    )
    api.upload_file(
        repo_id=SPACE_ID,
        repo_type="space",
        path_or_fileobj=ROOT / "space_README.md",
        path_in_repo="README.md",
        commit_message="Update README Space",
    )
    print(f"Selesai. Buka https://huggingface.co/spaces/{SPACE_ID}")


if __name__ == "__main__":
    main()
