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

## Menjalankan

1. Pakai Python 3.11, lalu pasang library:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Salin file model ke folder `checkpoints/`: `02_roberta_stage1.pt` dan `04_lstm_task_specific_seed42.pt`.
   Pengaturan modelnya (`06_model_app.json`) sudah ada di repo.
3. Salin `.streamlit/secrets.toml.example` menjadi `.streamlit/secrets.toml`, lalu isi dengan kunci Firebase.
4. Pasang aturan keamanan Firestore: salin isi `firestore.rules` ke Firebase Console > Firestore > Rules.
5. Jalankan:
   ```
   streamlit run app.py
   ```
   Saat pertama kali dijalankan, aplikasi mengunduh tokenizer RoBERTa dan model NLLB-200 dari Hugging Face,
   jadi butuh koneksi internet.

## Branch

- `prod`: versi stabil yang siap dipakai.
- `dev`: tempat pengembangan. Perubahan digabung ke `prod` setelah teruji.

## Catatan

FanMeta tidak berafiliasi dengan Archive of Our Own (AO3) atau Organization for Transformative Works.
Metadata dari FanMeta adalah rekomendasi, bukan keputusan akhir; penulis tetap perlu memeriksanya sebelum
mengunggah karya.
