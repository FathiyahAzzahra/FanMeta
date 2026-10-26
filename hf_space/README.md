---
title: FanMeta Model API
emoji: 📚
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 6.29.1
python_version: "3.12"
app_file: app.py
pinned: false
short_description: Model API for FanMeta (AO3 metadata recommendation)
---

# FanMeta Model API

Space ini menjalankan model FanMeta (RoBERTa + Task-Specific LSTM, NLLB-200 untuk teks Indonesia)
dan dipanggil oleh aplikasi Streamlit FanMeta lewat `gradio_client`.

- Hardware: **ZeroGPU** (pilih di Settings > Hardware).
- Secret `HF_TOKEN`: token read, untuk mengunduh file model dari repo `ZAaraAa/fanmeta-model` (private).
- Endpoint `/analyze(text, language, use_gpu)`: `use_gpu=False` berjalan di CPU (tanpa kuota);
  `use_gpu=True` memakai ZeroGPU dan otomatis pindah ke CPU kalau kuota habis.

Skripsi S1 Teknik Informatika, Universitas Tarumanagara.
