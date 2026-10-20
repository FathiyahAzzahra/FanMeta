"""Baca teks cerita dari file .txt atau .docx yang diunggah pengguna."""

import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree

MAX_FILE_BYTES = 5 * 1024 * 1024  # cerita 3.500 kata jauh di bawah 1 MB
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class StoryFileError(ValueError):
    """Pesan aman untuk ditampilkan ke pengguna."""


def _read_txt(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise StoryFileError("File .txt tidak dapat dibaca. Simpan ulang file dengan encoding UTF-8.")


def _read_docx(data: bytes) -> str:
    # .docx adalah file zip; teksnya ada di word/document.xml, satu <w:p> per paragraf
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise StoryFileError("File .docx rusak atau bukan dokumen Word.") from error

    paragraphs = []
    for paragraph in root.iter(f"{_W}p"):
        parts = []
        for node in paragraph.iter():
            if node.tag == f"{_W}t":
                parts.append(node.text or "")
            elif node.tag == f"{_W}tab":
                parts.append(" ")
            elif node.tag in (f"{_W}br", f"{_W}cr"):
                parts.append("\n")
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def read_story_file(file_name: str, data: bytes) -> str:
    """Kembalikan isi cerita sebagai teks biasa."""
    if len(data) > MAX_FILE_BYTES:
        raise StoryFileError("File terlalu besar (maksimal 5 MB).")
    suffix = Path(file_name).suffix.lower()
    if suffix == ".txt":
        text = _read_txt(data)
    elif suffix == ".docx":
        text = _read_docx(data)
    else:
        raise StoryFileError("Format file tidak didukung. Gunakan .txt atau .docx.")
    text = text.replace("\r\n", "\n").strip()
    if not text:
        raise StoryFileError("File tidak berisi teks.")
    return text
