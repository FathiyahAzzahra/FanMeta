"""Shared visual language derived from the FanMeta mockups."""

import base64
from pathlib import Path

import streamlit as st

ASSET_STEM = "gambar_register"
_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ===== 1. TOKENS & BASE ===== */
:root {
    --ink:#202033; --muted:#505365; --line:#e5e7eb; --surface:#ffffff; --canvas:#f7f8fc;
    --violet:#635bff; --violet-dark:#5149db; --violet-soft:#efeeff;
    --green:#29b66f; --orange:#ff9d45;
}
html, body, .stApp { font-family:'Inter', 'Source Sans Pro', sans-serif; }
.stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
.stApp li, .stApp input, .stApp textarea, .stApp button { font-family:'Inter', 'Source Sans Pro', sans-serif; }
[data-testid="stIconMaterial"], span[class*="material"] { font-family:"Material Symbols Rounded" !important; }
.stApp { background:var(--canvas); color:var(--ink); }
#MainMenu, footer, header { visibility:hidden; }
.block-container { max-width:1328px; padding:1.2rem 24px 3rem; }
h1, h2, h3, p { color:var(--ink); }

/* ===== 2. SHARED COMPONENTS ===== */
.fanmeta-brand { font-weight:800; color:var(--ink); font-size:1.05rem; white-space:nowrap; }
.fanmeta-brand span { display:inline-block; background:var(--violet); color:white; border-radius:5px; padding:2px 6px; margin-right:5px; }
.page-kicker { font-size:.8rem; color:var(--muted); margin-top:-.55rem; margin-bottom:1.3rem; }
.guide-card, .result-card { background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:1rem 1.1rem; margin-bottom:.8rem; }
.guide-card h4, .result-card h4 { margin:0 0 .5rem; font-size:.95rem; }
.guide-card p { font-size:.8rem; color:var(--muted); line-height:1.5; margin:.25rem 0 .8rem; }
.metric-label { font-size:.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }
.pill { display:inline-block; border-radius:5px; padding:.18rem .48rem; margin:.12rem .22rem .12rem 0; background:var(--violet-soft); color:#4d46be; font-size:.76rem; font-weight:600; }
.pill-warning { background:#fff0e8; color:#c2410c; }
.pill-rating { background:#edf7ff; color:#2563a8; }
.empty-copy { color:var(--muted); font-size:.85rem; }

.history-meta { color:var(--muted); font-size:.8rem; }

/* ===== 3. FORM CONTROLS ===== */
.stTextInput div[data-baseweb="input"],
.stTextInput div[data-baseweb="base-input"],
.stTextArea div[data-baseweb="textarea"],
.stTextArea div[data-baseweb="base-input"],
div[data-baseweb="select"] > div { background:#fff !important; }

.stTextInput input, .stTextArea textarea,
div[data-baseweb="select"] div { color:var(--ink) !important; -webkit-text-fill-color:var(--ink); }
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color:#6b7280 !important; -webkit-text-fill-color:#6b7280; }

div[data-testid="stForm"] { border:0 !important; padding:0 !important; }
.stTextInput div[data-baseweb="input"],
.stTextInput div[data-baseweb="base-input"],
.stTextArea textarea,
div[data-baseweb="select"] > div { border-color:#d9d7e5 !important; border-radius:6px !important; background:white !important; }
.stTextInput input { background:transparent !important; color:var(--ink) !important; }
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color:#6b7280 !important; opacity:1; }
/* tombol (mockup): primer = ungu solid, biasa = putih bergaris, tersier = teks saja */
.stButton > button, .stFormSubmitButton > button {
    border-radius:8px; font-weight:600; min-height:2.4rem; box-shadow:none;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"] {
    background:var(--violet); color:#fff; border:0;
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primaryFormSubmit"]:hover { background:var(--violet-dark); color:#fff; }
.stButton > button[kind="primary"] p, .stFormSubmitButton > button[kind="primaryFormSubmit"] p { color:#fff !important; }
.stButton > button[kind="secondary"], .stFormSubmitButton > button[kind="secondaryFormSubmit"] {
    background:#fff; color:var(--ink); border:1px solid var(--line);
}
.stButton > button[kind="secondary"] p, .stFormSubmitButton > button[kind="secondaryFormSubmit"] p { color:var(--ink); }
.stButton > button[kind="secondary"]:hover, .stFormSubmitButton > button[kind="secondaryFormSubmit"]:hover { border-color:var(--violet); }
.stButton > button[kind="secondary"]:hover p, .stFormSubmitButton > button[kind="secondaryFormSubmit"]:hover p { color:var(--violet); }
.stButton > button[kind="tertiary"] { background:transparent; border:0; min-height:0; padding:0; }

/* ===== 4. AUTH PAGES (login & register) ===== */
[data-testid="stAppViewContainer"]:has(.auth-art-marker) { background:#fff; }
/* kunci halaman auth: tidak ada scroll, tidak ada strip putih */
html:has(.auth-art-marker), body:has(.auth-art-marker) { overflow:hidden !important; height:100vh; }
[data-testid="stAppViewContainer"]:has(.auth-art-marker) [data-testid="stMain"] {
    overflow:hidden !important; height:100vh; padding:0 !important;
}
[data-testid="stAppViewContainer"]:has(.auth-art-marker) [data-testid="stMainBlockContainer"] {
    padding:0 !important; height:100vh; overflow:hidden;
}
[data-testid="stAppViewContainer"]:has(.auth-art-marker) [data-testid="stBottom"],
[data-testid="stAppViewContainer"]:has(.auth-art-marker) [data-testid="stBottomBlockContainer"] { display:none !important; }

/* panel pas 100vh, bukan lebih */
div[data-testid="stColumn"]:has(.auth-art-marker),
div[data-testid="column"]:has(.auth-art-marker),
div[data-testid="stColumn"]:has(.auth-form-marker),
div[data-testid="column"]:has(.auth-form-marker) { height:100vh; min-height:100vh; overflow:hidden; }
.auth-art { height:100vh; min-height:100vh; }
div[data-testid="stColumn"]:has(.auth-form-marker) > div[data-testid="stVerticalBlock"],
div[data-testid="column"]:has(.auth-form-marker) > div[data-testid="stVerticalBlock"] { height:100vh; min-height:100vh; }

[data-testid="stAppViewContainer"]:has(.auth-art-marker) [data-testid="stHeader"],
[data-testid="stAppViewContainer"]:has(.auth-art-marker) [data-testid="stToolbar"],
[data-testid="stAppViewContainer"]:has(.auth-art-marker) [data-testid="stDecoration"] { display:none !important; }
[data-testid="stAppViewContainer"]:has(.auth-art-marker) [data-testid="stMain"] { padding-top:0 !important; }
[data-testid="stAppViewContainer"]:has(.auth-art-marker) [data-testid="stMainBlockContainer"],
[data-testid="stAppViewContainer"]:has(.auth-art-marker) .block-container { padding:0 !important; max-width:100% !important; }
[data-testid="stMainBlockContainer"]:has(.auth-art-marker) > [data-testid="stVerticalBlock"] { gap:0 !important; }
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] style) { display:none; }
div[data-testid="stHorizontalBlock"]:has(.auth-art-marker) { gap:0 !important; align-items:stretch !important; }

div[data-testid="stColumn"]:has(.auth-art-marker),
div[data-testid="column"]:has(.auth-art-marker) {
    min-height:100vh;
    background:
        linear-gradient(180deg, rgba(10,8,30,.55) 0%, rgba(10,8,30,.35) 45%, rgba(10,8,30,.75) 100%),
        linear-gradient(135deg, #1b1740, #3b2f7a);
}

.auth-art {
    position:relative; min-height:100vh; box-sizing:border-box; padding:2rem 2.5rem;
    display:flex; flex-direction:column; justify-content:flex-start;
}
.auth-brand { display:flex; align-items:center; gap:.7rem; }
.auth-brand img { height:52px; width:auto; flex:none; filter:drop-shadow(0 0 8px rgba(255,255,255,.55)); }
.auth-brand .logo { width:64px; height:64px; border-radius:8px; background:#6C63FF; color:#fff; display:grid; place-items:center; }
.auth-brand-name { color:#fff !important; font-size:3rem; font-weight:700; letter-spacing:.3px; }
.auth-copy { margin:auto 0; padding-bottom:4rem; }
.auth-art h1 { color:#fff !important; font-size:2.4rem; line-height:1.2; font-weight:800; max-width:700px; margin:0 0 1rem; padding:0; }
.auth-art p { color:#E4E2FA !important; font-size:1rem; line-height:1.65; max-width:700px; margin:0; }

div[data-testid="stColumn"]:has(.auth-form-marker),
div[data-testid="column"]:has(.auth-form-marker) { background:#fff; min-height:100vh; }
div[data-testid="stColumn"]:has(.auth-form-marker) > div[data-testid="stVerticalBlock"],
div[data-testid="column"]:has(.auth-form-marker) > div[data-testid="stVerticalBlock"] {
    min-height:100vh; justify-content:center; padding:2rem 3.5rem; max-width:520px; margin:0 auto; gap:.6rem;
}
.auth-form-title h2 { font-size:1.6rem; font-weight:800; color:#111827; margin:0 0 .35rem; padding:0; }
.auth-form-title p { color:var(--muted); font-size:.85rem; margin:0 0 .6rem; }
.auth-hint { color:#6b7280; font-size:.72rem; margin:-.35rem 0 .2rem; }
div[data-testid="stColumn"]:has(.auth-form-marker) [data-testid="stTextInput"] label p { font-size:.78rem; font-weight:600; color:#1f2937; }
div[data-testid="stColumn"]:has(.auth-form-marker) .stTextInput div[data-baseweb="input"],
div[data-testid="stColumn"]:has(.auth-form-marker) .stTextInput div[data-baseweb="base-input"] { background:#F6F7FB !important; border-radius:10px !important; }
div[data-testid="stColumn"]:has(.auth-form-marker) .stTextInput div[data-baseweb="input"] { border:1px solid #E5E7EB !important; }
div[data-testid="stColumn"]:has(.auth-form-marker) .stTextInput div[data-baseweb="input"]:focus-within { border-color:#5B5FEF !important; box-shadow:0 0 0 2px rgba(91,95,239,.15); }
div[data-testid="stColumn"]:has(.auth-form-marker) .stTextInput input { font-size:.86rem; padding:.7rem .8rem; }
div[data-testid="stColumn"]:has(.auth-form-marker) .stFormSubmitButton > button { background:#5B5FEF; border-radius:10px; height:2.8rem; font-size:.9rem; margin-top:.6rem; }
div[data-testid="stColumn"]:has(.auth-form-marker) .stFormSubmitButton > button:hover { background:#4A4FDB; }
div[data-testid="stColumn"]:has(.auth-form-marker) .stFormSubmitButton > button,
div[data-testid="stColumn"]:has(.auth-form-marker) .stFormSubmitButton > button p,
div[data-testid="stColumn"]:has(.auth-form-marker) .stFormSubmitButton > button span {
    color:#fff !important; -webkit-text-fill-color:#fff !important;
}
div[data-testid="stColumn"]:has(.auth-form-marker) .stFormSubmitButton > button p {
    font-weight:600; font-size:.95rem;
}

.auth-switch { text-align:right; color:var(--muted); font-size:.82rem; padding-top:.45rem; }
.st-key-go_login button, .st-key-go_register button { background:none !important; border:none !important; box-shadow:none !important; padding:.45rem 0 0 !important; min-height:0; justify-content:flex-start; }
.st-key-go_login button, .st-key-go_login button p,
.st-key-go_register button, .st-key-go_register button p { color:#5B5FEF !important; font-weight:600; font-size:.82rem; }
.st-key-go_login button:hover, .st-key-go_register button:hover { text-decoration:underline; }

/* ===== 5. TOPBAR ===== */

.topbar-brand { display:flex; align-items:center; gap:.6rem; font-weight:800; font-size:1.35rem; color:var(--ink); }
.topbar-brand img { height:48px; width:auto; flex:none; }
.tb-logo-fallback { width:32px; height:32px; border-radius:8px; background:var(--violet); color:#fff; display:grid; place-items:center; }

[class*="st-key-nav_"] { padding-top:.55rem; }
[class*="st-key-nav_"] button {
    background:transparent !important; color:#374151 !important; box-shadow:none !important;
    border:0 !important; border-bottom:2px solid transparent !important; border-radius:0 !important;
    font-size:.88rem; font-weight:500; min-height:2.2rem; padding:0 .4rem;
}
[class*="st-key-nav_"] button p { color:inherit !important; white-space:nowrap; font-size:1.02rem !important; font-weight:600; }
[class*="st-key-nav_"] button:hover { color:var(--violet) !important; background:transparent !important; }
[class*="st-key-nav_"][class*="_active"] button { color:var(--violet) !important; border-bottom:2px solid var(--violet) !important; font-weight:600; }

.topbar-user { display:flex; align-items:center; justify-content:flex-end; gap:.7rem; }
.tu-text { display:flex; flex-direction:column; align-items:flex-end; line-height:1.25; min-width:0; }

.tu-text b { font-size:.98rem; color:var(--ink); }
.tu-text small { font-size:.76rem; color:var(--muted); max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.tu-avatar { width:44px; height:44px; border-radius:50%; flex:none; background:var(--violet); color:#fff; font-weight:700; font-size:1.05rem; display:grid; place-items:center; }


/* ===== 6. ANALYSIS PAGE ===== */
.page-title { font-size:1.5rem; font-weight:800; color:var(--ink); margin:.2rem 0 .25rem; }
.page-sub { font-size:.86rem; color:var(--muted); margin:0 0 1.1rem; line-height:1.5; }
.field-label { font-size:.78rem; font-weight:600; color:#1f2937; margin:.2rem 0 .35rem; }
div[data-testid="stColumn"]:has(.analysis-marker) [data-testid="stWidgetLabel"] p { font-size:.78rem; font-weight:600; color:#1f2937; }
div[data-testid="stColumn"]:has(.analysis-marker) .stTextInput div[data-baseweb="input"],
div[data-testid="stColumn"]:has(.analysis-marker) div[data-baseweb="select"] > div { background:#fff !important; border:1px solid #d9d7e5 !important; border-radius:8px !important; }
div[data-testid="stColumn"]:has(.analysis-marker) .stTextInput input { font-size:.88rem; }

div[data-testid="stVerticalBlockBorderWrapper"]:has(.editor-marker) { background:#fff; border:1px solid #d9d7e5 !important; border-radius:12px; padding:.5rem .7rem .2rem; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.editor-marker) .stTextArea div[data-baseweb="textarea"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.editor-marker) .stTextArea div[data-baseweb="base-input"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.editor-marker) .stTextArea textarea {
    border:0 !important; box-shadow:none !important; background:transparent !important;
    font-size:.92rem; line-height:1.7; color:var(--ink) !important;
}
.editor-footer { border-top:1px solid #eeedf4; padding:.6rem .1rem .3rem; margin-top:.2rem; font-size:.74rem; color:var(--muted); }
.editor-footer b { color:var(--ink); }

.st-key-clear_draft button { background:#fff !important; color:var(--ink) !important; border:1px solid #d9d7e5 !important; border-radius:8px !important; min-height:2.5rem; }
.st-key-clear_draft button:hover { border-color:var(--violet) !important; color:var(--violet) !important; }
.st-key-run_analysis button { border-radius:8px !important; min-height:2.5rem; font-size:.85rem; }

.quick-guide { background:#fff; border:1px solid var(--line); border-radius:14px; padding:1.3rem 1.3rem 1.6rem; min-height:600px; }
.qg-head { display:flex; align-items:center; gap:.6rem; font-weight:700; font-size:1rem; color:var(--ink); }
.qg-icon { width:32px; height:32px; border-radius:8px; background:var(--violet-soft); color:var(--violet); display:grid; place-items:center; }
.qg-intro { font-size:.82rem; color:var(--muted); line-height:1.6; margin:1rem 0 0; }
.qg-divider { border:0; border-top:1px solid #eeedf4; margin:1.1rem 0; }
.qg-item { margin-bottom:1.1rem; }
.qg-item h5 { font-size:.85rem; font-weight:700; color:var(--ink); margin:0 0 .25rem; }
.qg-item p { font-size:.78rem; color:var(--muted); line-height:1.55; margin:0; }


/* ===== 6b. PROCESSING PAGE ===== */
.proc-title { color:#5b6475; }
.proc-title span { color:#5b6475; }
div[data-testid="stColumn"]:has(.processing-marker) .stTextInput div[data-baseweb="input"],
div[data-testid="stColumn"]:has(.processing-marker) .stTextInput div[data-baseweb="base-input"],
div[data-testid="stColumn"]:has(.processing-marker) .stTextArea div[data-baseweb="textarea"],
div[data-testid="stColumn"]:has(.processing-marker) .stTextArea div[data-baseweb="base-input"],
div[data-testid="stColumn"]:has(.processing-marker) .stTextArea textarea { background:#eef2f8 !important; }
div[data-testid="stColumn"]:has(.processing-marker) .stTextInput input:disabled,
div[data-testid="stColumn"]:has(.processing-marker) .stTextArea textarea:disabled {
    color:#6b7280 !important; -webkit-text-fill-color:#6b7280 !important; opacity:1; cursor:not-allowed;
}

.processing-panel {
    background:#fff; border:1.5px solid #7c74ff; border-radius:16px;
    padding:1.3rem 1.3rem 1.6rem; min-height:600px; box-shadow:0 6px 20px rgba(99,91,255,.12);
}
.pp-head { display:flex; align-items:center; gap:.7rem; font-size:1rem; color:var(--ink); }
.pp-spin {
    width:30px; height:30px; border-radius:8px; background:var(--violet-soft); position:relative; flex:none;
}
.pp-spin::after {
    content:""; position:absolute; inset:7px; border-radius:50%;
    border:2px solid #cfd2ff; border-top-color:var(--violet); animation:ps-spin .8s linear infinite;
}
.pp-sub { font-size:.74rem; color:var(--muted); margin:.5rem 0 .6rem; }
.pp-bar { height:6px; background:#e5e7eb; border-radius:99px; overflow:hidden; }
.pp-bar div { height:100%; background:var(--violet); border-radius:99px; transition:width .4s ease; }
.pp-line { border:0; border-top:1px solid #eeedf4; margin:1.1rem 0 .6rem; }

.ps { display:flex; gap:.75rem; align-items:flex-start; padding:.6rem 0; }
.ps-icon {
    width:20px; height:20px; border-radius:50%; flex:none; margin-top:2px; box-sizing:border-box;
    display:grid; place-items:center; font-size:.7rem; font-weight:700;
}
.ps-done .ps-icon { background:#dcfce7; color:#16a34a; }
.ps-active .ps-icon { border:2px solid #cfd2ff; border-top-color:var(--violet); animation:ps-spin .8s linear infinite; }
.ps-pending .ps-icon { border:2px solid #cbd5e1; }
.ps-title { font-size:.9rem; font-weight:600; color:var(--ink); }
.ps-active .ps-title { color:var(--violet); }
.ps-pending .ps-title { color:#94a3b8; }
.ps-desc { font-size:.78rem; color:var(--muted); line-height:1.45; }
.ps-pending .ps-desc { color:#94a3b8; }
@keyframes ps-spin { to { transform:rotate(360deg); } }


/* ===== 6c. RESULTS PAGE ===== */
.stApp .page-sub { font-size:.86rem !important; color:var(--muted) !important; margin:0 0 1.1rem !important; }
.stApp .page-sub b { color:var(--ink); }
.badge-done { display:inline-block; vertical-align:middle; margin-left:.5rem; padding:.15rem .5rem; border-radius:6px;
    background:#dcfce7; color:#15803d; font-size:.68rem; font-weight:600; }

/* kartu hasil */
.rc-card { background:#fff; border:1px solid var(--line); border-radius:12px; padding:1.1rem 1.3rem; margin-bottom:1rem; }
.rc-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:.9rem; }
.rc-title { display:flex; align-items:center; gap:.5rem; font-weight:700; font-size:1.02rem; color:var(--ink); }
.rc-head small { font-weight:500; font-size:.76rem; color:#6b7280; }
.rc-body { display:flex; align-items:center; gap:1rem; flex-wrap:wrap; }
.stApp .rc-body p { flex:1; min-width:220px; margin:0; font-size:.86rem; color:var(--muted); line-height:1.5; }
.rc-pill { display:inline-block; padding:.55rem 1rem; border-radius:8px; font-weight:700; font-size:1.05rem; }
.rc-rating { background:#ebeaff; color:#5b54e6; }
.rc-warn { background:#ffefdc; color:#b4470f; }
.rc-tags { display:flex; flex-wrap:wrap; gap:.5rem; }
.rc-tag { padding:.35rem .75rem; border-radius:6px; background:#f1f3f7; color:#374151; font-size:.82rem; font-weight:500; border:1px solid #e5e7eb; }

/* kartu ringkasan di kanan */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.summary-marker) {
    background:#fff; border:1px solid var(--line) !important; border-radius:16px; padding:.9rem .7rem; min-height:480px;
}
.sum-title { font-weight:700; font-size:1.02rem; color:var(--ink); margin-bottom:.8rem; }
.sum-box { background:#f4f5fa; border:1px solid #e5e7eb; border-radius:8px; padding:.9rem 1rem; }
.sum-row { margin-bottom:.8rem; }
.sum-row:last-child { margin-bottom:0; }
.sum-row span { display:block; font-size:.68rem; text-transform:uppercase; letter-spacing:.05em; color:#6b7280; }
.sum-row b { display:block; font-size:.9rem; font-weight:600; color:var(--ink); margin-top:.1rem; line-height:1.45; }
.sum-line { border:0; border-top:1px solid #eeedf4; margin:.4rem 0 .2rem; }

/* dua tombol bawah: tinggi, radius, dan font seragam dengan tombol Copy */
.st-key-res_another button, .st-key-res_history button {
    width:100%; height:42px; min-height:42px; border-radius:8px !important;
    background:#fff !important; border:1px solid #d9d7e5 !important; box-shadow:none !important;
}
.st-key-res_another button p, .st-key-res_history button p {
    font-family:Inter,'Source Sans Pro',sans-serif !important; font-size:15px !important; font-weight:600 !important;
}
.st-key-res_another button { color:var(--ink) !important; }
.st-key-res_history button { color:var(--violet) !important; }
.st-key-res_another button:hover, .st-key-res_history button:hover {
    border-color:var(--violet) !important; color:var(--violet) !important;
}

/* bar persen keyakinan */
.cb-list { margin-top:1rem; display:flex; flex-direction:column; gap:.45rem; }
.cb-row { display:grid; grid-template-columns:minmax(120px, 210px) 1fr 52px; align-items:center; gap:.7rem; }
.cb-label { font-size:.8rem; color:#6b7280; }
.cb-track { height:8px; background:#eef0f5; border-radius:99px; overflow:hidden; }
.cb-track span { display:block; height:100%; background:#c9ccd6; border-radius:99px; }
.cb-val { font-size:.78rem; color:#6b7280; text-align:right; font-variant-numeric:tabular-nums; }
.cb-on .cb-label, .cb-on .cb-val { color:var(--ink); font-weight:600; }
.cb-on .cb-track span { background:var(--violet); }
.stApp .cb-note { margin:.8rem 0 0; font-size:.74rem; color:#6b7280; line-height:1.5; }

/* hasil terjemahan per segmen */
.tr-head { display:flex; align-items:center; gap:.6rem; font-size:.82rem; font-weight:700; color:var(--ink); margin:.9rem 0 .35rem; }
.tr-head span { font-weight:500; color:#6b7280; }
.tr-head .tr-ratio { padding:.08rem .45rem; border-radius:5px; background:#eef0f5; font-size:.72rem; }
.tr-head .tr-low { background:#ffefdc; color:#b4470f; }
.tr-box { background:#f8f9fc; border:1px solid var(--line); border-radius:8px; padding:.6rem .75rem;
    font-size:.8rem; line-height:1.55; color:#374151; max-height:220px; overflow-y:auto; }
.tr-box small { display:block; font-size:.66rem; text-transform:uppercase; letter-spacing:.05em; color:#6b7280; margin-bottom:.25rem; }
.tr-en { background:#f5f4ff; }


/* ===== 6d. HISTORY PAGE ===== */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.hist-search-marker),
div[data-testid="stVerticalBlockBorderWrapper"]:has(.hist-table-marker) {
    background:#fff; border:1px solid var(--line) !important; border-radius:12px;
}
.hist-filter-label { font-size:.82rem; font-weight:600; color:var(--ink); text-align:right; }
.ht-head { font-size:.68rem; font-weight:600; text-transform:uppercase; letter-spacing:.05em; color:#6b7280; padding:.2rem 0; }
.ht-title { font-size:.9rem; font-weight:700; color:var(--ink); }
.ht-cell { font-size:.85rem; color:var(--muted); }
.ht-empty { font-size:.85rem; color:var(--muted); padding:.6rem 0; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.hist-table-marker) div[data-testid="stHorizontalBlock"] {
    border-top:1px solid #eeedf4; padding-top:.45rem;
}
.rating-badge { display:inline-block; padding:.12rem .5rem; border-radius:5px; font-size:.72rem; font-weight:600; background:#f1f3f7; color:#374151; }
.rb-general { background:#e0f2fe; color:#0369a1; }
.rb-teen { background:#ebeaff; color:#5b54e6; }
.rb-mature { background:#ffefdc; color:#b4470f; }
.rb-explicit { background:#fee2e2; color:#b91c1c; }

/* tombol "View Details" dan "Back to History" tampil seperti tautan */
[class*="st-key-hist_view_"] button, .st-key-hist_back button {
    background:transparent !important; border:0 !important; box-shadow:none !important;
    padding:0 !important; min-height:0 !important; justify-content:flex-start;
}
[class*="st-key-hist_view_"] button p, .st-key-hist_back button p {
    color:var(--violet) !important; font-size:.85rem !important; font-weight:600;
}
.st-key-hist_back button p { color:var(--ink) !important; }
[class*="st-key-hist_del_"] button {
    background:transparent !important; border:0 !important; box-shadow:none !important;
    padding:0 !important; min-height:0 !important;
}
[class*="st-key-hist_del_"] button p { color:#dc2626 !important; font-size:.85rem !important; font-weight:600; }
[class*="st-key-hist_del_"] button:hover p { text-decoration:underline; }

.pub-status { font-size:.8rem; font-weight:600; color:#15803d; margin:.2rem 0 .1rem; }
.st-key-work_unpublish button {
    width:100%; height:42px; min-height:42px; border-radius:8px !important;
    background:#fff !important; border:1px solid #fecaca !important; box-shadow:none !important;
}
.st-key-work_unpublish button p { color:#dc2626 !important; font-size:15px !important; font-weight:600 !important; }
.st-key-work_unpublish button:hover { border-color:#dc2626 !important; }


/* ===== 6e. HOME PAGE ===== */


/* ===== 6f. GALLERY ===== */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.gallery-card-marker) {
    background:#fff; border:1px solid var(--line) !important; border-radius:12px;
}
.gc-title { font-size:1rem; font-weight:800; color:var(--ink); line-height:1.35; }
.gc-meta { font-size:.76rem; color:#6b7280; margin:.15rem 0 .55rem; }
.gc-meta b { color:var(--ink); font-weight:600; }
.gc-badges { display:flex; flex-wrap:wrap; gap:.3rem; margin-bottom:.55rem; }
.gc-warn { display:inline-block; padding:.12rem .5rem; border-radius:5px; font-size:.72rem; font-weight:600; background:#ffefdc; color:#b4470f; }
.stApp .gc-snippet { font-size:.8rem; color:var(--muted); line-height:1.55; margin:0 0 .6rem;
    display:-webkit-box; -webkit-line-clamp:4; -webkit-box-orient:vertical; overflow:hidden; min-height:4.9rem; }
.stApp .gc-hidden { font-style:italic; color:#9ca3af; }
.gc-tags { display:flex; flex-wrap:wrap; gap:.3rem; min-height:1.5rem; }
.gc-tag { padding:.15rem .5rem; border-radius:5px; background:#f1f3f7; color:#374151; font-size:.72rem; border:1px solid #e5e7eb; }
.gc-more { background:var(--violet-soft); color:var(--violet); border-color:transparent; }
.gc-stats { display:flex; flex-wrap:wrap; gap:.8rem; font-size:.74rem; color:#6b7280; margin-top:.7rem;
    border-top:1px solid #eeedf4; padding-top:.55rem; }
[class*="st-key-gal_read_"] button, [class*="st-key-home_read_"] button {
    background:transparent !important; border:0 !important; box-shadow:none !important; padding:0 !important; min-height:0 !important;
}
[class*="st-key-gal_read_"] button p, [class*="st-key-home_read_"] button p { color:var(--violet) !important; font-size:.85rem !important; font-weight:600; }
[class*="st-key-gal_read_"] button:hover p, [class*="st-key-home_read_"] button:hover p { text-decoration:underline; }

/* halaman baca cerita */
.story-body { background:#fff; border:1px solid var(--line); border-radius:12px; padding:1.4rem 1.6rem; }
.stApp .story-body p { font-size:.95rem; line-height:1.85; color:#1f2937; margin:0 0 1rem; }
.st-key-work_like button, .st-key-work_liked button {
    width:100%; height:42px; min-height:42px; border-radius:8px !important; box-shadow:none !important;
}
.st-key-work_like button { background:#fff !important; border:1px solid #d9d7e5 !important; }
.st-key-work_like button p { color:var(--ink) !important; font-size:15px !important; font-weight:600 !important; }
.st-key-work_like button:hover { border-color:#e11d48 !important; }
.st-key-work_liked button { background:#fff1f2 !important; border:1px solid #fecdd3 !important; }
.st-key-work_liked button p { color:#e11d48 !important; font-size:15px !important; font-weight:600 !important; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.age-gate-marker) {
    background:#fff; border:1px solid #fed7aa !important; border-radius:12px; padding:.6rem .8rem;
}
.ag-title { font-size:1.05rem; font-weight:800; color:#b4470f; }
.stApp .ag-text { font-size:.86rem; color:var(--muted); line-height:1.55; margin:.3rem 0 .6rem; }
.st-key-age_no button { background:#fff !important; border:1px solid #d9d7e5 !important; }
.st-key-age_no button p { color:var(--ink) !important; }

/* komentar */
.cm-title { font-size:1.05rem; font-weight:800; color:var(--ink); margin:1.6rem 0 .6rem; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.comment-marker) { background:#fff; border:1px solid var(--line) !important; border-radius:10px; }
.cm-head { display:flex; align-items:center; gap:.5rem; font-size:.85rem; color:var(--ink); }
.cm-head small { color:#9ca3af; font-size:.74rem; margin-left:auto; }
.cm-author { padding:.05rem .4rem; border-radius:4px; background:var(--violet-soft); color:var(--violet); font-size:.68rem; font-weight:600; }
.cm-text { font-size:.86rem; color:#374151; line-height:1.6; margin-top:.3rem; white-space:pre-wrap; }
[class*="st-key-cm_del_"] button {
    background:transparent !important; border:0 !important; box-shadow:none !important; padding:0 !important; min-height:0 !important;
}
[class*="st-key-cm_del_"] button p { color:#dc2626 !important; font-size:.78rem !important; font-weight:600; }

/* tautan Back to Home di halaman login/register, tombol daftar di topbar */
.st-key-go_home button { background:none !important; border:none !important; box-shadow:none !important; padding:.2rem 0 0 !important; min-height:0; }
.st-key-go_home button p { color:#6b7280 !important; font-size:.8rem; font-weight:600; }
.st-key-go_home button:hover p { color:#5B5FEF !important; text-decoration:underline; }
[class*="st-key-tb_register"] { padding-top:.55rem; }
.st-key-tb_register button { border-radius:8px !important; min-height:2.3rem; }

/* ===== 6h. WORKSPACE ===== */
.st-key-ws_new button { min-height:2.6rem; border-radius:8px !important; padding:0 1.2rem; white-space:nowrap; }
.ws-counts { font-size:.78rem; color:#6b7280; margin:.1rem 0 .8rem; }
.ws-counts b { color:var(--ink); }
.ws-muted { font-size:.76rem; color:#9ca3af; font-style:italic; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ws-card-marker),
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ws-section-marker) {
    background:#fff; border:1px solid var(--line) !important; border-radius:12px;
}
.wc-top { display:flex; align-items:center; gap:.4rem; flex-wrap:wrap; margin-bottom:.45rem; }
.wc-title { font-size:1rem; font-weight:800; color:var(--ink); line-height:1.35; }
.wc-fandom { font-size:.78rem; color:#6b7280; margin:.1rem 0 .5rem; }
.wc-stats { display:flex; flex-wrap:wrap; gap:.7rem; font-size:.74rem; color:#6b7280; border-top:1px solid #eeedf4; padding-top:.5rem; }
.status-badge { display:inline-block; padding:.12rem .5rem; border-radius:5px; font-size:.72rem; font-weight:700; background:#f1f3f7; color:#374151; }
.st-draft { background:#f1f3f7; color:#4b5563; }
.st-ongoing { background:#dbeafe; color:#1d4ed8; }
.st-complete { background:#dcfce7; color:#15803d; }
.st-hiatus { background:#fef3c7; color:#b45309; }
.st-key-ws_edit button { background:#fff !important; border:1px solid #d9d7e5 !important; }
.st-key-ws_edit button p { color:var(--ink) !important; }
.ws-section { font-size:1.02rem; font-weight:800; color:var(--ink); margin-bottom:.3rem; }
.ws-chips { display:flex; flex-wrap:wrap; gap:.3rem; margin-top:.25rem; }
.ws-notes-title { margin-top:1rem; }
.ws-notes { font-size:.82rem; color:#374151; white-space:pre-wrap; line-height:1.55; }
.ch-row { padding:.35rem 0; }
.ch-title { font-size:.92rem; font-weight:700; color:var(--ink); }
.ch-meta { font-size:.74rem; color:#6b7280; margin-top:.1rem; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ws-section-marker) div[data-testid="stHorizontalBlock"] + div[data-testid="stHorizontalBlock"] {
    border-top:1px solid #eeedf4; padding-top:.35rem;
}
[class*="st-key-ws_ch_open_"] button, [class*="st-key-ws_ch_up_"] button, [class*="st-key-ws_ch_down_"] button,
.st-key-ch_prev button, .st-key-ch_next button {
    background:#fff !important; border:1px solid #d9d7e5 !important; min-height:2rem; padding:0 .7rem;
}
[class*="st-key-ws_ch_open_"] button p { color:var(--violet) !important; font-weight:600; }
[class*="st-key-ws_ch_up_"] button p, [class*="st-key-ws_ch_down_"] button p,
.st-key-ch_prev button p, .st-key-ch_next button p { color:var(--ink) !important; }
[class*="st-key-ws_ch_"] button:disabled, .st-key-ch_prev button:disabled, .st-key-ch_next button:disabled { opacity:.4; }
.st-key-ws_ch_new button { white-space:nowrap; }
.ws-crumb { font-size:.78rem; color:#6b7280; font-weight:600; }
/* status analisis per bab */
.ch-status { display:flex; flex-wrap:wrap; align-items:center; gap:.35rem; margin-top:.3rem; }
.cs { display:inline-block; padding:.08rem .45rem; border-radius:5px; font-size:.7rem; font-weight:600; }
.cs-empty { background:#f1f3f7; color:#9ca3af; }
.cs-new { background:#f1f3f7; color:#6b7280; }
.cs-changed { background:#ffefdc; color:#b4470f; }
.cs-tags { font-size:.74rem; color:#4b5563; }
[class*="st-key-ws_ch_an_"] button { background:#fff !important; border:1px solid #c7c3ff !important; min-height:2rem; padding:0 .7rem; }
[class*="st-key-ws_ch_an_"] button p { color:var(--violet) !important; font-weight:600; }
[class*="st-key-ws_ch_res_"] button { background:#fff !important; border:1px solid #d9d7e5 !important; min-height:2rem; padding:0 .7rem; }
[class*="st-key-ws_ch_res_"] button p { color:var(--ink) !important; }
/* metadata cerita gabungan */
.sm-grid { display:grid; grid-template-columns:90px 1fr; gap:.7rem 1rem; align-items:center; margin:.4rem 0 .2rem; }
.sm-label { font-size:.72rem; text-transform:uppercase; letter-spacing:.05em; color:#6b7280; font-weight:600; }
.sm-pills { display:flex; flex-wrap:wrap; align-items:center; gap:.35rem; }
.rc-pill.sm { padding:.3rem .65rem; font-size:.82rem; }
.sm-from { font-size:.7rem; color:#9ca3af; margin-left:.35rem; font-weight:500; }
.sm-pending { font-size:.8rem; font-weight:600; color:#b4470f; background:#fff7ed; border:1px solid #fed7aa;
    border-radius:8px; padding:.45rem .7rem; margin:.4rem 0 .2rem; }
.st-key-wsa_all button { margin-top:.3rem; }
.ws-progress { min-height:0; }
.ps-error .ps-icon { background:#fee2e2; color:#dc2626; }
.ps-error .ps-title { color:#dc2626; }
.ps-title small { font-weight:500; color:#9ca3af; }
/* label sumber analisis di History */
.ht-src { display:flex; flex-wrap:wrap; align-items:center; gap:.35rem; margin-top:.2rem; }
.src-badge { display:inline-block; padding:.05rem .4rem; border-radius:4px; font-size:.66rem; font-weight:700; }
.src-quick { background:#f1f3f7; color:#6b7280; }
.src-ws { background:#ede9fe; color:#6d28d9; }
.src-where { font-size:.72rem; color:#6b7280; }
.st-key-res_ws button { width:100%; height:42px; min-height:42px; border-radius:8px !important;
    background:#fff !important; border:1px solid #c7c3ff !important; box-shadow:none !important; }
.st-key-res_ws button p { color:var(--violet) !important; font-size:15px !important; font-weight:600 !important; }
/* log analisis cerita */
.lg-note { margin-top:0 !important; margin-bottom:.6rem !important; }
.lg-wrap { overflow-x:auto; border:1px solid var(--line); border-radius:10px; }
.lg-table { width:100%; min-width:860px; border-collapse:collapse; font-size:.76rem; color:#374151; }
.lg-table th { background:#f8f9fc; text-align:left; font-size:.66rem; font-weight:600; text-transform:uppercase;
    letter-spacing:.05em; color:#6b7280; padding:.55rem .6rem; border-bottom:1px solid var(--line); white-space:nowrap; }
.lg-table td { padding:.55rem .6rem; border-bottom:1px solid #eeedf4; vertical-align:top; line-height:1.45; }
.lg-table tr:last-child td { border-bottom:0; }
.lg-table td small { color:#9ca3af; }
.lg-date { white-space:nowrap; color:#6b7280; }
.lg-table td.lg-story { color:#6d28d9; }
.lg-deleted td { color:#9ca3af; }
.lg-deleted td b { text-decoration:line-through; }
.ch-of { font-size:.95rem; font-weight:500; color:#9ca3af; }


/* footer & disclaimer */
.app-footer { margin-top:3rem; padding-top:1rem; border-top:1px solid var(--line); text-align:center;
    font-size:.74rem; color:#6b7280; line-height:1.5; }
.auth-disclaimer { font-size:.72rem; color:rgba(228,226,250,.75); line-height:1.5; max-width:620px; }

/* ===== 6g. GLOSSARY ===== */
.gl-jump { display:flex; gap:2rem; flex-wrap:wrap; border-bottom:1px solid var(--line); margin:.6rem 0 1.6rem; }
.stApp .gl-jump a { color:#202033; text-decoration:none; font-size:.95rem; font-weight:500; padding:.2rem 0 .8rem; border-bottom:2px solid transparent; }
.stApp .gl-jump a:hover { color:var(--violet); border-bottom-color:var(--violet); }
.stApp h2.gl-h2 { display:flex; align-items:center; gap:.7rem; font-size:1.55rem; font-weight:600; color:var(--ink); margin:0 0 .35rem; padding:0; scroll-margin-top:1rem; }
.gl-count { font-size:.78rem; font-weight:600; color:#4b5563; background:#f3f4f6; border-radius:6px; padding:.2rem .55rem; }
.stApp .gl-lead { font-size:.95rem; color:var(--muted); margin:0 0 1.1rem; line-height:1.55; }
.gl-grid { display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:1.1rem; margin-bottom:2.4rem; }
@media (max-width: 1100px) { .gl-grid, .gl-warn-grid { grid-template-columns:repeat(2, minmax(0, 1fr)); } }
@media (max-width: 640px) { .gl-grid, .gl-warn-grid { grid-template-columns:1fr; } .gl-how { grid-template-columns:1fr !important; } }
.gl-card > .bdg { align-self:flex-start; }
.gl-card { background:#fff; border:1px solid var(--line); border-radius:12px; padding:1.4rem 1.4rem 1.3rem; display:flex; flex-direction:column; }
.stApp .gl-card p.gl-desc { margin:.85rem 0 0; font-size:.92rem; color:#374151; line-height:1.6; flex:1; }
.gl-example { margin-top:1rem; padding-top:.9rem; border-top:1px solid #eeedf4; font-size:.84rem; color:var(--muted); }
.gl-cat { font-size:.72rem; text-transform:uppercase; letter-spacing:.05em; color:var(--violet); font-weight:600; }
.gl-name { font-size:1.12rem; font-weight:600; color:var(--ink); margin-top:.45rem; }
.stApp .gl-card .gl-name + p.gl-desc { margin-top:.45rem; }
.gl-ex-label { margin-top:1rem; font-size:.7rem; text-transform:uppercase; letter-spacing:.05em; color:#505365; font-weight:600; }
.gl-ex { margin-top:.25rem; font-size:.86rem; color:var(--violet); line-height:1.5; }
.gl-panel { background:#fff; border:1px solid var(--line); border-radius:12px; padding:1.6rem 1.6rem 1.5rem; margin-bottom:2.4rem; }
.gl-warn-grid { display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:1rem; margin-bottom:1.1rem; }
.gl-warn { background:#f8f9fc; border-radius:10px; padding:1rem 1.1rem; }
.gl-warn-name { font-weight:600; font-size:.95rem; color:var(--ink); }
.stApp .gl-warn p { margin:.35rem 0 0; font-size:.88rem; color:var(--muted); line-height:1.55; }
.gl-note { display:flex; gap:.6rem; align-items:flex-start; font-size:.88rem; color:#b86010; background:#fff3e5; border-radius:10px; padding:.85rem 1rem; line-height:1.55; }
.gl-note svg { flex:none; margin-top:.15rem; }
.gl-how { display:grid; grid-template-columns:minmax(0, 1fr) minmax(0, 1.8fr); gap:2.5rem; background:#efeeff; border-radius:14px; padding:2rem 2.2rem; margin:.4rem 0 1rem; scroll-margin-top:1rem; }
.stApp .gl-how-left h2.gl-h2 { margin:.8rem 0 .5rem; }
.stApp .gl-how-left p { font-size:.95rem; color:#374151; line-height:1.6; margin:0; }
.gl-how-right { display:flex; flex-direction:column; gap:1.1rem; }
.gl-step { display:flex; gap:.9rem; align-items:flex-start; }
.gl-step-n { flex:none; width:28px; height:28px; border-radius:50%; background:#fff; color:var(--violet); font-weight:700; font-size:.85rem; display:flex; align-items:center; justify-content:center; }
.gl-step-t { font-weight:600; font-size:.98rem; color:var(--ink); }
.stApp .gl-step p { margin:.2rem 0 0; font-size:.9rem; color:#505365; line-height:1.55; }
.st-key-qg_glossary button { background:#fff !important; border:1px solid #d9d7e5 !important; width:100%; margin-top:.6rem; }
.st-key-qg_glossary button p { color:var(--violet) !important; font-weight:600; }
.st-key-qg_glossary button:hover { border-color:var(--violet) !important; }

/* catatan panjang cerita di bawah editor */
.editor-footer { display:flex; justify-content:space-between; align-items:center; gap:1rem; flex-wrap:wrap; }
.len-warn { color:#b4470f; font-weight:500; }
[class*="st-key-hist_view_"] button:hover p, .st-key-hist_back button:hover p { text-decoration:underline; color:var(--violet) !important; }

.sum-snippet { font-size:.82rem; font-style:italic; color:var(--muted); line-height:1.55; }
.st-key-res_rerun button {
    width:100%; height:42px; min-height:42px; border-radius:8px !important;
    background:#fff !important; border:1px solid #d9d7e5 !important; box-shadow:none !important;
}
.st-key-res_rerun button p { color:var(--ink) !important; font-size:15px !important; font-weight:600 !important; }
.st-key-res_rerun button:hover { border-color:var(--violet) !important; }
.st-key-res_rerun button:hover p { color:var(--violet) !important; }





/* ===== 8. DESAIN MOCKUP FIGMA (warna & ukuran diambil dari mockup) ===== */
.stApp, .stApp p, .stApp label, .stApp button, .stApp input, .stApp textarea { font-family:'Inter', sans-serif; }
.ic { vertical-align:-3px; flex:none; }
.ic-box { display:inline-grid; place-items:center; width:42px; height:42px; border-radius:10px; background:#efeeff; flex:none; }
[data-testid="stElementContainer"]:has(> div > div > .bc-marker),
[data-testid="stElementContainer"]:has(.ch-actions-marker) { display:none; }

/* kolom isian putih bergaris (mockup) */
.stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"], .stApp [data-baseweb="select"] > div,
.stApp [data-baseweb="textarea"], .stApp .stTextArea textarea,
.stApp [data-testid="stTextInputRootElement"], .stApp [data-testid="stTextAreaRootElement"] { background:#fff !important; }
.stApp [data-baseweb="input"], .stApp [data-baseweb="select"] > div, .stApp [data-baseweb="textarea"] {
    border-color:var(--line) !important; border-radius:8px !important; }
.stApp [data-baseweb="input"] input { min-height:2.6rem; }

/* badge */
.bdg { display:inline-block; padding:.22rem .62rem; border-radius:6px; font-size:.78rem; font-weight:600; line-height:1.35; white-space:nowrap; }
.bdg-violet { background:#efeeff; color:#635bff; }
.bdg-orange { background:#fff3e5; color:#b86010; }
.bdg-blue { background:#eff6ff; color:#2563eb; }
.bdg-green { background:#eaf7f1; color:#237c64; }
.bdg-red { background:#fff0f1; color:#d04452; }
.bdg-grey { background:#f3f4f6; color:#4b5563; }

/* judul halaman */
.pg-kicker { font-size:.78rem; letter-spacing:.03em; text-transform:uppercase; color:#505365; margin:.4rem 0 .45rem; }
.stApp h1.pg-h1 { font-size:2.15rem; font-weight:700; color:var(--ink); line-height:1.2; margin:0; padding:0; letter-spacing:-.01em; }
.stApp .pg-sub { font-size:.95rem; color:#505365; margin:.55rem 0 1.2rem; }
[class*="st-key-bc_"] button p { font-size:.82rem !important; color:#505365 !important; font-weight:400 !important; }
[class*="st-key-bc_"] button:hover p { color:var(--violet) !important; }
.bc-sep { font-size:.82rem; color:#9ca3af; margin:0 .45rem; }
.bc-current { font-size:.82rem; color:#505365; }

/* topbar: putih penuh selebar layar */
.st-key-topbar {
    background:#fff; box-shadow:0 0 0 100vmax #fff; clip-path:inset(0 -100vmax); border-bottom:1px solid var(--line);
    padding:0; margin:-1.2rem 0 2rem;
}
.tb-logo img { height:38px; width:auto; display:block; }
.st-key-tb_brand button p { font-size:1.35rem !important; font-weight:500 !important; color:var(--ink) !important; }
[class*="st-key-nav_"] { padding-top:0; }
[class*="st-key-nav_"] button { padding:0 .2rem !important; min-height:4.9rem; }
[class*="st-key-nav_"] button p { font-size:.92rem !important; font-weight:500 !important; color:#3c3c4d; }
[class*="st-key-nav_"][class*="_active"] button p { color:var(--violet) !important; }
.tb-user { display:flex; align-items:center; gap:.7rem; font-size:.9rem; color:#505365; transform:translateY(-8px); }
.tb-avatar { width:36px; height:36px; border-radius:50%; background:#efeeff; color:var(--violet); font-weight:700;
    font-size:.8rem; display:grid; place-items:center; }
.st-key-tb_login button p { font-size:.92rem !important; font-weight:500 !important; color:#3c3c4d !important; }
.st-key-tb_register button { min-height:2.7rem; padding:0 1.2rem; }

/* kartu umum */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ws-section-marker),
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ws-card-marker),
div[data-testid="stVerticalBlockBorderWrapper"]:has(.form-card-marker) {
    background:#fff; border:1px solid var(--line) !important; border-radius:12px; padding:.6rem .75rem;
}
.card-title { display:flex; align-items:center; justify-content:space-between; gap:.6rem; font-size:1.2rem;
    font-weight:500; color:var(--ink); margin:.1rem 0 .9rem; }
.card-title small { font-size:.78rem; font-weight:400; color:#6b6e80; }
.card-title .ic { vertical-align:-2px; }
.card-title.start { justify-content:flex-start; }
.count-pill { display:inline-block; margin-right:auto; padding:.08rem .5rem; border-radius:6px; background:#f3f4f6;
    font-size:.78rem; font-weight:600; color:#3c3c4d; }
.chip { display:inline-block; padding:.28rem .62rem; border-radius:6px; background:#f3f4f6; color:#3c3c4d; font-size:.8rem; font-weight:500; }
.chips { display:flex; flex-wrap:wrap; gap:.4rem; }
.stApp [data-testid="stWidgetLabel"] p { font-size:.88rem; font-weight:600; color:var(--ink); }
.stApp .field-help { font-size:.78rem; color:#6b6e80; margin:-.5rem 0 .4rem; }

/* workspace: statistik, filter, kartu cerita */
.ws-stats { display:grid; grid-template-columns:repeat(3, 1fr); gap:1.25rem; margin:.6rem 0 1.6rem; }
.ws-stat { display:flex; align-items:center; gap:1rem; background:#fff; border:1px solid var(--line); border-radius:12px; padding:1.35rem 1.25rem; }
.ws-stat-n { font-size:1.6rem; color:var(--ink); line-height:1.15; }
.ws-stat-l { font-size:.84rem; color:#505365; margin-top:.15rem; }
.ws-count { text-align:right; font-size:.86rem; color:#505365; }
.ws-empty { display:flex; flex-direction:column; align-items:center; gap:.5rem; text-align:center; padding:3rem 1rem;
    background:#fff; border:1px dashed #d9d7e5; border-radius:12px; color:#505365; font-size:.9rem; }
.ws-empty b { color:var(--ink); font-size:1.05rem; font-weight:600; }
.wc-top { display:flex; justify-content:space-between; align-items:center; gap:.5rem; }
.wc-title { font-size:1.25rem; font-weight:500; color:var(--ink); line-height:1.3; margin:.85rem 0 .3rem; }
.wc-fandom { font-size:.88rem; color:var(--violet); margin-bottom:.7rem; }
.stApp .wc-summary { font-size:.88rem; color:#505365; line-height:1.55; margin:0 0 .75rem; min-height:2.73rem;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.wc-meta { display:flex; align-items:center; gap:.85rem; font-size:.8rem; color:#6b6e80; }
.wc-meta .ic { margin-right:-.45rem; }
.wc-line { border:0; border-top:1px solid #eeeff3; margin:1rem 0 .2rem; }
.wc-edited { font-size:.78rem; color:#6b6e80; }
[class*="st-key-ws_open_"] button { min-height:2.2rem; padding:0 .85rem; font-size:.85rem; }
.ws-private { display:flex; justify-content:center; align-items:center; gap:.5rem; font-size:.84rem; color:#505365; margin:2rem 0 0; }
.st-key-ws_new button { min-height:2.75rem; padding:0 1.2rem; font-size:.95rem; }

/* form cerita + kartu samping */
.side-card { background:#fff; border:1px solid var(--line); border-radius:12px; padding:1.4rem 1.4rem 1.3rem; margin-bottom:1.1rem; }
.side-card hr { border:0; border-top:1px solid #eeeff3; margin:1.1rem 0; }
.side-title { display:flex; align-items:center; gap:.5rem; font-size:1.15rem; font-weight:500; color:var(--ink); margin:.2rem 0 .7rem; }
.side-card .ic-box + .side-title { margin-top:1.2rem; }
.stApp .side-card p { font-size:.9rem; color:#505365; line-height:1.6; margin:0; }
.side-steps { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:1rem; font-size:.88rem; color:var(--ink); }
.side-steps span { display:inline-grid; place-items:center; width:24px; height:24px; border-radius:50%; background:#efeeff;
    color:var(--violet); font-size:.72rem; font-weight:600; margin-right:.8rem; }
.side-note { background:#efeeff; border-radius:12px; padding:1.3rem 1.4rem; }
.side-note b { display:block; font-size:1.02rem; font-weight:500; color:var(--violet); margin-bottom:.5rem; }
.stApp .side-note p { font-size:.86rem; color:#505365; line-height:1.6; margin:0; }
.side-label { font-size:.88rem; font-weight:600; color:var(--ink); margin-bottom:.5rem; }
.side-lines { font-size:.88rem; color:#505365; line-height:1.7; }
.stApp .side-text { font-size:.9rem; color:#505365; line-height:1.7; }
.side-foot { font-size:.74rem; color:#6b6e80; margin-top:1rem; }
.form-foot-note { font-size:.82rem; color:#6b6e80; }
.st-key-ws_glossary button p { color:var(--violet) !important; font-size:.88rem !important; font-weight:500 !important; }

/* detail cerita */
.sd-head { display:flex; align-items:center; gap:.8rem; flex-wrap:wrap; }
.stApp .sd-sub { font-size:.95rem; color:#505365; margin:.3rem 0 1.6rem; }
.sd-fandom { color:var(--violet); margin-right:1.2rem; }
.st-key-ws_edit button, .st-key-ws_delete button { min-height:2.75rem; padding:0 1rem; }
.sm-rating { display:flex; justify-content:space-between; align-items:center; gap:1rem; }
.sm-label { font-size:.78rem; text-transform:uppercase; letter-spacing:.03em; color:#505365; }
.sm-hint { font-size:.9rem; color:var(--ink); margin-top:.3rem; }
.sm-rating-val { display:flex; align-items:center; gap:1rem; }
.sm-rating-val small, .sm-warn small { font-size:.82rem; color:#6b6e80; }
.sm-line { border:0; border-top:1px solid #eeeff3; margin:1.3rem 0 .4rem; }
.sm-sub { font-size:.9rem; font-weight:600; color:var(--ink); margin:1.1rem 0 .6rem; }
.sm-row { display:flex; flex-wrap:wrap; align-items:center; gap:.5rem; }
.sm-warn { display:inline-flex; align-items:center; gap:.7rem; margin-right:.6rem; }
.sm-tag { display:inline-flex; align-items:center; gap:.4rem; padding:.3rem .65rem; border-radius:6px; background:#efeeff;
    color:var(--violet); font-size:.82rem; }
.sm-tag b { font-size:.72rem; font-weight:700; }
.sm-foot { font-size:.82rem; color:#505365; }
.sm-note-warn { color:#b86010; font-weight:600; }
.stApp .sm-empty { margin:0 0 .6rem; }
.st-key-wsa_all button { min-height:2.75rem; padding:0 1.1rem; }
.ch-row { display:flex; align-items:center; gap:1rem; border-top:1px solid #eeeff3; padding-top:1.2rem; margin-top:.35rem; }
.ch-row.ch-first { border-top:0; padding-top:.2rem; margin-top:0; }
.ch-num { display:grid; place-items:center; width:44px; height:44px; border-radius:10px; background:#f7f8fc;
    border:1px solid var(--line); color:#505365; font-size:1.05rem; flex:none; }
.ch-body { flex:1; min-width:0; }
.stApp .ch-title { font-size:1rem; font-weight:500; color:var(--ink); }
.ch-meta { font-size:.8rem; color:#6b6e80; margin-top:.15rem; }
.ch-badges { display:flex; gap:.5rem; flex:none; }
[class*="st-key-ws_ch_open_"] button, [class*="st-key-ws_ch_an_"] button, [class*="st-key-ws_ch_res_"] button,
[class*="st-key-ws_ch_up_"] button, [class*="st-key-ws_ch_down_"] button {
    background:#fff !important; border:1px solid var(--line) !important; min-height:2.3rem; padding:0 .8rem;
}
[class*="st-key-ws_ch_"] button p { font-size:.84rem !important; font-weight:500 !important; color:#3c3c4d !important; }
[class*="st-key-ws_ch_del_"] button { padding:0 .6rem !important; }
[class*="st-key-ws_ch_del_"] button p { color:#3c3c4d !important; }
[class*="st-key-ws_ch_"] button:disabled { opacity:.45; }
.st-key-ws_ch_new button { min-height:2.3rem; padding:0 .8rem; }
.st-key-ws_ch_new button p { font-size:.85rem !important; }
.stApp .ch-note { font-size:.78rem; color:#6b6e80; margin:.9rem 0 .2rem; }

/* pop-up */
.stApp .dlg-text { font-size:.92rem; color:#505365; line-height:1.6; margin:0 0 .4rem; }
.stApp .dlg-note { font-size:.8rem; color:#6b6e80; line-height:1.55; margin:.2rem 0 .4rem; }

/* log analisis */
.lg-title .lg-count { font-size:.82rem; font-weight:400; color:#6b6e80; }
.stApp .lg-sub { font-size:.84rem; color:#505365; margin:-.6rem 0 1rem; }
.lg-wrap { border:0; border-radius:0; }
.lg-table { min-width:900px; font-size:.86rem; }
.lg-table th { background:#f9fafc; text-transform:none; letter-spacing:0; font-size:.82rem; font-weight:600; color:#3c3c4d;
    padding:.75rem .9rem; border-bottom:0; }
.lg-table td { padding:1rem .9rem; color:#3c3c4d; border-bottom:1px solid #eeeff3; vertical-align:middle; }
.lg-table td.lg-ch { font-weight:500; color:var(--ink); }
.stApp .lg-table th, .stApp .lg-table td { border-left:0 !important; border-right:0 !important; border-top:0 !important; }
.stApp .lg-table th { border-bottom:0 !important; }
.lg-table td.lg-change { color:var(--violet); }
.lg-date { color:#3c3c4d; }

/* ===== 7. RESPONSIVE ===== */
@media (max-width: 760px) { .block-container { padding:1rem; } }
@media (max-width: 900px) {
    div[data-testid="stColumn"]:has(.auth-art-marker),
    div[data-testid="column"]:has(.auth-art-marker) { display:none; }
}
/* ===== B1 CHAPTER EDITOR ===== */
/* halaman bab (mockup "Chapter editor") */
.ch-bignum { width:52px; height:56px; border-radius:10px; background:#efeeff; color:#635bff; font-size:1.55rem; font-weight:600;
  display:flex; align-items:center; justify-content:center; }
.st-key-ch_head { margin:.6rem 0 1.2rem; }
.ch-kicker + * { margin-top:0; }
.ch-kicker { font-size:.74rem; font-weight:500; letter-spacing:.03em; text-transform:uppercase; color:#505365; margin:0 0 .15rem .1rem; }
.st-key-ch_head [data-testid="stTextInputRootElement"] { border:0 !important; background:transparent !important; box-shadow:none !important; }
.st-key-ch_head [data-testid="stTextInputRootElement"] input { font-size:2rem !important; font-weight:500 !important; color:#202033 !important;
  padding:.1rem .1rem !important; background:transparent !important; }
.st-key-ch_head [data-testid="stTextInputRootElement"]:focus-within { box-shadow:inset 0 -2px 0 #c7c3ff !important; }
.st-key-ch_head [data-testid="InputInstructions"] { display:none; }
.ch-of-pill { display:inline-block; white-space:nowrap; font-size:.82rem; font-weight:600; color:#202033; background:#f3f4f6;
  border-radius:6px; padding:.25rem .6rem; }
.stApp p.ch-save-note { display:flex; align-items:center; justify-content:center; gap:.45rem; font-size:.84rem; color:#505365;
  margin:1.4rem 0 1rem; }
.stApp .fmed-area, .stApp .fmed-area p, .stApp .fmed-area li, .stApp .fmed-area h2, .stApp .fmed-area blockquote {
  font-family:'Source Serif 4', Georgia, 'Times New Roman', serif; }
.stApp .fmed-area p { font-size:1.2rem; line-height:1.75; color:#202033; margin:0 0 1.35rem; }
.st-key-ch_head [data-testid="stTextInputRootElement"] { height:auto !important; min-height:0 !important; }
.st-key-ch_head [data-testid="stTextInputRootElement"] input { height:auto !important; line-height:1.25 !important; }
.st-key-ch_head .ch-kicker { margin-bottom:.3rem; }
/* ===== /B1 CHAPTER EDITOR ===== */
/* ===== B2 ANALYSIS PROGRESS ===== */
/* halaman progres analisis Workspace (mockup "Analysis progress") */
.ap-top { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; margin:.4rem 0 .4rem; }
.ap-top .bdg { margin-top:1.1rem; }
.ap-card { background:#fff; border:1px solid var(--line); border-radius:12px; padding:1.5rem 1.5rem 1.3rem; margin-bottom:1.5rem; }
.ap-story { display:flex; align-items:center; gap:1rem; }
.ap-story .ic-box { width:46px; height:46px; }
.ap-story-t { flex:1; min-width:0; }
.ap-story-title { font-size:1.25rem; font-weight:500; color:var(--ink); }
.ap-story-meta { font-size:.84rem; color:var(--muted); margin-top:.2rem; }
.ap-percent { font-size:1.9rem; font-weight:500; color:var(--violet); }
.ap-bar { height:8px; background:#efeeff; border-radius:99px; overflow:hidden; margin:1.4rem 0 1rem; }
.ap-bar div { height:100%; background:var(--violet); border-radius:99px; transition:width .5s ease; }
.ap-status { display:flex; justify-content:space-between; gap:1rem; flex-wrap:wrap; font-size:.88rem; color:var(--muted); }
.ap-status b { color:var(--ink); font-weight:600; }
.ap-foot { border-top:1px solid #eeedf4; margin-top:1.1rem; padding-top:1rem; font-size:.82rem; color:var(--muted); }
.ap-card-title { font-size:1.25rem; font-weight:500; color:var(--ink); margin-bottom:.6rem; }
.ap-row { display:flex; gap:1rem; padding:1.1rem 0; border-top:1px solid #eeedf4; }
.ap-card-title + .ap-row { border-top:0; }
.ap-lead { flex:none; width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-weight:700; }
.ap-done .ap-lead { background:#eaf7f1; color:#237c64; }
.ap-active .ap-lead { border:2px solid #dcd9ff; border-top-color:var(--violet); animation:ps-spin .9s linear infinite; }
.ap-waiting .ap-lead { background:#f3f4f6; color:#6b7280; }
.ap-error .ap-lead { background:#fff0f1; color:#d04452; }
.ap-main { flex:1; min-width:0; }
.ap-head { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; }
.ap-title { font-size:.98rem; font-weight:600; color:var(--ink); }
.ap-meta { font-size:.84rem; color:var(--muted); margin-top:.15rem; }
.ap-error .ap-meta { color:#d04452; }
.ap-steps { display:flex; align-items:center; gap:1.1rem; flex-wrap:wrap; margin-top:.75rem; }
.ap-step { display:inline-flex; align-items:center; gap:.35rem; font-size:.8rem; color:#6b7280; }
.ap-step-done { color:#237c64; }
.ap-step-active { color:var(--violet); }
.ap-ring { width:13px; height:13px; border-radius:50%; border:1.6px solid currentColor; display:inline-block; }
.ap-step-active .ap-ring { border-color:#dcd9ff; border-top-color:var(--violet); animation:ps-spin .9s linear infinite; }
.ap-side { background:#fff; border:1px solid var(--line); border-radius:12px; padding:1.5rem; margin-bottom:1.3rem; }
.ap-side-title { font-size:1.25rem; font-weight:500; color:var(--ink); line-height:1.3; }
.stApp .ap-side p { font-size:.9rem; color:var(--muted); line-height:1.6; margin:.9rem 0 0; }
.ap-side hr { border:0; border-top:1px solid #eeedf4; margin:1.2rem 0 1rem; }
.ap-side-step { display:flex; gap:.8rem; align-items:flex-start; margin-bottom:.9rem; }
.ap-side-step svg { flex:none; margin-top:.1rem; }
.ap-side-step b { display:block; font-size:.9rem; font-weight:600; color:var(--ink); }
.ap-side-step span { font-size:.82rem; color:var(--muted); }
.ap-note { background:#efeeff; border-radius:12px; padding:1.5rem; }
.ap-note-title { font-size:1.05rem; color:var(--violet); margin:.8rem 0 .5rem; }
.stApp .ap-note p { font-size:.9rem; color:#374151; line-height:1.6; margin:0; }
.ap-leave { font-size:.84rem; color:var(--muted); margin-left:auto; }
/* ===== /B2 ANALYSIS PROGRESS ===== */
/* ===== B3 DIALOGS ===== */
/* pop-up (mockup Logout / Delete story / Save to Workspace) */
[role="dialog"] { border-radius:14px !important; background:#fff !important; }
[role="dialog"] h2 > span { display:flex !important; flex-direction:column; align-items:flex-start !important; gap:1rem; }
[role="dialog"] [data-testid="stDialogIcon"] { width:46px; height:46px; border-radius:12px; background:#efeeff;
  display:flex; align-items:center; justify-content:center; margin:0 !important; }
[role="dialog"] [data-testid="stDialogIcon"] [data-testid="stIconMaterial"] { font-size:24px !important; color:#635bff !important; }
[role="dialog"] h2 p { font-size:1.6rem !important; font-weight:500 !important; color:#202033 !important; line-height:1.25 !important; }
[role="dialog"]:has(.st-key-wsdel_confirm, .st-key-chdel_confirm, .st-key-del_confirm) [data-testid="stDialogIcon"] { background:#fff0f1; }
[role="dialog"]:has(.st-key-wsdel_confirm, .st-key-chdel_confirm, .st-key-del_confirm) [data-testid="stDialogIcon"] [data-testid="stIconMaterial"] { color:#d04452 !important; }
.st-key-wsdel_confirm button, .st-key-chdel_confirm button, .st-key-del_confirm button { background:#d04452 !important; border-color:#d04452 !important; }
.st-key-wsdel_confirm button:hover, .st-key-chdel_confirm button:hover, .st-key-del_confirm button:hover { background:#b83542 !important; border-color:#b83542 !important; }
[role="dialog"] .stButton button { min-height:2.9rem; padding:0 1.1rem; font-weight:600; }
.dlg-danger { display:flex; gap:1rem; align-items:flex-start; background:#fff0f1; border-radius:10px; padding:1.1rem 1.1rem; margin:.9rem 0 .6rem; }
.dlg-danger svg { flex:none; margin-top:.15rem; }
.dlg-danger b { display:block; font-size:.95rem; font-weight:600; color:#202033; margin-bottom:.2rem; }
.dlg-danger span { display:block; font-size:.84rem; color:#505365; line-height:1.55; }
/* ===== /B3 DIALOGS ===== */
/* ===== C HOME ===== */
/* Home (mockup "Home · Welcome to FanMeta") */
.st-key-hero { background:#211b3a; border-radius:16px; padding:3rem 3rem 3rem 3rem; margin-top:.4rem; }
.hero-kicker { display:flex; align-items:center; gap:.5rem; font-size:.78rem; font-weight:600; letter-spacing:.02em;
  text-transform:uppercase; color:#d9d6ff; }
.stApp h1.hero-h1 { color:#fff !important; font-size:3.3rem; line-height:1.1; font-weight:700; letter-spacing:-.015em;
  margin:1.2rem 0 1.5rem; padding:0; }
.stApp p.hero-p { color:#e4e2fa; font-size:1.05rem; line-height:1.65; margin:0 0 1.6rem; max-width:580px; }
.stApp p.hero-note { color:#c9c6e8; font-size:.84rem; margin:1.5rem 0 0; }
.st-key-home_analyze button, .st-key-home_read button, .st-key-home_cta_btn button { min-height:2.9rem; padding:0 1.2rem; font-weight:600; }
.st-key-home_read button { background:#fff !important; border:1px solid #fff !important; }
.st-key-home_read button p { color:#202033 !important; font-weight:600; }
.hero-art { position:relative; border-radius:12px; height:460px; background:#2c2550 center / cover no-repeat; overflow:hidden; }
.hero-sample { position:absolute; left:1.5rem; right:1.5rem; bottom:1.5rem; background:#fff; border-radius:12px;
  padding:1.1rem 1.25rem; box-shadow:0 10px 30px rgba(10,8,30,.25); }
.hero-sample-top { display:flex; justify-content:space-between; align-items:center; gap:1rem; font-size:1.05rem; color:#202033; }
.hero-sample-tags { display:flex; gap:.5rem; flex-wrap:wrap; margin-top:.8rem; }
.home-head { display:flex; justify-content:space-between; align-items:baseline; gap:1rem; flex-wrap:wrap; margin:3.4rem 0 1.4rem; }
.home-h2 { font-size:1.75rem; font-weight:700; color:#202033; line-height:1.3; }
.home-head span { font-size:.88rem; color:#505365; }
.home-feat-grid { display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:1.3rem; }
.home-steps { display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:2rem; }
@media (max-width: 1000px) { .home-feat-grid, .home-steps { grid-template-columns:repeat(2, minmax(0, 1fr)); } }
@media (max-width: 640px) { .home-feat-grid, .home-steps { grid-template-columns:1fr; } .st-key-hero { padding:1.6rem; }
  .stApp h1.hero-h1 { font-size:2.2rem; } .hero-art { height:320px; } }
.home-feat { background:#fff; border:1px solid var(--line); border-radius:12px; padding:1.5rem 1.5rem 1.6rem; }
.stApp .home-feat h3 { font-size:1.08rem; font-weight:500; color:#202033; margin:1.5rem 0 .8rem; padding:0; }
.stApp .home-feat p, .stApp .home-step p { font-size:.9rem; color:#505365; line-height:1.6; margin:0; }
.home-step-n { font-size:1.6rem; font-weight:600; color:var(--violet); padding-bottom:.9rem; border-bottom:1px solid #d9d7e5; }
.stApp .home-step h3 { font-size:1.05rem; font-weight:500; color:#202033; margin:1.2rem 0 .7rem; padding:0; }
.st-key-home_cta { background:#efeeff; border-radius:14px; padding:1.9rem 1.8rem; margin:3.4rem 0 .5rem; }
.st-key-home_cta > div:first-child { flex:1 1 auto; }
.cta-t { font-size:1.45rem; color:#202033; }
.cta-s { font-size:.95rem; color:#505365; margin-top:.4rem; }
/* ===== /C HOME ===== */
</style>
"""


def apply_theme() -> None:
    # foto latar login dipasang di auth_layout.art_panel (hanya di halaman login/register)
    st.markdown(_THEME_CSS, unsafe_allow_html=True)