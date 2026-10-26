#!/usr/bin/env bash
# Dijalankan saat container Hugging Face Space start.
set -e

# 1. Secrets: Space tidak membaca .streamlit/secrets.toml dari repo (memang tidak di-upload).
#    Isi seluruh secrets.toml disimpan di Settings Space > Secrets dengan nama STREAMLIT_SECRETS.
if [ -n "$STREAMLIT_SECRETS" ]; then
    mkdir -p .streamlit
    printf '%s\n' "$STREAMLIT_SECRETS" > .streamlit/secrets.toml
else
    echo "PERINGATAN: STREAMLIT_SECRETS kosong, login Firebase tidak akan berfungsi."
fi

# 2. Unduh model di latar belakang (checkpoint fine-tune + NLLB), supaya pengguna pertama
#    tidak menunggu unduhan. Aplikasi tetap bisa dibuka selama proses ini berjalan.
python -c "
from src.ml.predictor import FanMetaPredictor
FanMetaPredictor(device='cpu')._load_nllb()
print('Model siap (sudah di-cache).')
" &

# 3. Jalankan Streamlit di port 7860 (port default Spaces).
#    XSRF dimatikan karena Space tampil di dalam iframe; tanpa ini upload .txt/.docx gagal (403).
exec streamlit run app.py \
    --server.port=7860 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.runOnSave=false \
    --server.enableXsrfProtection=false \
    --server.enableCORS=false \
    --browser.gatherUsageStats=false
