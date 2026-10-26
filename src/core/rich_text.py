"""Isi bab berformat: pembersihan HTML dari editor, dan konversi HTML <-> teks biasa.

Editor hanya boleh menghasilkan tag format sederhana. Semua tag lain dibuang (isinya tetap),
semua atribut dibuang, dan isi <script>/<style> dihapus. Model selalu menerima teks biasa.
"""

import html
import re
from html.parser import HTMLParser

ALLOWED_TAGS = {"p", "br", "strong", "b", "em", "i", "u", "h2", "h3", "ul", "ol", "li", "blockquote", "hr"}
_VOID = {"br", "hr"}
_DROP_CONTENT = {"script", "style", "iframe", "object", "embed", "template"}
_BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "li", "blockquote", "ul", "ol", "hr", "br"}
SCENE_BREAK = "* * *"


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.open: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):  # noqa: ARG002 - atribut sengaja dibuang
        if tag in _DROP_CONTENT:
            self.skip += 1
            return
        if self.skip:
            return
        tag = "p" if tag == "div" else tag  # contenteditable kadang membuat <div> per baris
        if tag not in ALLOWED_TAGS:
            return
        if tag in ("li", "p"):
            # seperti browser: <li> / <p> baru menutup <li> / <p> sebelumnya yang belum ditutup
            for current in reversed(self.open):
                if current == tag:
                    self.handle_endtag(tag)
                    break
                if current in ("ul", "ol", "blockquote"):
                    break
        self.out.append(f"<{tag}>")
        if tag not in _VOID:
            self.open.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID and self.open and self.open[-1] == tag:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in _DROP_CONTENT:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        tag = "p" if tag == "div" else tag
        if tag in _VOID or tag not in self.open:
            return
        while self.open:  # tutup tag yang belum ditutup di dalamnya juga
            current = self.open.pop()
            self.out.append(f"</{current}>")
            if current == tag:
                break

    def handle_data(self, data):
        if not self.skip:
            self.out.append(html.escape(data, quote=False))

    def result(self) -> str:
        while self.open:
            self.out.append(f"</{self.open.pop()}>")
        return "".join(self.out)


def sanitize_html(value: str) -> str:
    parser = _Sanitizer()
    parser.feed(str(value or ""))
    parser.close()
    cleaned = parser.result()
    return re.sub(r"<p>(\s|<br>)*</p>", "", cleaned).strip()  # buang paragraf kosong


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "hr":
            self.parts.append(f"\n\n{SCENE_BREAK}\n\n")
        elif tag in _BLOCK:
            self.parts.append("\n\n" if tag != "br" else "\n")

    def handle_endtag(self, tag):
        if tag in _BLOCK:
            self.parts.append("\n\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(value: str) -> str:
    """Teks biasa untuk dianalisis model dan dihitung katanya (format dibuang)."""
    parser = _TextExtractor()
    parser.feed(sanitize_html(value))
    parser.close()
    text = "".join(parser.parts).replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def text_to_html(text: str) -> str:
    """Teks biasa (misalnya dari file .txt/.docx) -> paragraf HTML untuk editor."""
    paragraphs = re.split(r"\n\s*\n", str(text or "").replace("\r\n", "\n").strip())
    out = []
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if re.fullmatch(r"[*\-_~#\s]{3,}", paragraph):
            out.append("<hr>")
        else:
            out.append("<p>" + "<br>".join(html.escape(line) for line in paragraph.split("\n")) + "</p>")
    return "".join(out)


def count_words(value: str) -> int:
    return len(html_to_text(value).replace(SCENE_BREAK, " ").split())
