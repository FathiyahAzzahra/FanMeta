"""Firestore persistence for the public FanMeta gallery.

Struktur data (terpisah dari riwayat pribadi users/{uid}/history):
    public_works/{work_id}                  salinan cerita yang dipublikasikan
    public_works/{work_id}/likes/{uid}      satu like per akun
    public_works/{work_id}/comments/{id}    komentar
    users/{uid}                             profil, berisi pen_name

work_id = "{uid}_{analysis_id}", jadi satu riwayat hanya bisa dipublikasikan sekali.
Aplikasi memakai service account (akses admin), sehingga semua pengecekan hak akses
(siapa boleh unpublish / hapus komentar) dilakukan di kelas ini.
"""

from datetime import datetime, timezone
from typing import Any

from firebase_admin import firestore

from src.firestore_history import PROBABILITY_FIELDS, probs_to_rows, rows_to_probs

SNIPPET_CHARS = 300
MAX_COMMENT_CHARS = 1000
MAX_PEN_NAME_CHARS = 40
# field yang diambil untuk daftar galeri (cerita lengkap tidak ikut, supaya ringan)
_LIST_FIELDS = [
    "owner_uid", "pen_name", "title", "language", "snippet", "word_count", "rating",
    "warnings", "tags", "like_count", "comment_count", "published_at",
]


class GalleryError(RuntimeError):
    """A user-safe error raised when the gallery cannot be accessed."""


def clean_pen_name(name: str) -> str:
    name = " ".join(str(name).split())[:MAX_PEN_NAME_CHARS]
    if not name:
        raise GalleryError("Nama pena tidak boleh kosong.")
    return name


class GalleryStore:
    def __init__(self, client: Any) -> None:
        self._client = client

    # ---------- referensi ----------
    def _works(self) -> Any:
        return self._client.collection("public_works")

    def _work(self, work_id: str) -> Any:
        return self._works().document(work_id)

    @staticmethod
    def work_id_for(uid: str, analysis_id: str) -> str:
        return f"{uid}_{analysis_id}"

    # ---------- profil (nama pena) ----------
    def get_pen_name(self, uid: str) -> str | None:
        try:
            snapshot = self._client.collection("users").document(uid).get()
        except Exception as error:
            raise GalleryError("Profil tidak dapat dimuat.") from error
        return (snapshot.to_dict() or {}).get("pen_name") if snapshot.exists else None

    def set_pen_name(self, uid: str, pen_name: str) -> str:
        pen_name = clean_pen_name(pen_name)
        try:
            self._client.collection("users").document(uid).set({"pen_name": pen_name}, merge=True)
        except Exception as error:
            raise GalleryError("Nama pena gagal disimpan.") from error
        return pen_name

    # ---------- publish ----------
    def publish(self, uid: str, item: dict[str, Any], pen_name: str) -> str:
        """Salin satu riwayat ke galeri publik dan kembalikan work_id."""
        pen_name = self.set_pen_name(uid, pen_name)
        story = str(item.get("story") or "")
        work_id = self.work_id_for(uid, item["analysis_id"])
        data = {
            "owner_uid": uid,
            "analysis_id": item["analysis_id"],
            "pen_name": pen_name,
            "title": str(item.get("title") or "Untitled Draft"),
            "language": str(item.get("language") or "-"),
            "story": story,
            "snippet": story[:SNIPPET_CHARS],
            "word_count": len(story.split()),
            "rating": str(item.get("rating") or "-"),
            "warnings": list(item.get("warnings") or []),
            "tags": list(item.get("tags") or []),
            "like_count": 0,
            "comment_count": 0,
            "analyzed_at": item.get("created_at"),
            "published_at": datetime.now(timezone.utc),
        }
        for field in PROBABILITY_FIELDS:
            if item.get(field):
                data[field] = probs_to_rows(item[field])
        if item.get("segments_english"):
            data["segments_english"] = list(item["segments_english"])
        try:
            self._work(work_id).set(data)
        except Exception as error:
            raise GalleryError("Cerita gagal dipublikasikan.") from error
        return work_id

    def unpublish(self, uid: str, work_id: str) -> None:
        """Hapus cerita dari galeri beserta like & komentarnya (hanya pemilik)."""
        work = self.get_work(work_id)
        if work is None:
            return
        if work["owner_uid"] != uid:
            raise GalleryError("Hanya pemilik cerita yang dapat menghapusnya dari galeri.")
        try:
            ref = self._work(work_id)
            for sub in ("likes", "comments"):
                for snapshot in ref.collection(sub).stream():
                    snapshot.reference.delete()
            ref.delete()
        except Exception as error:
            raise GalleryError("Cerita gagal dihapus dari galeri.") from error

    def is_published(self, uid: str, analysis_id: str) -> bool:
        try:
            return self._work(self.work_id_for(uid, analysis_id)).get().exists
        except Exception as error:
            raise GalleryError("Status publikasi tidak dapat dimuat.") from error

    # ---------- baca ----------
    def list_works(self, limit: int = 200) -> list[dict[str, Any]]:
        """Cerita terbaru (tanpa isi cerita lengkap). Filter dilakukan di aplikasi."""
        try:
            snapshots = (
                self._works()
                .select(_LIST_FIELDS)
                .order_by("published_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
                .stream()
            )
            works = []
            for snapshot in snapshots:
                item = snapshot.to_dict() or {}
                item["work_id"] = snapshot.id
                works.append(item)
            return works
        except Exception as error:
            raise GalleryError("Galeri tidak dapat dimuat.") from error

    def get_work(self, work_id: str) -> dict[str, Any] | None:
        try:
            snapshot = self._work(work_id).get()
        except Exception as error:
            raise GalleryError("Cerita tidak dapat dimuat.") from error
        if not snapshot.exists:
            return None
        item = snapshot.to_dict() or {}
        item["work_id"] = snapshot.id
        return rows_to_probs(item)

    # ---------- like ----------
    def has_liked(self, work_id: str, uid: str) -> bool:
        try:
            return self._work(work_id).collection("likes").document(uid).get().exists
        except Exception as error:
            raise GalleryError("Status like tidak dapat dimuat.") from error

    def toggle_like(self, work_id: str, uid: str) -> bool:
        """Like / batal like. Kembalikan True kalau sekarang disukai."""
        work_ref = self._work(work_id)
        like_ref = work_ref.collection("likes").document(uid)

        @firestore.transactional
        def _toggle(transaction: Any) -> bool:
            if not work_ref.get(transaction=transaction).exists:
                raise GalleryError("Cerita ini sudah tidak ada di galeri.")
            if like_ref.get(transaction=transaction).exists:
                transaction.delete(like_ref)
                transaction.update(work_ref, {"like_count": firestore.Increment(-1)})
                return False
            transaction.set(like_ref, {"uid": uid, "liked_at": datetime.now(timezone.utc)})
            transaction.update(work_ref, {"like_count": firestore.Increment(1)})
            return True

        try:
            return _toggle(self._client.transaction())
        except GalleryError:
            raise
        except Exception as error:
            raise GalleryError("Like gagal disimpan.") from error

    # ---------- komentar ----------
    def list_comments(self, work_id: str, limit: int = 200) -> list[dict[str, Any]]:
        try:
            snapshots = (
                self._work(work_id).collection("comments")
                .order_by("created_at")
                .limit(limit)
                .stream()
            )
            comments = []
            for snapshot in snapshots:
                item = snapshot.to_dict() or {}
                item["comment_id"] = snapshot.id
                comments.append(item)
            return comments
        except Exception as error:
            raise GalleryError("Komentar tidak dapat dimuat.") from error

    def add_comment(self, work_id: str, uid: str, pen_name: str, text: str) -> None:
        text = str(text).strip()
        if not text:
            raise GalleryError("Komentar tidak boleh kosong.")
        if len(text) > MAX_COMMENT_CHARS:
            raise GalleryError(f"Komentar maksimal {MAX_COMMENT_CHARS} karakter.")
        pen_name = self.set_pen_name(uid, pen_name)
        work_ref = self._work(work_id)
        try:
            if not work_ref.get().exists:
                raise GalleryError("Cerita ini sudah tidak ada di galeri.")
            batch = self._client.batch()
            batch.set(work_ref.collection("comments").document(), {
                "uid": uid, "pen_name": pen_name, "text": text,
                "created_at": datetime.now(timezone.utc),
            })
            batch.update(work_ref, {"comment_count": firestore.Increment(1)})
            batch.commit()
        except GalleryError:
            raise
        except Exception as error:
            raise GalleryError("Komentar gagal dikirim.") from error

    def delete_comment(self, work_id: str, comment_id: str, uid: str) -> None:
        """Penulis komentar atau pemilik cerita boleh menghapus komentar."""
        work_ref = self._work(work_id)
        comment_ref = work_ref.collection("comments").document(comment_id)
        try:
            comment = comment_ref.get()
            work = work_ref.get()
        except Exception as error:
            raise GalleryError("Komentar tidak dapat dimuat.") from error
        if not comment.exists or not work.exists:
            return
        owner_uid = (work.to_dict() or {}).get("owner_uid")
        if uid not in ((comment.to_dict() or {}).get("uid"), owner_uid):
            raise GalleryError("Kamu tidak berhak menghapus komentar ini.")
        try:
            batch = self._client.batch()
            batch.delete(comment_ref)
            batch.update(work_ref, {"comment_count": firestore.Increment(-1)})
            batch.commit()
        except Exception as error:
            raise GalleryError("Komentar gagal dihapus.") from error
