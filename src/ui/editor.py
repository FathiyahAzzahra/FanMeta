"""Editor teks berformat untuk bab Workspace (Streamlit Custom Components v2, tanpa library luar).

Alur data:
- Python -> JS : ``data.value`` (isi bab), ``data.doc_id`` (bab yang sedang dibuka), ``data.status``.
- JS -> Python : state ``value`` dikirim 1,5 detik setelah penulis berhenti mengetik dan saat
  editor kehilangan fokus. Python lalu membersihkan HTML-nya dan menyimpannya (simpan otomatis).
"""
from collections.abc import Callable
from typing import Any

import streamlit as st

from src.core.i18n import is_id, tr

_SVG = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{}</svg>')
_ICONS = {
    "quote": '<path d="M16 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2 1 1 0 0 1 1 1v1a2 2 0 0 1-2 2 1 1 0 0 0-1 1v2a1 1 0 0 0 1 1 '
             '6 6 0 0 0 6-6V5a2 2 0 0 0-2-2z"/><path d="M5 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2 1 1 0 0 1 1 1v1a2 2 0 0 1-2 '
             '2 1 1 0 0 0-1 1v2a1 1 0 0 0 1 1 6 6 0 0 0 6-6V5a2 2 0 0 0-2-2z"/>',
    "list": '<path d="M3 12h.01"/><path d="M3 18h.01"/><path d="M3 6h.01"/><path d="M8 12h13"/><path d="M8 18h13"/>'
            '<path d="M8 6h13"/>',
    "olist": '<path d="M10 12h11"/><path d="M10 18h11"/><path d="M10 6h11"/><path d="M4 10h2"/><path d="M4 6h1v4"/>'
             '<path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"/>',
    "scene": '<path d="M5 12h14"/>',
    "check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
}


def _svg(name: str) -> str:
    return _SVG.format(_ICONS[name])


_HTML = f"""
<div class="fmed">
  <div class="fmed-bar" role="toolbar" aria-label="Formatting">
    <select class="fmed-block" title="Text style" aria-label="Text style">
      <option value="p">Paragraph</option><option value="h2">Heading</option><option value="blockquote">Quote</option>
    </select>
    <span class="fmed-sep"></span>
    <button type="button" data-cmd="bold" title="Bold (Ctrl+B)"><b>B</b></button>
    <button type="button" data-cmd="italic" title="Italic (Ctrl+I)"><i>I</i></button>
    <button type="button" data-cmd="underline" title="Underline (Ctrl+U)"><u>U</u></button>
    <span class="fmed-sep"></span>
    <button type="button" data-cmd="formatBlock:h2" title="Heading">H2</button>
    <button type="button" data-cmd="formatBlock:blockquote" title="Quote">{_svg("quote")}</button>
    <button type="button" data-cmd="insertUnorderedList" title="Bulleted list">{_svg("list")}</button>
    <button type="button" data-cmd="insertOrderedList" title="Numbered list">{_svg("olist")}</button>
    <button type="button" data-cmd="scene" title="Scene break">{_svg("scene")}</button>
    <span class="fmed-meta"></span>
  </div>
  <div class="fmed-page">
    <div class="fmed-doc"><span class="fmed-doc-l"></span><span class="fmed-doc-r"></span></div>
    <div class="fmed-area" contenteditable="true" spellcheck="true"></div>
  </div>
  <div class="fmed-foot">
    <span class="fmed-left"><span class="fmed-words"></span>
      <span class="fmed-status"><span class="fmed-ok">{_svg("check")}</span><span class="fmed-status-t"></span></span>
      <span class="fmed-when"></span></span>
    <button type="button" class="fmed-save">Save &amp; back to story</button>
  </div>
</div>
"""

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap');
.fmed { border:1px solid var(--bd-e5e7eb, #e5e7eb); border-radius:12px; background:var(--bg-ffffff, #fff); font-family:Inter,sans-serif; }
.fmed-bar { display:flex; flex-wrap:wrap; align-items:center; gap:.35rem; padding:.7rem 1.4rem; border-bottom:1px solid var(--bd-e5e7eb, #e5e7eb);
  background:var(--bg-ffffff, #fff); border-radius:12px 12px 0 0; }
.fmed-block { border:0; background:transparent; font:500 .92rem Inter,sans-serif; color:var(--fg-202033, #202033); padding:.4rem .5rem;
  margin-right:.4rem; cursor:pointer; outline:none; border-radius:6px; }
.fmed-block:hover { background:var(--bg-f5f5fb, #f5f5fb); }
.fmed-bar button { border:0; background:transparent; color:var(--fg-202033, #202033); border-radius:7px; height:34px; min-width:34px;
  padding:0 .5rem; font:500 .95rem Inter,sans-serif; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; }
.fmed-bar button:hover { background:var(--bg-efeeff, #efeeff); color:var(--fg-635bff, #635bff); }
.fmed-sep { width:1px; height:22px; background:var(--bg-e5e7eb, #e5e7eb); margin:0 .35rem; }
.fmed-meta { margin-left:auto; font-size:.82rem; color:var(--fg-505365, #505365); }
.fmed-page { max-width:940px; margin:0 auto; padding:2.6rem 1.5rem 2.4rem; }
.fmed-doc { display:flex; justify-content:space-between; gap:1rem; font-size:.74rem; color:var(--fg-505365, #505365); margin-bottom:1.6rem; }
.fmed-doc-l { text-transform:uppercase; letter-spacing:.03em; }
.fmed-area { min-height:460px; outline:none; font-size:1.2rem; line-height:1.75; color:var(--fg-202033, #202033);
  font-family:'Source Serif 4',Georgia,'Times New Roman',serif; }
.fmed-area:empty::before { content:attr(data-placeholder); color:var(--fg-9ca3af, #9ca3af); font-style:italic; }
.fmed-area p, .fmed-area > div { margin:0 0 1.35rem; }
.fmed-area h2 { font-size:1.45rem; font-weight:600; margin:1.8rem 0 .9rem; font-family:inherit; color:var(--fg-202033, #202033); }
.fmed-area blockquote { margin:0 0 1.35rem; padding:.1rem 0 .1rem 1.2rem; border-left:3px solid var(--bd-c7c3ff, #c7c3ff); color:var(--fg-505365, #505365); font-style:italic; }
.fmed-area ul, .fmed-area ol { margin:0 0 1.35rem; padding-left:1.6rem; }
.fmed-area hr { border:0; text-align:center; margin:1.6rem 0; height:auto; overflow:visible; }
.fmed-area hr::after { content:"*  *  *"; color:var(--fg-505365, #505365); letter-spacing:.35rem; font-size:1rem; }
.fmed-foot { display:flex; justify-content:space-between; align-items:center; gap:1rem; padding:1rem 1.4rem;
  border-top:1px solid var(--bd-e5e7eb, #e5e7eb); position:sticky; bottom:0; z-index:2; background:var(--bg-ffffff, #fff); border-radius:0 0 12px 12px; }
.fmed-left { display:flex; align-items:center; gap:1.4rem; flex-wrap:wrap; }
.fmed-words { font-size:.92rem; color:var(--fg-202033, #202033); }
.fmed-status { display:inline-flex; align-items:center; gap:.4rem; font-size:.92rem; color:var(--fg-237c64, #237c64); }
.fmed-status svg { width:16px; height:16px; display:block; }
.fmed-status.dirty, .fmed-status.busy { color:var(--fg-b86010, #b86010); }
.fmed-status.error { color:var(--fg-d04452, #d04452); }
.fmed-status:not(.saved) .fmed-ok { display:none; }
.fmed-when { font-size:.8rem; color:var(--fg-505365, #505365); }
.fmed-save { border:0; border-radius:8px; background:var(--bg-635bff, #635bff); color:var(--fg-ffffff, #fff); font:600 .95rem Inter,sans-serif;
  padding:.75rem 1.2rem; cursor:pointer; }
.fmed-save:hover { background:var(--bg-5149db, #5149db); }
"""

_JS = """
const STATE = new WeakMap()

export default function (component) {
  const { data, parentElement, setStateValue, setTriggerValue } = component
  const root = parentElement.querySelector(".fmed")
  if (!root) return
  const area = root.querySelector(".fmed-area")
  const status = root.querySelector(".fmed-status")
  const statusText = root.querySelector(".fmed-status-t")
  const when = root.querySelector(".fmed-when")
  const words = root.querySelector(".fmed-words")
  const block = root.querySelector(".fmed-block")
  // teks antarmuka sesuai bahasa (dikirim dari Python)
  const L = data.labels || {}
  block.options[0].text = L.paragraph || "Paragraph"
  block.options[1].text = L.heading || "Heading"
  block.options[2].text = L.quote || "Quote"
  block.title = L.style || "Text style"
  root.querySelectorAll("[data-cmd]").forEach((b) => { if (L.titles && L.titles[b.dataset.cmd]) b.title = L.titles[b.dataset.cmd] })
  root.querySelector(".fmed-save").textContent = L.save || "Save & back to story"
  root.querySelector(".fmed-meta").textContent = data.meta || ""
  root.querySelector(".fmed-doc-l").textContent = data.doc_left || ""
  root.querySelector(".fmed-doc-r").textContent = data.doc_right || ""
  const setStatus = (kind, text, whenText) => {
    status.className = "fmed-status " + kind
    statusText.textContent = text
    if (whenText !== undefined) when.textContent = whenText
  }

  let st = STATE.get(parentElement)
  if (!st) {
    st = { docId: null, lastEmitted: null, timer: null }
    STATE.set(parentElement, st)
  }

  // Isi dari Python hanya ditimpakan kalau bab berganti atau isinya berubah dari luar
  // (misalnya impor file). Gema dari ketikan sendiri diabaikan supaya kursor tidak meloncat.
  const incoming = (data && data.value) || ""
  if (st.docId !== data.doc_id) {
    area.innerHTML = incoming
    st.docId = data.doc_id
    st.lastEmitted = incoming
  } else if (incoming !== st.lastEmitted) {
    area.innerHTML = incoming
    st.lastEmitted = incoming
  }
  area.dataset.placeholder = data.placeholder || ""
  if (!st.timer) setStatus(data.status_kind || "saved", data.status || "", data.status_when || "")

  const countWords = () => {
    const text = area.innerText.replace(/[✻*]/g, " ").trim()
    const n = text ? text.split(/\\s+/).length : 0
    words.textContent = n.toLocaleString(L.locale || "en-US") + " " + (L.words || "words")
  }
  countWords()

  const emit = () => {
    clearTimeout(st.timer)
    st.timer = null
    const value = area.innerHTML
    if (value !== st.lastEmitted) {
      st.lastEmitted = value
      setStatus("busy", L.saving || "Saving…")
      setStateValue("value", value)
    }
  }
  const changed = () => {
    countWords()
    setStatus("dirty", L.unsaved || "Unsaved changes")
    clearTimeout(st.timer)
    st.timer = setTimeout(emit, 1500)
  }

  // tombol Save: kirim isi terbaru saat itu juga (tanpa menunggu jeda), lalu Python kembali ke cerita
  root.querySelector(".fmed-save").onclick = () => {
    clearTimeout(st.timer)
    st.timer = null
    st.lastEmitted = area.innerHTML
    setStatus("busy", L.saving || "Saving…")
    setTriggerValue("save", area.innerHTML)
  }

  // dropdown gaya teks mengikuti blok tempat kursor berada
  const syncBlock = () => {
    const tag = (document.queryCommandValue("formatBlock") || "p").toLowerCase()
    block.value = ["h2", "blockquote"].includes(tag) ? tag : "p"
  }
  block.onchange = () => {
    area.focus()
    document.execCommand("formatBlock", false, "<" + block.value + ">")
    changed()
  }
  area.onkeyup = syncBlock
  area.onmouseup = syncBlock

  area.oninput = changed
  area.onblur = emit
  area.onpaste = (event) => {
    // tempel sebagai teks biasa supaya format/script dari situs lain tidak ikut
    event.preventDefault()
    const text = (event.clipboardData || window.clipboardData).getData("text/plain")
    document.execCommand("insertText", false, text)
  }

  root.querySelectorAll("[data-cmd]").forEach((button) => {
    button.onmousedown = (event) => event.preventDefault()  // seleksi teks jangan hilang
    button.onclick = () => {
      area.focus()
      const [cmd, arg] = button.dataset.cmd.split(":")
      if (cmd === "scene") {
        document.execCommand("insertHorizontalRule")
      } else {
        document.execCommand(cmd, false, arg ? "<" + arg + ">" : null)
      }
      syncBlock()
      changed()
    }
  })

  return () => emit()
}
"""

_EDITOR = st.components.v2.component(
    "fanmeta_chapter_editor", html=_HTML, css=_CSS, js=_JS, isolate_styles=False,
)


def _labels() -> dict[str, Any]:
    return {
        "paragraph": tr("Paragraph", "Paragraf"), "heading": tr("Heading", "Judul"), "quote": tr("Quote", "Kutipan"),
        "style": tr("Text style", "Gaya teks"), "save": tr("Save & back to story", "Simpan & kembali ke cerita"),
        "words": tr("words", "kata"), "saving": tr("Saving…", "Menyimpan…"),
        "unsaved": tr("Unsaved changes", "Belum tersimpan"), "locale": "id-ID" if is_id() else "en-US",
        "titles": {
            "bold": tr("Bold (Ctrl+B)", "Tebal (Ctrl+B)"), "italic": tr("Italic (Ctrl+I)", "Miring (Ctrl+I)"),
            "underline": tr("Underline (Ctrl+U)", "Garis bawah (Ctrl+U)"), "formatBlock:h2": tr("Heading", "Judul"),
            "formatBlock:blockquote": tr("Quote", "Kutipan"),
            "insertUnorderedList": tr("Bulleted list", "Daftar berpoin"),
            "insertOrderedList": tr("Numbered list", "Daftar bernomor"), "scene": tr("Scene break", "Pergantian adegan"),
        },
    }


def editor_key(chapter_id: str) -> str:
    return f"chapter_editor_{chapter_id}"


def set_editor_value(chapter_id: str, value: str) -> None:
    """Ganti isi editor dari Python (misalnya setelah impor file). Panggil sebelum editor tampil."""
    st.session_state.setdefault(editor_key(chapter_id), {})["value"] = value


def pending_value(chapter_id: str) -> str | None:
    """Isi terbaru yang sudah dikirim browser (sebelum editor ditampilkan di run ini), atau None."""
    state: Any = st.session_state.get(editor_key(chapter_id))
    return state.get("value") if state is not None and hasattr(state, "get") else None


def saved_value(chapter_id: str) -> str | None:
    """Isi yang dikirim tombol Save. Hanya terbaca di dalam callback ``on_save``."""
    state: Any = st.session_state.get(editor_key(chapter_id))
    return getattr(state, "save", None) if state is not None else None


def chapter_editor(chapter_id: str, stored_html: str, status: dict[str, str], placeholder: str,
                   meta: str = "", doc_left: str = "", doc_right: str = "",
                   on_save: Callable[[], None] | None = None) -> str:
    """Tampilkan editor dan kembalikan isi terbaru (HTML mentah dari browser).

    ``status`` = {"kind": "saved"/"error"/..., "text": ..., "when": ...}. ``meta`` tampil di kanan toolbar,
    ``doc_left``/``doc_right`` di atas naskah. ``on_save`` dipanggil (sebelum halaman dijalankan ulang) saat tombol Save diklik.
    """
    key = editor_key(chapter_id)
    state: Any = st.session_state.get(key) or {}
    value = state.get("value", stored_html) if hasattr(state, "get") else stored_html
    result = _EDITOR(
        key=key,
        data={"value": value, "doc_id": chapter_id, "status": status.get("text", ""),
              "status_kind": status.get("kind", "saved"), "status_when": status.get("when", ""),
              "placeholder": placeholder, "meta": meta, "doc_left": doc_left, "doc_right": doc_right,
              "labels": _labels()},
        default={"value": value},
        on_value_change=lambda: None,
        on_save_change=on_save or (lambda: None),
    )
    return result.value if result.value is not None else value
