# FanMeta

Aplikasi web (Streamlit) yang merekomendasikan metadata **Archive of Our Own (AO3)** dari teks fanfiksi:

- **Content Rating**: General Audiences, Teen And Up Audiences, Mature, Explicit
- **Archive Warnings**: Graphic Depictions Of Violence, Major Character Death, Rape/Non-Con, No Archive Warnings Apply
- **Additional Tags**: 16 kategori (Angst, Fluff, Hurt/Comfort, dan lainnya)

Dibuat untuk skripsi S1 Teknik Informatika, Universitas Tarumanagara.

## Fitur

- **Quick Analysis**: tempel teks atau unggah `.txt` / `.docx`, dalam bahasa Inggris atau Indonesia.
  Teks Indonesia diterjemahkan dulu ke Inggris dengan NLLB-200.
- **Workspace**: simpan cerita per bab, tulis dengan editor teks, analisis per bab, lalu lihat metadata gabungan
  dan log analisis setiap cerita.
- **History** dan **Glossary** (penjelasan setiap metadata).

## Model

Teks dipecah menjadi segmen 200 kata (overlap 50 kata). RoBERTa (`FacebookAI/roberta-base`, di-fine-tune) membaca
setiap segmen, lalu Task-Specific LSTM menggabungkan semua segmen untuk tiap tugas (rating, warning, tags).

File model **tidak ada di repo ini** karena terlalu besar untuk GitHub (±500 MB).

## Struktur folder

```
app.py                  titik masuk: resource bersama (cache), aturan akses halaman, router (tabel ROUTES)
src/
├── ml/                 model AI
│   ├── fanmeta_utils.py    aturan preprocessing, segmentasi, NLLB, arsitektur model (salinan dari folder Training)
│   ├── predictor.py        menjalankan model di komputer ini (FanMetaPredictor)
│   ├── remote_predictor.py menjalankan model lewat Space Hugging Face (ZeroGPU)
│   └── model_api.py        memilih predictor lokal atau Space (dari Streamlit secrets)
├── services/           akses data & layanan luar
│   ├── firebase_auth.py    login / daftar (Firebase Auth)
│   ├── firestore_history.py, workspace_store.py, gallery_store.py   penyimpanan di Firestore
│   └── gpu_quota.py        catatan sisa kuota ZeroGPU
├── core/               helper tanpa tampilan
│   └── i18n.py (bahasa EN/ID), rich_text.py, story_file.py (.txt/.docx), workspace_metadata.py
├── ui/                 tampilan Streamlit
│   ├── pages/              satu file per halaman, masing-masing punya render(...)
│   ├── components.py       komponen bersama (topbar, navigate, badge, ikon)
│   ├── editor.py, auth_layout.py, device_choice.py
│   ├── styles.py           memuat CSS + warna mode gelap
│   └── css/                theme.css, dark_widgets.css
└── assets/             gambar (logo, ilustrasi)
checkpoints/            06_model_app.json (+ file .pt model, tidak ikut repo)
hf_space/               Space Hugging Face (Gradio + ZeroGPU) yang menjalankan model
```

Alur satu permintaan: `app.py` (router) → `src/ui/pages/<halaman>.py` → `src/services/*` (data) dan
`src/ml/*` (model).

## Menjalankan

1. Pakai Python 3.11, lalu pasang library:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Salin file model ke folder `checkpoints/`: `02_roberta_stage1_C.pt` dan `04_lstm_C_seed42.pt` (model final C).
   Pengaturan modelnya (`06_model_app.json`) sudah ada di repo.
3. Salin `.streamlit/secrets.toml.example` menjadi `.streamlit/secrets.toml`, lalu isi dengan kunci Firebase.
4. Pasang aturan keamanan Firestore: salin isi `firestore.rules` ke Firebase Console > Firestore > Rules.
5. Jalankan:
   ```
   streamlit run app.py
   ```
   Saat pertama kali dijalankan, aplikasi mengunduh tokenizer RoBERTa dan model NLLB-200 dari Hugging Face,
   jadi butuh koneksi internet.

## Deploy (Hugging Face Spaces)

Aplikasi di-deploy sebagai Space Docker. File model disimpan di repo model Hugging Face, bukan di GitHub.
Jika file `.pt` tidak ada di `checkpoints/`, `src/ml/predictor.py` mengunduhnya dari repo
`ZAaraAa/fanmeta-model` (bisa diganti lewat env `FANMETA_MODEL_REPO`).

1. Login: `hf auth login` (token **write** dari https://huggingface.co/settings/tokens).
2. Upload model (sekali saja, ulangi jika model diganti):
   ```
   hf repos create ZAaraAa/fanmeta-model --private
   hf upload ZAaraAa/fanmeta-model checkpoints/02_roberta_stage1_C.pt 02_roberta_stage1_C.pt
   hf upload ZAaraAa/fanmeta-model checkpoints/04_lstm_C_seed42.pt 04_lstm_C_seed42.pt
   ```
3. Upload aplikasi: `python deploy_hf_space.py` (rahasia, model, dan `mock_up/` tidak ikut).
4. Di Space > Settings > **Secrets**, tambahkan:
   - `STREAMLIT_SECRETS`: seluruh isi `.streamlit/secrets.toml`.
   - `HF_TOKEN`: token **read**, supaya Space bisa mengunduh repo model yang private.
5. Firebase Console > Authentication > Settings > **Authorized domains**: tambahkan `<nama-space>.hf.space`.

Catatan:
- Space CPU gratis (2 vCPU) lebih lambat dari laptop, terutama untuk teks Indonesia (NLLB).
  Untuk demo yang cepat, ganti hardware ke GPU (Settings > Hardware) dan tambahkan variable
  `TORCH_INDEX_URL=https://pypi.org/simple` supaya torch versi CUDA yang dipasang. Pause Space setelah selesai.
- Space gratis tidur setelah 48 jam tidak dibuka. Saat bangun, model diunduh ulang (beberapa menit),
  jadi buka aplikasinya dulu sebelum demo.
- Mengubah kode: commit ke GitHub seperti biasa, lalu jalankan lagi `python deploy_hf_space.py`.

## Branch

- `prod`: versi stabil yang siap dipakai.
- `dev`: tempat pengembangan. Perubahan digabung ke `prod` setelah teruji.

## Catatan

FanMeta tidak berafiliasi dengan Archive of Our Own (AO3) atau Organization for Transformative Works.
Metadata dari FanMeta adalah rekomendasi, bukan keputusan akhir; penulis tetap perlu memeriksanya sebelum
mengunggah karya.
