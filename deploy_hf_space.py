"""Upload model dan Space FanMeta ke Hugging Face.

Login dulu sekali (token WRITE dari https://huggingface.co/settings/tokens):
    .venv\\Scripts\\hf.exe auth login

    python deploy_hf_space.py model    upload 2 file .pt (nama dari checkpoints/06_model_app.json) ke repo model private
    python deploy_hf_space.py space    upload Space Gradio + ZeroGPU (hf_space/ + src/ml/ + checkpoints/06_model_app.json)

Tambahkan --dry-run untuk melihat daftar file tanpa meng-upload apa pun.

Space butuh secret HF_TOKEN (token READ) untuk mengunduh repo model yang private. Isi env
FANMETA_SPACE_HF_TOKEN sebelum menjalankan `space` supaya diisi otomatis, atau isi sendiri di
Settings Space > Variables and secrets.
"""

import argparse
import json
import os
from pathlib import Path

MODEL_REPO = os.environ.get("FANMETA_MODEL_REPO", "ZAaraAa/fanmeta-model")
SPACE_REPO = os.environ.get("FANMETA_SPACE", "ZAaraAa/fanmeta-model-api")
ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "checkpoints" / "06_model_app.json"

# File lokal -> path di Space. Hanya yang dibutuhkan untuk menjalankan model (tanpa Streamlit/Firebase).
SPACE_FILES = {
    "hf_space/app.py": "app.py",
    "hf_space/requirements.txt": "requirements.txt",
    "hf_space/README.md": "README.md",
    "src/__init__.py": "src/__init__.py",
    "src/ml/__init__.py": "src/ml/__init__.py",
    "src/ml/predictor.py": "src/ml/predictor.py",
    "src/ml/fanmeta_utils.py": "src/ml/fanmeta_utils.py",
    "checkpoints/06_model_app.json": "checkpoints/06_model_app.json",
}


def model_files() -> dict[str, str]:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    return {f"checkpoints/{name}": name for name in (config["roberta_checkpoint"], config["lstm_checkpoint"])}


def check(files: dict[str, str]) -> None:
    missing = [src for src in files if not (ROOT / src).is_file()]
    if missing:
        raise SystemExit("File tidak ditemukan: " + ", ".join(missing))
    for src, dst in files.items():
        print(f"  {src}  ->  {dst}  ({(ROOT / src).stat().st_size / 2**20:.1f} MB)")


def upload(api, repo_id: str, repo_type: str, files: dict[str, str], message: str) -> None:
    from huggingface_hub import CommitOperationAdd

    operations = [CommitOperationAdd(path_in_repo=dst, path_or_fileobj=str(ROOT / src)) for src, dst in files.items()]
    api.create_commit(repo_id=repo_id, repo_type=repo_type, operations=operations, commit_message=message)


def deploy_model(api, dry_run: bool) -> None:
    files = model_files()
    print(f"Repo model (private): {MODEL_REPO}")
    check(files)
    if dry_run:
        return
    api.create_repo(MODEL_REPO, repo_type="model", private=True, exist_ok=True)
    upload(api, MODEL_REPO, "model", files, "Upload model final C (RoBERTa + Task-Specific LSTM seed 42)")
    print(f"Selesai: https://huggingface.co/{MODEL_REPO}")


def deploy_space(api, dry_run: bool) -> None:
    print(f"Space (Gradio + ZeroGPU): {SPACE_REPO}")
    check(SPACE_FILES)
    if dry_run:
        return
    token = os.environ.get("FANMETA_SPACE_HF_TOKEN")
    secret = {"key": "HF_TOKEN", "value": token, "description": "Token READ untuk repo model private"}
    # Akun gratis hanya boleh membuat Space Gradio di ZeroGPU (Space baru otomatis cpu-basic = butuh PRO),
    # jadi hardware dan secret diisi saat Space dibuat, sebelum build pertama.
    api.create_repo(SPACE_REPO, repo_type="space", space_sdk="gradio", space_hardware="zero-a10g",
                    space_secrets=[secret] if token else None, exist_ok=True)
    if token:
        api.add_space_secret(SPACE_REPO, **secret)  # Space yang sudah ada: perbarui secret-nya
        print("Secret HF_TOKEN diisi.")
    else:
        print("PERHATIAN: isi secret HF_TOKEN (token READ) di Settings > Variables and secrets.")
    upload(api, SPACE_REPO, "space", SPACE_FILES, "Deploy FanMeta model API")
    print(f"Selesai: https://huggingface.co/spaces/{SPACE_REPO}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload model / Space FanMeta ke Hugging Face.")
    parser.add_argument("target", choices=["model", "space"])
    parser.add_argument("--dry-run", action="store_true", help="tampilkan daftar file tanpa meng-upload")
    args = parser.parse_args()

    api = None
    if not args.dry_run:
        from huggingface_hub import HfApi

        api = HfApi()
        print(f"Akun Hugging Face: {api.whoami()['name']}")
    (deploy_model if args.target == "model" else deploy_space)(api, args.dry_run)


if __name__ == "__main__":
    main()
