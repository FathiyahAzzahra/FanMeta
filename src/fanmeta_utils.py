"""
fanmeta_utils.py
================
Satu tempat untuk semua fungsi FanMeta, dipakai oleh:
    - 01_Training_FanMeta.ipynb
    - 02_Evaluasi_Indonesia.ipynb
    - aplikasi Streamlit (nanti)

Dengan begitu aturan label, preprocessing, segmentasi, dan model
dijamin SAMA di semua tempat. Kalau ingin mengubah aturan, ubah di sini saja.

Isi file:
    1. Konfigurasi label
    2. Preprocessing teks
    3. Rule-based labeling (Additional Tags, versi v2)
    4. Persiapan dataset (cleaning + labeling)
    5. Segmentasi 200/50
    6. Translasi NLLB (per kalimat)
    7. Model (RoBERTa segment encoder + Task-Specific LSTM + Shared LSTM)
    8. Loss, metrik, threshold
    9. Inference satu dokumen
"""

import re
import json
import hashlib
import unicodedata

import numpy as np
import pandas as pd
import torch
import torch.nn as nn


# ============================================================
# 1. KONFIGURASI LABEL
# ============================================================

TAGS = [
    "Alcohol", "Humor", "Angst", "Blood/Injury", "Character Death",
    "Established Relationship", "Family", "Fluff", "Friendship",
    "Hurt/Comfort", "Mental Health", "Mythical Creatures", "Pining",
    "Smut", "Suicide", "Whump",
]

RATINGS = [
    "General Audiences",
    "Teen And Up Audiences",
    "Mature",
    "Explicit",
]
RATING_TO_ID = {label: i for i, label in enumerate(RATINGS)}

WARNING_LABELS = [
    "No Archive Warnings Apply",
    "Graphic Depictions Of Violence",
    "Major Character Death",
    "Rape/Non-Con",
]


def _warning_col(label):
    return "warning_" + label.lower().replace("/", "_").replace(" ", "_")


WARNING_COLS = [_warning_col(w) for w in WARNING_LABELS]
# -> ['warning_no_archive_warnings_apply', 'warning_graphic_depictions_of_violence',
#     'warning_major_character_death', 'warning_rape_non-con']

LABEL_VERSION = "v3"   # hasil v2 tersimpan di fanmeta_checkpoint/, hasil v3 di fanmeta_checkpoint_v3/


# ============================================================
# 2. PREPROCESSING TEKS
# ============================================================
# Hanya membersihkan "sampah" teks. Huruf besar/kecil, tanda baca,
# dan stopword TIDAK diubah karena RoBERTa butuh teks natural.

_HTML = re.compile(r"<[^>]+>")
_URL = re.compile(r"https?://\S+|www\.\S+", flags=re.IGNORECASE)
_WS = re.compile(r"\s+")


def preprocess_text(text):
    text = str(text)
    text = _HTML.sub(" ", text)                 # 1. hapus HTML
    text = _URL.sub(" ", text)                  # 2. hapus URL
    text = unicodedata.normalize("NFKC", text)  # 3. normalisasi Unicode
    text = _WS.sub(" ", text).strip()           # 4. rapikan spasi
    return text


def text_hash(text):
    normalized = " ".join(str(text).lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ============================================================
# 3. RULE-BASED LABELING — ADDITIONAL TAGS (v2)
# ============================================================
# v1 = aturan asli (exact / whole word / contains).
# v2 = v1 + tambahan pola longgar untuk Humor, Fluff, Angst, Hurt/Comfort
#      (contoh: "fluff and humor" -> Fluff + Humor),
#      dengan pengecualian tag penyangkal ("no angst", "angst-free").
# Label v1 TIDAK pernah dihapus; v2 hanya MENAMBAH.

EXACT_MATCH_KEYWORDS = {
    "Angst": ["angst", "hurt no comfort", "angst with a happy ending",
                "angst and feels", "emotional hurt", "heartbreak"],
    "Fluff": ["fluff", "tooth-rotting fluff", "domestic fluff", "fluff and angst"],
    "Hurt/Comfort": ["hurt/comfort", "hurt comfort", "emotional hurt/comfort"],
    "Character Death": ["character death", "major character death", "off-screen death"],
    "Suicide": ["suicide", "suicidal ideation", "suicide attempt",
                "implied/referenced suicide", "suicidal thoughts",
                "mentions of suicide ideation", "mentions of suicide"],
    "Established Relationship": ["established relationship"],
    "Humor": ["humor", "attempt to humor"],
    "Smut": ["smut"],
}

WHOLE_WORD_KEYWORDS = {
    "Mythical Creatures": ["mythical creatures", "vampire", "werewolf", "mermaid",
                            "fairy", "fae", "shapeshifter", "phoenix", "demon",
                            "ghost", "elf", "elves", "siren"],
    "Whump": ["whump"],
    "Alcohol": ["alcohol", "alcoholism", "drunk", "drunkenness", "hangover"],
    "Mental Health": ["mental health", "depression", "anxiety", "trauma",
                        "therapy", "ptsd"],
}

CONTAINS_PATTERNS = {
    "Hurt/Comfort": [r"needs? a hug", r"touch[- ]starved"],
    "Pining": [r"lovesick", r"pining", r"unrequited", r"is (in love|smitten)"],
    "Family": [r"\bfamily\b", r"\bsibling", r"\bparent"],
    "Friendship": [r"friendship", r"bonding"],
    "Blood/Injury": [r"\bblood\b", r"\binjur(?:y|ies|ed)\b"],
}

NSFW_EXACT = [
    "smut", "nsfw", "anal sex", "oral sex", "blow job", "blowjob", "rough sex",
    "dirty talk", "praise kink", "size kink", "dubious consent", "dub-con",
    "non-con", "age play", "ageplay", "huge dick", "big dick", "face-fucking",
    "coming inside", "multiple orgasms", "sexual overstimulation",
    "unprotected sex", "touch-starved", "touch starved", "explicit sexual content",
]

NSFW_WHOLE_WORD = [
    "masturbation", "fingering", "penetration", "bdsm", "bondage", "spanking",
    "cunnilingus", "fellatio", "creampie", "edging", "deepthroat", "rimming",
    "orgasm", "genital", "nipple", "dick", "cock", "kink", "choking", "biting",
    "forced", "lube", "lubrication",
]

NSFW_CONTAINS = [r"\btop\b", r"\bbottom\b"]

# --- tambahan v2 ---
V2_LOOSE_KEYWORDS = {
    "Humor": r"humou?r",
    "Fluff": r"fluff",
    "Angst": r"angst",
    "Hurt/Comfort": r"hurt[/ ]comfort",
}

# --- tambahan v3 (hanya MENAMBAH; v1 & v2 tidak berubah) ---
# 1. Whole word boleh bentuk jamak -s/-es ("Vampires", "Ghosts", "Kinks").
#    Berlaku untuk WHOLE_WORD_KEYWORDS, NSFW_WHOLE_WORD, dan V3_WHOLE_WORD.
# 2. Whump diperluas ke trope penderitaan fisik (sickfic, torture, kidnapping,
#    captivity, physical abuse). Pola "Hurt <nama tokoh>" sengaja TIDAK dipakai:
#    nama tokoh tidak bisa didaftar dan mudah tertukar dengan Hurt/Comfort.
# 3. Celah aturan lain ditutup (Character Death, Humor, Friendship, Family,
#    Mental Health, Mythical Creatures).
V3_WHOLE_WORD = {
    "Mythical Creatures": ["werewolves", "fairies", "angel", "dragon"],
    "Whump": ["sick character", "sickfic", "sick fic", "torture", "kidnapping",
                "kidnapped", "captivity", "physical abuse"],
    "Humor": ["comedy", "crack", "crack treated seriously"],
    "Friendship": ["best friend", "platonic"],
    "Mental Health": ["panic attack", "self-harm", "self harm", "eating disorder",
                        "dissociation"],
}

V3_TAG_PATTERNS = {  # dicocokkan per tag (bukan seluruh string)
    "Character Death": [r"character death"],
    "Whump": [r"\bwhump\w*"],   # whumpee, whumper, whumptober, ...
    "Family": [r"\b(father|mother|brother|sister|daughter)s?\b"],
}

V3_EXCLUDE = {  # tag yang cocok pola di atas tapi TIDAK boleh diberi label v3
    "Friendship": r"to lovers",                 # "Best Friends to Lovers"
    "Family": r"incest",                        # hubungan seksual, bukan tema keluarga
    # nama tokoh / panggilan sayang, bukan makhluk mitos
    "Mythical Creatures": (r"monkey d\.? ?dragon|celestial dragon|angel dust|snow angel"
                            r"|petname|pet name|\bis an angel\b|'s an angel\b|shoutout to angel"),
    "Character Death": r"\b(no|not|non|without|zero)\s+(\w+\s+){0,2}character death",
}


def _split_tags(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    return [t.strip().lower() for t in str(value).split(";") if t.strip()]


def _whole_word(text, keyword, plural=False):
    suffix = r"(?:s|es)?" if plural else ""
    return re.search(r"\b" + re.escape(keyword.lower()) + suffix + r"\b", text) is not None


def _is_negated(tag, kata):
    # contoh: "no angst", "not much angst", "angst-free"
    return bool(
        re.search(rf"\b(no|not|non|without|zero)\s+(\w+\s+){{0,2}}{kata}", tag)
        or re.search(rf"{kata}[- ]free", tag)
    )


def apply_rule_based_tags(raw_tags, version=LABEL_VERSION):
    """Ubah string Additional Tags AO3 -> dict {tag: 0/1} untuk 16 target."""
    tags_text = "" if raw_tags is None else str(raw_tags).strip().lower()
    source = _split_tags(raw_tags)
    found = set()

    # Level 1: exact match per tag
    for target, keywords in EXACT_MATCH_KEYWORDS.items():
        if any(tag == kw.lower() for tag in source for kw in keywords):
            found.add(target)

    # Level 2: whole word per tag
    for target, keywords in WHOLE_WORD_KEYWORDS.items():
        if any(_whole_word(tag, kw) for tag in source for kw in keywords):
            found.add(target)

    # Level 3: contains / regex pada seluruh string tag
    for target, patterns in CONTAINS_PATTERNS.items():
        if any(re.search(p, tags_text, flags=re.IGNORECASE) for p in patterns):
            found.add(target)

    # Smut: gabungan banyak penanda konten seksual
    if (
        any(tag == kw for tag in source for kw in NSFW_EXACT)
        or any(_whole_word(tag, kw) for tag in source for kw in NSFW_WHOLE_WORD)
        or any(re.search(p, tags_text, flags=re.IGNORECASE) for p in NSFW_CONTAINS)
    ):
        found.add("Smut")

    # v2: pola longgar + pengecualian penyangkal (juga berlaku di v3)
    if version in ("v2", "v3"):
        for target, kata in V2_LOOSE_KEYWORDS.items():
            for tag in source:
                if re.search(rf"\b{kata}\b", tag) and not _is_negated(tag, kata):
                    found.add(target)
                    break

    if version == "v3":
        found |= _v3_tags(source)

    return {tag: int(tag in found) for tag in TAGS}


def _v3_tags(source):
    """Label tambahan v3 dari daftar tag (huruf kecil)."""
    found = set()

    def allowed(target, tag):
        ex = V3_EXCLUDE.get(target)
        return not (ex and re.search(ex, tag))

    # whole word + jamak, untuk aturan lama dan aturan v3
    for words in (WHOLE_WORD_KEYWORDS, V3_WHOLE_WORD):
        for target, keywords in words.items():
            if any(_whole_word(tag, kw, plural=True) and allowed(target, tag)
                   for tag in source for kw in keywords):
                found.add(target)

    if any(_whole_word(tag, kw, plural=True) for tag in source for kw in NSFW_WHOLE_WORD):
        found.add("Smut")

    for target, patterns in V3_TAG_PATTERNS.items():
        if any(re.search(p, tag) and allowed(target, tag) for tag in source for p in patterns):
            found.add(target)
    return found


def parse_warning_labels(value):
    """String Archive Warning AO3 -> dict {warning_col: 0/1}."""
    labels = [x.strip() for x in str(value).split(";") if x.strip()]
    return {
        col: int(label in labels)
        for label, col in zip(WARNING_LABELS, WARNING_COLS)
    }


def normalize_rating(value):
    value = str(value).strip()
    return value if value in RATING_TO_ID else np.nan


# ============================================================
# 4. PERSIAPAN DATASET
# ============================================================

def prepare_dataframe(df, english_only=True, version=LABEL_VERSION, verbose=True):
    """
    Pipeline lengkap dari CSV hasil scraping sampai siap dipakai model.

    Urutan (sama untuk data latih Inggris dan test Indonesia):
        1. buang kolom duplikat, cek kolom wajib
        2. isi nilai kosong, buang teks kosong
        3. (opsional) hanya bahasa Inggris
        4. buang duplikat ID, lalu duplikat teks
        5. preprocessing teks
        6. labeling Additional Tags (rule-based)
        7. labeling Rating (buang yang tidak valid, mis. Not Rated)
        8. labeling Archive Warning
        9. buang cerita tanpa satu pun target tag

    Mengembalikan (df_bersih, log) — log berisi jumlah data per tahap.
    """
    log = {}
    df = df.loc[:, ~df.columns.duplicated()].copy()

    required = ["id", "text", "rating", "archive_warning", "additional_tags"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Kolom wajib tidak ditemukan: {missing}")

    log["raw"] = len(df)

    df["text"] = df["text"].fillna("").astype(str).str.strip()
    for col in ["rating", "archive_warning", "additional_tags"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    n = len(df)
    df = df[df["text"] != ""].copy()
    log["buang_teks_kosong"] = n - len(df)

    if english_only and "language" in df.columns:
        n = len(df)
        lang = df["language"].fillna("").astype(str).str.strip().str.lower()
        df = df[lang.isin(["english", "en"])].copy()
        log["buang_non_english"] = n - len(df)

    n = len(df)
    df = df.drop_duplicates(subset=["id"], keep="first").copy()
    log["buang_duplikat_id"] = n - len(df)

    n = len(df)
    df["_hash"] = df["text"].map(text_hash)
    df = df.drop_duplicates(subset=["_hash"], keep="first").drop(columns="_hash")
    log["buang_duplikat_teks"] = n - len(df)

    df["text_raw"] = df["text"]
    df["text"] = df["text"].map(preprocess_text)
    n = len(df)
    df = df[df["text"].str.strip() != ""].copy()
    log["buang_kosong_setelah_preprocess"] = n - len(df)

    tag_matrix = pd.DataFrame(
        [apply_rule_based_tags(x, version=version) for x in df["additional_tags"]],
        index=df.index, columns=TAGS,
    )
    df = pd.concat([df.drop(columns=[c for c in TAGS if c in df.columns]), tag_matrix], axis=1)

    df["rating_label"] = df["rating"].map(normalize_rating)
    n = len(df)
    df = df[df["rating_label"].notna()].copy()
    log["buang_rating_tidak_valid"] = n - len(df)

    warn_matrix = pd.DataFrame(
        [parse_warning_labels(x) for x in df["archive_warning"]],
        index=df.index, columns=WARNING_COLS,
    )
    df = pd.concat([df.drop(columns=[c for c in WARNING_COLS if c in df.columns]), warn_matrix], axis=1)
    # 1 = penulis memberi minimal satu dari 4 warning target.
    # 0 = misalnya "Creator Chose Not To Use Archive Warnings" -> label TIDAK diketahui.
    df["warning_has_gt"] = df[WARNING_COLS].sum(axis=1).gt(0).astype(int)

    n = len(df)
    df = df[df[TAGS].sum(axis=1) > 0].copy()
    log["buang_tanpa_target_tag"] = n - len(df)

    log["final"] = len(df)
    df = df.reset_index(drop=True)

    if verbose:
        print("Ringkasan cleaning:")
        for k, v in log.items():
            print(f"  {k:32s}: {v}")
    return df, log


def label_distribution(df):
    """Tabel jumlah & persentase untuk rating, warning, tags."""
    n = len(df)
    rating = df["rating_label"].value_counts().reindex(RATINGS, fill_value=0)
    warning = df[WARNING_COLS].sum()
    warning.index = WARNING_LABELS
    tags = df[TAGS].sum().sort_values(ascending=False)

    def to_table(s, name):
        return pd.DataFrame({
            name: s.index,
            "Jumlah": s.values.astype(int),
            "Persentase (%)": (s.values / n * 100).round(2),
        })

    return (
        to_table(rating, "Content Rating"),
        to_table(warning, "Archive Warning"),
        to_table(tags, "Additional Tags"),
    )


# ============================================================
# 5. SEGMENTASI 200 KATA / OVERLAP 50
# ============================================================

SEGMENT_WORDS = 200
OVERLAP_WORDS = 50


def split_segments(text, segment_words=SEGMENT_WORDS, overlap_words=OVERLAP_WORDS):
    words = str(text).split()
    if not words:
        return [""]
    if len(words) <= segment_words:
        return [" ".join(words)]

    segments = []
    step = segment_words - overlap_words
    for start in range(0, len(words), step):
        chunk = words[start:start + segment_words]
        if not chunk:
            break
        segments.append(" ".join(chunk))
        if start + segment_words >= len(words):
            break
    return segments


# ============================================================
# 6. TRANSLASI NLLB (Indonesia -> Inggris)
# ============================================================
# NLLB dilatih per kalimat. Satu segmen 200 kata dipecah menjadi
# KALIMAT, tiap kalimat diterjemahkan, lalu digabung kembali menjadi
# SATU segmen Inggris.
# Riwayat: (1) 200 kata sekaligus, max_new_tokens=160 -> terpotong (rasio 0,41);
# (2) kelompok kalimat <=120 token -> rasio 0,73, 19% segmen rasio < 0,6 karena
# NLLB melompati kalimat; (3) per kalimat -> rasio 1,11, 0% segmen < 0,6,
# waktu sama (uji 20 cerita, 21 Okt 2026). Cara (2) masih bisa dipakai
# dengan per_sentence=False untuk mengulang hasil lama.

def split_sentences(text, max_words=60):
    parts = re.split(r"(?<=[.!?])\s+", str(text).strip())
    out = []
    for p in parts:
        if not p:
            continue
        w = p.split()
        if len(w) > max_words:  # kalimat sangat panjang / tanpa titik
            out.extend(" ".join(w[i:i + max_words]) for i in range(0, len(w), max_words))
        else:
            out.append(p)
    return out


def group_sentences(sentences, tokenizer, max_tokens=120):
    groups, cur = [], []
    for s in sentences:
        cand = " ".join(cur + [s])
        n = len(tokenizer.encode(cand, add_special_tokens=False))
        if cur and n > max_tokens:
            groups.append(" ".join(cur))
            cur = [s]
        else:
            cur.append(s)
    if cur:
        groups.append(" ".join(cur))
    return groups


@torch.inference_mode()
def translate_many(texts, tokenizer, model, device, forced_bos_token_id,
                    batch_size=16, num_beams=2):
    """Terjemahkan banyak potongan sekaligus. Batch otomatis turun jika VRAM penuh."""
    order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
    results = [""] * len(texts)
    bs, i = batch_size, 0
    while i < len(order):
        idxs = order[i:i + bs]
        batch = [texts[j] for j in idxs]
        try:
            enc = tokenizer(batch, return_tensors="pt", padding=True,
                            truncation=True, max_length=256)
            enc = {k: v.to(device) for k, v in enc.items()}
            max_new = int(enc["input_ids"].shape[1] * 1.5) + 10
            out = model.generate(
                **enc,
                forced_bos_token_id=forced_bos_token_id,
                max_new_tokens=max_new,
                num_beams=num_beams,
                no_repeat_ngram_size=4,
            )
            decoded = tokenizer.batch_decode(out, skip_special_tokens=True,
                                                clean_up_tokenization_spaces=True)
            for j, t in zip(idxs, decoded):
                results[j] = t.strip()
            i += len(idxs)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            if bs == 1:
                raise
            bs = max(1, bs // 2)
            print(f"\n⚠ VRAM penuh, batch NLLB diturunkan ke {bs}")
    return results


def translate_document(text, tokenizer, model, device, forced_bos_token_id,
                        batch_size=16, num_beams=2, per_sentence=True):
    """Segmentasi 200/50 (bahasa Indonesia) lalu terjemahkan tiap segmen.
    per_sentence=True: per kalimat (bawaan). False: kelompok kalimat <=120 token (cara lama)."""
    segments_id = split_segments(text)
    if per_sentence:
        seg_groups = [split_sentences(s) for s in segments_id]
    else:
        seg_groups = [group_sentences(split_sentences(s), tokenizer) for s in segments_id]
    # potongan yang sama (akibat overlap) cukup diterjemahkan sekali
    unique = list(dict.fromkeys(g for groups in seg_groups for g in groups))
    translated = dict(zip(unique, translate_many(
        unique, tokenizer, model, device, forced_bos_token_id, batch_size, num_beams
    )))
    segments_en = [
        " ".join(translated[g] for g in groups if translated[g])
        for groups in seg_groups
    ]
    return segments_id, segments_en


def length_ratio(segments_id, segments_en):
    """Rasio jumlah kata Inggris / Indonesia per segmen (cek kualitas terjemahan)."""
    return [len(b.split()) / max(1, len(a.split())) for a, b in zip(segments_id, segments_en)]


# ============================================================
# 7. MODEL
# ============================================================

ENCODER_MODEL_NAME = "FacebookAI/roberta-base"
TOKEN_MAX_LENGTH = 256
HIDDEN_SIZE = 100
NUM_RATING = len(RATINGS)
NUM_WARNING = len(WARNING_LABELS)
NUM_TAGS = len(TAGS)


class RoBERTaSegmentMultiTask(nn.Module):
    """
    Stage 1. RoBERTa membaca SATU segmen dan menghasilkan CLS embedding (768).
    Tiga head sementara hanya dipakai saat fine-tuning Stage 1.
    """

    def __init__(self, model_name=ENCODER_MODEL_NAME):
        super().__init__()
        from transformers import AutoModel
        self.encoder = AutoModel.from_pretrained(model_name)
        # Checkpoint disimpan dengan transformers 4.24 yang ikut menyimpan buffer
        # "position_ids" (nomor urut posisi token, bukan bobot hasil belajar).
        # Transformers versi baru tidak menyimpannya, jadi buffer ini dibuat
        # persisten lagi supaya checkpoint lama tetap bisa dimuat (strict).
        emb = self.encoder.embeddings
        if "position_ids" not in emb._buffers:
            emb.register_buffer(
                "position_ids",
                torch.arange(self.encoder.config.max_position_embeddings).expand((1, -1)),
                persistent=True,
            )
        else:
            emb._non_persistent_buffers_set.discard("position_ids")
        hidden = self.encoder.config.hidden_size
        self.dropout = nn.Dropout(0.2)
        self.rating_head = nn.Linear(hidden, NUM_RATING)
        self.warning_head = nn.Linear(hidden, NUM_WARNING)
        self.tag_head = nn.Linear(hidden, NUM_TAGS)

    def forward(self, input_ids, attention_mask):
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls = self.dropout(out.last_hidden_state[:, 0, :])
        return {
            "cls_embedding": cls,
            "rating_logits": self.rating_head(cls),
            "warning_logits": self.warning_head(cls),
            "tag_logits": self.tag_head(cls),
        }


def _make_head(hidden, n_out):
    return nn.Sequential(nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, n_out))


def _last_hidden(lstm, embeddings, lengths, dropout):
    packed = nn.utils.rnn.pack_padded_sequence(
        embeddings, lengths.cpu(), batch_first=True, enforce_sorted=False,
    )
    _, (hidden, _) = lstm(packed)
    return dropout(hidden[-1])


class TaskSpecificLSTMMultiTask(nn.Module):
    """
    Stage 2 — MODEL UTAMA FanMeta.
    Satu LSTM untuk tiap tugas (Rating, Warning, Tags), masing-masing
    membaca urutan CLS embedding yang sama.
    """

    def __init__(self, hidden_size=HIDDEN_SIZE):
        super().__init__()
        self.rating_lstm = nn.LSTM(768, hidden_size, num_layers=1, batch_first=True)
        self.warning_lstm = nn.LSTM(768, hidden_size, num_layers=1, batch_first=True)
        self.tag_lstm = nn.LSTM(768, hidden_size, num_layers=1, batch_first=True)
        self.dropout = nn.Dropout(0.2)
        self.rating_head = _make_head(hidden_size, NUM_RATING)
        self.warning_head = _make_head(hidden_size, NUM_WARNING)
        self.tag_head = _make_head(hidden_size, NUM_TAGS)

    def forward(self, embeddings, lengths):
        r = _last_hidden(self.rating_lstm, embeddings, lengths, self.dropout)
        w = _last_hidden(self.warning_lstm, embeddings, lengths, self.dropout)
        t = _last_hidden(self.tag_lstm, embeddings, lengths, self.dropout)
        return {
            "rating_logits": self.rating_head(r),
            "warning_logits": self.warning_head(w),
            "tag_logits": self.tag_head(t),
        }


class SharedLSTMMultiTask(nn.Module):
    """Stage 2 — PEMBANDING (ablation): satu LSTM dipakai bersama tiga tugas."""

    def __init__(self, hidden_size=HIDDEN_SIZE):
        super().__init__()
        self.lstm = nn.LSTM(768, hidden_size, num_layers=1, batch_first=True)
        self.dropout = nn.Dropout(0.2)
        self.rating_head = _make_head(hidden_size, NUM_RATING)
        self.warning_head = _make_head(hidden_size, NUM_WARNING)
        self.tag_head = _make_head(hidden_size, NUM_TAGS)

    def forward(self, embeddings, lengths):
        d = _last_hidden(self.lstm, embeddings, lengths, self.dropout)
        return {
            "rating_logits": self.rating_head(d),
            "warning_logits": self.warning_head(d),
            "tag_logits": self.tag_head(d),
        }


LSTM_MODELS = {
    "task_specific": TaskSpecificLSTMMultiTask,
    "shared": SharedLSTMMultiTask,
}


# ============================================================
# 8. LOSS, METRIK, THRESHOLD
# ============================================================

def make_pos_weight(frame, columns, device, clip_max=10.0):
    """Bobot kelas positif = jumlah negatif / jumlah positif, dibatasi 1..10."""
    y = frame[columns].fillna(0).astype(np.float32).values
    pos = y.sum(axis=0)
    neg = len(y) - pos
    w = np.ones(len(columns), dtype=np.float32)
    mask = pos > 0
    w[mask] = neg[mask] / pos[mask]
    w = np.clip(w, 1.0, clip_max)
    return torch.tensor(w, dtype=torch.float32, device=device)


class MultiTaskLoss:
    """Total loss = CrossEntropy(rating) + BCE(warning) + BCE(tags)."""

    def __init__(self, df_train, device):
        self.device = device
        self.rating = nn.CrossEntropyLoss()
        self.warning = nn.BCEWithLogitsLoss(pos_weight=make_pos_weight(df_train, WARNING_COLS, device))
        self.tags = nn.BCEWithLogitsLoss(pos_weight=make_pos_weight(df_train, TAGS, device))

    def __call__(self, out, batch):
        d = self.device
        return (
            self.rating(out["rating_logits"], batch["rating_labels"].to(d))
            + self.warning(out["warning_logits"], batch["warning_labels"].to(d))
            + self.tags(out["tag_logits"], batch["tag_labels"].to(d))
        )


def compute_metrics(rating_true, rating_pred, warn_true, warn_prob, tag_true, tag_prob,
                    warn_thr=0.5, tag_thr=0.5):
    """
    Metrik sesuai proposal:
        Rating  : Accuracy, Macro-F1
        Warning : Micro-F1, Macro-F1 — HANYA cerita yang punya label warning
                (cerita "Creator Chose Not To Use" = label tidak diketahui)
        Tags    : Micro-F1, Macro-F1
    warn_thr / tag_thr boleh angka tunggal atau array per label.
    """
    from sklearn.metrics import accuracy_score, f1_score

    warn_pred = np.asarray(warn_prob) >= np.asarray(warn_thr)
    tag_pred = np.asarray(tag_prob) >= np.asarray(tag_thr)
    has_gt = np.asarray(warn_true).sum(axis=1) > 0

    f1 = lambda y, p, avg: f1_score(y, p, average=avg, zero_division=0)
    return {
        "rating_accuracy": accuracy_score(rating_true, rating_pred),
        "rating_macro_f1": f1(rating_true, rating_pred, "macro"),
        "warning_micro_f1": f1(warn_true[has_gt], warn_pred[has_gt], "micro"),
        "warning_macro_f1": f1(warn_true[has_gt], warn_pred[has_gt], "macro"),
        "tags_micro_f1": f1(tag_true, tag_pred, "micro"),
        "tags_macro_f1": f1(tag_true, tag_pred, "macro"),
    }


METRIC_COLS = [
    "rating_accuracy", "rating_macro_f1",
    "warning_micro_f1", "warning_macro_f1",
    "tags_micro_f1", "tags_macro_f1",
]


def tune_thresholds(y_true, y_prob, grid=None, min_support=15):
    """
    Cari 'batas yakin' terbaik per label pada data VALIDATION.
        1. cari satu threshold global terbaik (Macro-F1)
        2. label dengan contoh >= min_support dapat threshold sendiri
        3. label langka tetap memakai threshold global (supaya tidak overfit)
    """
    from sklearn.metrics import f1_score

    if grid is None:
        grid = np.round(np.arange(0.30, 0.91, 0.05), 2)
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)

    g_best = max(grid, key=lambda t: f1_score(y_true, y_prob >= t, average="macro", zero_division=0))
    thr = np.full(y_true.shape[1], g_best, dtype=float)
    for j in range(y_true.shape[1]):
        if y_true[:, j].sum() < min_support:
            continue
        thr[j] = max(grid, key=lambda t: f1_score(y_true[:, j], y_prob[:, j] >= t, zero_division=0))
    return float(g_best), thr


def mean_std_table(rows, cols=METRIC_COLS):
    df = pd.DataFrame(rows)
    return pd.DataFrame({
        "rata_rata": df[cols].mean(),
        "std": df[cols].std(),
        "tampilan": [f"{df[c].mean():.3f} ± {df[c].std():.3f}" for c in cols],
    }, index=cols)


# ============================================================
# 9. INFERENCE SATU DOKUMEN (dipakai juga oleh aplikasi)
# ============================================================

@torch.inference_mode()
def get_cls_embeddings(segments, roberta, tokenizer, device, batch_size=16, use_amp=True):
    roberta.eval()
    embs = []
    for i in range(0, len(segments), batch_size):
        enc = tokenizer(segments[i:i + batch_size], truncation=True,
                        max_length=TOKEN_MAX_LENGTH, padding="max_length",
                        return_attention_mask=True, return_tensors="pt")
        with torch.amp.autocast("cuda", enabled=use_amp and device.type == "cuda"):
            out = roberta(enc["input_ids"].to(device), enc["attention_mask"].to(device))
        embs.append(out["cls_embedding"].float().cpu())
    return torch.cat(embs, dim=0)


def postprocess_warnings(warn_prob, thr):
    """'No Archive Warnings Apply' tidak boleh muncul bersama warning lain."""
    thr = np.broadcast_to(np.asarray(thr, dtype=float), (len(WARNING_LABELS),))
    specific = [WARNING_LABELS[i] for i in (1, 2, 3) if warn_prob[i] >= thr[i]]
    return specific if specific else ["No Archive Warnings Apply"]


@torch.inference_mode()
def predict_document(text_en, roberta, tokenizer, lstm_model, device,
                        warn_thr=0.5, tag_thr=0.5, max_tags=5, use_amp=True):
    """Teks bahasa Inggris -> rekomendasi metadata."""
    segments = split_segments(preprocess_text(text_en))
    return predict_segments(segments, roberta, tokenizer, lstm_model, device,
                            warn_thr, tag_thr, max_tags, use_amp)


@torch.inference_mode()
def predict_indonesian(text_id, nllb_tokenizer, nllb_model, forced_bos_token_id,
                        roberta, tokenizer, lstm_model, device,
                        warn_thr=0.5, tag_thr=0.5, max_tags=5, use_amp=True,
                        nllb_batch=16, num_beams=2, on_stage=None):
    """
    Teks bahasa Indonesia -> rekomendasi metadata.
    Segmentasi 200/50 dilakukan SEBELUM NLLB (sama seperti evaluasi),
    lalu tiap segmen Inggris langsung masuk RoBERTa.
    on_stage (opsional) dipanggil dengan "translating" lalu "classifying",
    dipakai aplikasi untuk menampilkan progres.
    """
    if on_stage:
        on_stage("translating")
    _, segments_en = translate_document(preprocess_text(text_id), nllb_tokenizer, nllb_model,
                                        device, forced_bos_token_id, nllb_batch, num_beams)
    if on_stage:
        on_stage("classifying")
    result = predict_segments(segments_en, roberta, tokenizer, lstm_model, device,
                                warn_thr, tag_thr, max_tags, use_amp)
    result["segments_english"] = segments_en
    return result


@torch.inference_mode()
def predict_segments(segments, roberta, tokenizer, lstm_model, device,
                        warn_thr=0.5, tag_thr=0.5, max_tags=5, use_amp=True):
    """Daftar segmen bahasa Inggris -> rekomendasi metadata."""
    emb = get_cls_embeddings(segments, roberta, tokenizer, device, use_amp=use_amp)
    lstm_model.eval()
    out = lstm_model(emb.unsqueeze(0).to(device), torch.tensor([len(segments)]))

    rating_prob = torch.softmax(out["rating_logits"], dim=1)[0].cpu().numpy()
    warn_prob = torch.sigmoid(out["warning_logits"])[0].cpu().numpy()
    tag_prob = torch.sigmoid(out["tag_logits"])[0].cpu().numpy()

    tag_thr = np.broadcast_to(np.asarray(tag_thr, dtype=float), (len(TAGS),))
    order = [i for i in np.argsort(-tag_prob) if tag_prob[i] >= tag_thr[i]]
    return {
        "rating": RATINGS[int(rating_prob.argmax())],
        "rating_probabilities": dict(zip(RATINGS, rating_prob.round(4).tolist())),
        "warnings": postprocess_warnings(warn_prob, warn_thr),
        "warning_probabilities": dict(zip(WARNING_LABELS, warn_prob.round(4).tolist())),
        "tags": [TAGS[i] for i in order[:max_tags]],
        "tag_probabilities": dict(zip(TAGS, tag_prob.round(4).tolist())),
        "n_segments": len(segments),
    }
