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
Arsitektur hierarkis ini diadaptasi dari ARC-NLP (Sahin dkk., 2023) untuk tugas Trigger Detection PAN 2023,
lalu dikembangkan menjadi multi-task (rating, warning, tags) dengan LSTM terpisah untuk tiap tugas.

Data latih berasal dari cerita AO3 hasil scraping dan dataset Hugging Face
[`midwestern-simulation-active/ao3_random_subset`](https://huggingface.co/datasets/midwestern-simulation-active/ao3_random_subset).
Dataset tidak dibagikan karena cerita adalah milik penulisnya.

### File model

File model (±500 MB) **tidak ada di repo ini** karena terlalu besar untuk GitHub. File disimpan di repo
Hugging Face [`ZAaraAa/fanmeta-model`](https://huggingface.co/ZAaraAa/fanmeta-model) dengan akses **gated**:

1. Buka halaman model, isi formulir **Request access**, lalu tunggu disetujui pemilik. Akses hanya untuk
   riset atau pendidikan non-komersial (lisensi CC BY-NC 4.0).
2. Setelah disetujui, login Hugging Face di komputer (`hf auth login`, token **read**). Aplikasi akan
   mengunduh kedua file model secara otomatis saat analisis pertama.

Tanpa akses ke file model, model tetap bisa dicoba lewat Space publik
[`ZAaraAa/fanmeta-model-api`](https://huggingface.co/spaces/ZAaraAa/fanmeta-model-api) (lihat bagian
[Deploy](#deploy-streamlit-community-cloud--hugging-face-space), bagian `[model_api]` di secrets).

### Referensi

- Sahin, U., Kucukkaya, I. E., & Toraman, C. (2023). *ARC-NLP at PAN 2023: Hierarchical Long Text
  Classification for Trigger Detection*. CLEF 2023 Working Notes. https://arxiv.org/abs/2307.14912
- Liu, Y., dkk. (2019). *RoBERTa: A Robustly Optimized BERT Pretraining Approach*. https://arxiv.org/abs/1907.11692
- NLLB Team (2022). *No Language Left Behind: Scaling Human-Centered Machine Translation*.
  https://arxiv.org/abs/2207.04672

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
│   ├── firestore_history.py, workspace_store.py   penyimpanan di Firestore
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
   pip install -r requirements-local.txt
   ```
2. Siapkan file model (lihat [File model](#file-model)): minta akses lalu `hf auth login`, atau salin
   `02_roberta_stage1_C.pt` dan `04_lstm_C_seed42.pt` (model final C) ke folder `checkpoints/` kalau sudah
   punya filenya. Pengaturan modelnya (`06_model_app.json`) sudah ada di repo.
3. Salin `.streamlit/secrets.toml.example` menjadi `.streamlit/secrets.toml`, lalu isi dengan kunci Firebase.
4. Pasang aturan keamanan Firestore: salin isi `firestore.rules` ke Firebase Console > Firestore > Rules.
5. Jalankan:
   ```
   streamlit run app.py
   ```
   Saat pertama kali dijalankan, aplikasi mengunduh tokenizer RoBERTa dan model NLLB-200 dari Hugging Face,
   jadi butuh koneksi internet.

## Deploy (Streamlit Community Cloud + Hugging Face Space)

Aplikasi online dipecah menjadi dua bagian, keduanya gratis:

| Bagian | Platform | Isi |
|---|---|---|
| Tampilan | Streamlit Community Cloud | `app.py` + `src/` (login, Workspace, History). Tidak memuat model. Library: `requirements.txt`. |
| Model | Hugging Face Space `ZAaraAa/fanmeta-model-api` (Gradio + ZeroGPU) | `hf_space/` + `src/ml/predictor.py` + `src/ml/fanmeta_utils.py` + `checkpoints/06_model_app.json` |
| File model | Repo model Hugging Face `ZAaraAa/fanmeta-model` (gated, persetujuan manual) | `02_roberta_stage1_C.pt`, `04_lstm_C_seed42.pt` |

Tampilan memanggil Space lewat `gradio_client` (`src/ml/remote_predictor.py`) kalau Streamlit secrets punya
bagian `[model_api]`. Tanpa bagian itu (misalnya di laptop), model berjalan langsung di komputer sendiri.

Pengguna memilih **GPU** (bawaan, lebih cepat) atau **CPU** (tidak memakai kuota) sebelum analisis. GPU memakai kuota ZeroGPU
akun `ZAaraAa` (akun PRO: 40 menit per hari, pulih 24 jam setelah pemakaian GPU pertama). Kalau kuota habis,
analisis otomatis dijalankan dengan CPU dan pengguna mendapat pemberitahuan. Perkiraan sisa kuota dicatat di
Firestore (dokumen `app_state/zerogpu_quota`).

### Pertama kali

1. Login Hugging Face (token **write** dari https://huggingface.co/settings/tokens):
   ```
   .venv\Scripts\hf.exe auth login
   ```
2. Upload file model ke repo model (gated):
   ```
   python deploy_hf_space.py model
   ```
3. Upload Space. Isi dulu `FANMETA_SPACE_HF_TOKEN` dengan token **read** supaya secret `HF_TOKEN` di Space
   terisi otomatis (dipakai Space untuk mengunduh repo model yang gated):
   ```
   $env:FANMETA_SPACE_HF_TOKEN = "hf_..."
   python deploy_hf_space.py space
   ```
   Cek di Settings Space: Hardware = **ZeroGPU**, dan secret `HF_TOKEN` ada. Kalau belum, atur manual.
   Tambahkan `--dry-run` di perintah mana pun untuk melihat daftar file tanpa meng-upload.
4. Buat aplikasi di https://share.streamlit.io dari repo GitHub ini: branch `prod`, file `app.py`,
   Advanced settings > Python **3.12**. Di kolom **Secrets**, tempel isi `.streamlit/secrets.toml` (Firebase)
   ditambah:
   ```toml
   [model_api]
   space = "ZAaraAa/fanmeta-model-api"
   hf_token = "hf_..."   # token read akun ZAaraAa; kuota GPU dihitung ke akun ini
   ```
   Tanpa `hf_token`, ZeroGPU memakai kuota anonim (2 menit per hari, dibagi per IP server).

### Update setelah online

| Yang diubah | Cara update |
|---|---|
| Tampilan (`app.py`, `src/ui/`, `src/services/`, `src/core/`) | Commit lalu push ke branch `prod`. Streamlit Cloud memperbarui sendiri. |
| Cara model berjalan (`src/ml/predictor.py`, `src/ml/fanmeta_utils.py`, `hf_space/`) atau `checkpoints/06_model_app.json` | `python deploy_hf_space.py space` |
| File model `.pt` | `python deploy_hf_space.py model`, lalu `python deploy_hf_space.py space` (nama file baru di `06_model_app.json`) |

Catatan:
- Setiap upload membuat Space build ulang dan restart (beberapa menit). Selama itu analisis online gagal,
  jadi jangan update tepat sebelum demo. Riwayat upload tersimpan di tab Files Space.
- Script upload hanya menambah dan menimpa file. File yang dihapus di laptop tetap ada di Space sampai dihapus
  manual dari tab Files.
- `src/ml/fanmeta_utils.py` adalah salinan dari folder Training: ubah di sana dulu, salin ke sini, baru upload.
- Space dan aplikasi Streamlit gratis akan tidur kalau lama tidak dibuka. Buka aplikasinya beberapa menit
  sebelum dipakai supaya model sudah dimuat.

## Branch

- `prod`: versi stabil yang siap dipakai.
- `dev`: tempat pengembangan. Perubahan digabung ke `prod` setelah teruji.

## Catatan

FanMeta tidak berafiliasi dengan Archive of Our Own (AO3) atau Organization for Transformative Works.
Metadata dari FanMeta adalah rekomendasi, bukan keputusan akhir; penulis tetap perlu memeriksanya sebelum
mengunggah karya.
