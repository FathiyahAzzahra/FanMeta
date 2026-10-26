"""Firestore persistence for the private writing Workspace.

Struktur data (riwayat lama users/{uid}/history tidak diubah):
    users/{uid}/works/{work_id}                        satu proyek cerita
    users/{uid}/works/{work_id}/chapters/{chapter_id}  bab-bab cerita
Analisis Workspace disimpan di users/{uid}/history dengan field tambahan
source="workspace", work_id, chapter_id (dikerjakan di tahap W3).

Field ringkasan di dokumen cerita (chapter_count, word_count, rating) diperbarui
setiap kali bab atau analisis berubah, supaya daftar cerita cukup membaca satu koleksi.
"""

from datetime import datetime, timezone
from typing import Any

from firebase_admin import firestore

from src.core.i18n import tr

from src.core.rich_text import count_words, sanitize_html
from src.core.workspace_metadata import aggregate

MAX_CHAPTER_CHARS = 300_000  # jauh di bawah batas dokumen Firestore (1 MB)
STATUSES = ("Draft", "Ongoing", "Complete", "Hiatus")
LANGUAGES = ("Bahasa Indonesia", "Bahasa Inggris")
LIMITS = {"title": 200, "fandom": 100, "summary": 1000, "notes": 2000, "list_item": 100, "list_len": 30}


class WorkspaceError(RuntimeError):
    """A user-safe error raised when the workspace cannot be accessed or input is invalid."""


def _clean_text(value: Any, field: str, label: str, required: bool = False) -> str:
    text = str(value or "").strip()
    if required and not text:
        raise WorkspaceError(tr(f"{label} is required.", f"{label} wajib diisi."))
    if len(text) > LIMITS[field]:
        raise WorkspaceError(tr(f"{label} can be at most {LIMITS[field]:,} characters.",
                                f"{label} maksimal {LIMITS[field]:,} karakter."))
    return text


def _clean_list(values: Any, label: str) -> list[str]:
    cleaned, seen = [], set()
    for value in values or []:
        value = " ".join(str(value).split())
        if value and value.lower() not in seen:
            if len(value) > LIMITS["list_item"]:
                raise WorkspaceError(tr(f"{label}: each entry can be at most {LIMITS['list_item']} characters.",
                                    f"{label}: tiap isian maksimal {LIMITS['list_item']} karakter."))
            seen.add(value.lower())
            cleaned.append(value)
    if len(cleaned) > LIMITS["list_len"]:
        raise WorkspaceError(tr(f"{label} can have at most {LIMITS['list_len']} entries.",
                                f"{label} maksimal {LIMITS['list_len']} isian."))
    return cleaned


def _check_size(content_html: str) -> None:
    if len(content_html) > MAX_CHAPTER_CHARS:
        raise WorkspaceError(tr("This chapter is too long. Split it into several chapters.", "Bab terlalu panjang. Pecah menjadi beberapa bab."))


def clean_work(data: dict[str, Any]) -> dict[str, Any]:
    """Validasi isian form cerita dan kembalikan field yang boleh disimpan."""
    if data.get("status") not in STATUSES:
        raise WorkspaceError(tr("Invalid status.", "Status tidak valid."))
    if data.get("language") not in LANGUAGES:
        raise WorkspaceError(tr("Invalid language.", "Bahasa tidak valid."))
    return {
        "title": _clean_text(data.get("title"), "title", tr("Title", "Judul"), required=True),
        "fandom": _clean_text(data.get("fandom"), "fandom", "Fandom", required=True),
        "characters": _clean_list(data.get("characters"), tr("Characters", "Tokoh")),
        "relationships": _clean_list(data.get("relationships"), "Relationship"),
        "summary": _clean_text(data.get("summary"), "summary", tr("Summary", "Ringkasan")),
        "language": data["language"],
        "status": data["status"],
        "notes": _clean_text(data.get("notes"), "notes", tr("Notes", "Catatan")),
    }


class WorkspaceStore:
    def __init__(self, client: Any) -> None:
        self._client = client

    def _works(self, uid: str) -> Any:
        return self._client.collection("users").document(uid).collection("works")

    # ---------- cerita ----------
    def list_works(self, uid: str) -> list[dict[str, Any]]:
        try:
            snapshots = self._works(uid).order_by("updated_at", direction=firestore.Query.DESCENDING).stream()
            works = []
            for snapshot in snapshots:
                item = snapshot.to_dict() or {}
                item["work_id"] = snapshot.id
                works.append(item)
            return works
        except Exception as error:
            raise WorkspaceError(tr("Your stories could not be loaded.", "Daftar cerita tidak dapat dimuat.")) from error

    def get_work(self, uid: str, work_id: str) -> dict[str, Any] | None:
        try:
            snapshot = self._works(uid).document(work_id).get()
        except Exception as error:
            raise WorkspaceError(tr("The story could not be loaded.", "Cerita tidak dapat dimuat.")) from error
        if not snapshot.exists:
            return None
        item = snapshot.to_dict() or {}
        item["work_id"] = snapshot.id
        return item

    def create_work(self, uid: str, data: dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        work = {**clean_work(data), "chapter_count": 0, "word_count": 0, "rating": None,
                "created_at": now, "updated_at": now}
        try:
            ref = self._works(uid).document()
            ref.set(work)
            return ref.id
        except Exception as error:
            raise WorkspaceError(tr("The story could not be created.", "Cerita gagal dibuat.")) from error

    def update_work(self, uid: str, work_id: str, data: dict[str, Any]) -> None:
        work = {**clean_work(data), "updated_at": datetime.now(timezone.utc)}
        try:
            self._works(uid).document(work_id).update(work)
        except Exception as error:
            raise WorkspaceError(tr("The story changes could not be saved.", "Perubahan cerita gagal disimpan.")) from error

    # ---------- bab ----------
    def _chapters(self, uid: str, work_id: str) -> Any:
        return self._works(uid).document(work_id).collection("chapters")

    def list_chapters(self, uid: str, work_id: str) -> list[dict[str, Any]]:
        """Bab urut sesuai posisi; field 'number' (1, 2, 3, ...) dihitung dari urutan."""
        try:
            chapters = []
            for snapshot in self._chapters(uid, work_id).stream():
                item = snapshot.to_dict() or {}
                item["chapter_id"] = snapshot.id
                chapters.append(item)
        except Exception as error:
            raise WorkspaceError(tr("The chapters could not be loaded.", "Daftar bab tidak dapat dimuat.")) from error
        chapters.sort(key=lambda c: (c.get("order", 0), str(c.get("created_at"))))
        for number, chapter in enumerate(chapters, start=1):
            chapter["number"] = number
        return chapters

    def _refresh_stats(self, uid: str, work_id: str) -> None:
        chapters = self.list_chapters(uid, work_id)
        self._works(uid).document(work_id).update({
            "chapter_count": len(chapters),
            "word_count": sum(int(c.get("word_count") or 0) for c in chapters),
            "updated_at": datetime.now(timezone.utc),
        })

    def create_chapter(self, uid: str, work_id: str, content_html: str = "") -> str:
        content_html = sanitize_html(content_html)
        _check_size(content_html)
        chapters = self.list_chapters(uid, work_id)
        now = datetime.now(timezone.utc)
        try:
            ref = self._chapters(uid, work_id).document()
            ref.set({
                "order": max((int(c.get("order", 0)) for c in chapters), default=0) + 1,
                "title": "", "content_html": content_html, "word_count": count_words(content_html),
                "created_at": now, "updated_at": now, "last_analyzed_at": None,
            })
            self._refresh_stats(uid, work_id)
            return ref.id
        except Exception as error:
            raise WorkspaceError(tr("The chapter could not be created.", "Bab gagal dibuat.")) from error

    def update_chapter(self, uid: str, work_id: str, chapter_id: str, *,
                       content_html: str | None = None, title: str | None = None) -> dict[str, Any]:
        data: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
        if content_html is not None:
            content_html = sanitize_html(content_html)
            _check_size(content_html)
            data.update(content_html=content_html, word_count=count_words(content_html))
        if title is not None:
            title = " ".join(str(title).split())
            if len(title) > LIMITS["title"]:
                raise WorkspaceError(tr(f"Chapter title can be at most {LIMITS['title']} characters.",
                                        f"Judul bab maksimal {LIMITS['title']} karakter."))
            data["title"] = title
        try:
            self._chapters(uid, work_id).document(chapter_id).update(data)
            self._refresh_stats(uid, work_id)
        except Exception as error:
            raise WorkspaceError(tr("The chapter could not be saved.", "Bab gagal disimpan.")) from error
        return data

    def move_chapter(self, uid: str, work_id: str, chapter_id: str, step: int) -> None:
        """Geser bab satu posisi ke atas (step=-1) atau ke bawah (step=1)."""
        chapters = self.list_chapters(uid, work_id)
        index = next((i for i, c in enumerate(chapters) if c["chapter_id"] == chapter_id), None)
        if index is None or not 0 <= index + step < len(chapters):
            return
        chapters[index], chapters[index + step] = chapters[index + step], chapters[index]
        try:
            batch = self._client.batch()
            for order, chapter in enumerate(chapters, start=1):  # tulis ulang urutan 1..n
                batch.update(self._chapters(uid, work_id).document(chapter["chapter_id"]), {"order": order})
            batch.update(self._works(uid).document(work_id), {"updated_at": datetime.now(timezone.utc)})
            batch.commit()
        except Exception as error:
            raise WorkspaceError(tr("The chapter order could not be changed.", "Urutan bab gagal diubah.")) from error

    def delete_chapter(self, uid: str, work_id: str, chapter_id: str) -> None:
        """Hapus bab. Analisisnya tetap ada di riwayat (log), metadata cerita dihitung ulang."""
        try:
            self._chapters(uid, work_id).document(chapter_id).delete()
            self._refresh_stats(uid, work_id)
            self.refresh_metadata(uid, work_id)
        except Exception as error:
            raise WorkspaceError(tr("The chapter could not be deleted.", "Bab gagal dihapus.")) from error

    # ---------- analisis ----------
    def set_chapter_analysis(self, uid: str, work_id: str, chapter_id: str, analysis: dict[str, Any]) -> None:
        """Simpan ringkasan analisis terakhir di dokumen bab, lalu hitung ulang metadata cerita."""
        try:
            self._chapters(uid, work_id).document(chapter_id).update({"analysis": analysis,
                                                                      "last_analyzed_at": analysis["analyzed_at"]})
            self.refresh_metadata(uid, work_id)
        except Exception as error:
            raise WorkspaceError(tr("The chapter analysis could not be saved.", "Hasil analisis bab gagal disimpan.")) from error

    def unlink_analysis(self, uid: str, work_id: str, chapter_id: str, analysis_id: str) -> None:
        """Dipanggil saat analisis Workspace dihapus dari History: kalau itu analisis terakhir bab,
        bab kembali berstatus 'belum dianalisis' dan metadata cerita dihitung ulang."""
        ref = self._chapters(uid, work_id).document(chapter_id)
        try:
            snapshot = ref.get()
            if not snapshot.exists:
                return
            if ((snapshot.to_dict() or {}).get("analysis") or {}).get("analysis_id") == analysis_id:
                ref.update({"analysis": firestore.DELETE_FIELD, "last_analyzed_at": None})
                self.refresh_metadata(uid, work_id)
        except Exception as error:
            raise WorkspaceError(tr("The chapter analysis status could not be updated.", "Status analisis bab gagal diperbarui.")) from error

    def refresh_metadata(self, uid: str, work_id: str) -> dict[str, Any] | None:
        metadata = aggregate(self.list_chapters(uid, work_id))
        update: dict[str, Any] = {"rating": metadata["rating"] if metadata else None, "metadata": metadata}
        if metadata:
            update["metadata"] = {**metadata, "updated_at": datetime.now(timezone.utc)}
        self._works(uid).document(work_id).update(update)
        return metadata

    def delete_work(self, uid: str, work_id: str) -> None:
        """Hapus cerita beserta semua bab dan analisis Workspace-nya."""
        ref = self._works(uid).document(work_id)
        history = self._client.collection("users").document(uid).collection("history")
        try:
            for snapshot in ref.collection("chapters").stream():
                snapshot.reference.delete()
            for snapshot in history.where(filter=firestore.FieldFilter("work_id", "==", work_id)).stream():
                snapshot.reference.delete()
            ref.delete()
        except Exception as error:
            raise WorkspaceError(tr("The story could not be deleted.", "Cerita gagal dihapus.")) from error
