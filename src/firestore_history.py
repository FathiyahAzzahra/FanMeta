"""Firestore persistence for a logged-in FanMeta user's analysis history."""

from datetime import datetime, timezone
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore


PROBABILITY_FIELDS = ("rating_probabilities", "warning_probabilities", "tag_probabilities")


class FirestoreHistoryError(RuntimeError):
    """A user-safe error raised when analysis history cannot be accessed."""


def probs_to_rows(probs: dict[str, float]) -> list[dict[str, Any]]:
    # nama label seperti "Rape/Non-Con" mengandung karakter khusus untuk nama field
    # Firestore, jadi persen keyakinan disimpan sebagai daftar {label, prob}
    return [{"label": k, "prob": float(v)} for k, v in probs.items()]


def rows_to_probs(item: dict[str, Any]) -> dict[str, Any]:
    for field in PROBABILITY_FIELDS:
        if isinstance(item.get(field), list):
            item[field] = {row["label"]: row["prob"] for row in item[field]}
    return item


class FirestoreHistory:
    """Store and retrieve documents at users/{uid}/history/{analysis_id}."""

    def __init__(self, client: Any) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        """Firestore client, dipakai bersama oleh galeri publik."""
        return self._client

    @classmethod
    def from_service_account(cls, service_account: dict[str, Any]) -> "FirestoreHistory":
        """Create a Firestore client using service-account data from secrets."""
        try:
            try:
                app = firebase_admin.get_app("fanmeta-firestore")
            except ValueError:
                app = firebase_admin.initialize_app(
                    credentials.Certificate(service_account), name="fanmeta-firestore"
                )
            return cls(firestore.client(app=app))
        except Exception as error:
            raise FirestoreHistoryError("Riwayat analisis tidak dapat terhubung.") from error

    def save_analysis(
        self,
        *,
        firebase_uid: str,
        email: str,
        title: str,
        language: str,
        story: str,
        rating: str,
        warnings: list[str],
        tags: list[str],
        rating_probabilities: dict[str, float] | None = None,
        warning_probabilities: dict[str, float] | None = None,
        tag_probabilities: dict[str, float] | None = None,
        segments_english: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """Persist one completed prediction and return its generated analysis ID.

        ``extra`` berisi field tambahan, misalnya penanda analisis Workspace
        (source, work_id, chapter_id, ...). Analisis lama tanpa field ini = Quick Analysis.
        """
        try:
            document = (
                self._client.collection("users")
                .document(firebase_uid)
                .collection("history")
                .document()
            )
            data = {
                "firebase_uid": firebase_uid,
                "email": email,
                "title": title,
                "language": language,
                "story": story,
                "rating": rating,
                "warnings": list(warnings),
                "tags": list(tags),
                "created_at": datetime.now(timezone.utc),
            }
            for field, probs in (
                ("rating_probabilities", rating_probabilities),
                ("warning_probabilities", warning_probabilities),
                ("tag_probabilities", tag_probabilities),
            ):
                if probs:
                    data[field] = probs_to_rows(probs)
            if segments_english:
                data["segments_english"] = list(segments_english)
            if extra:
                data.update({k: v for k, v in extra.items() if k not in data})  # field lama tidak ditimpa
            document.set(data)
            return str(document.id)
        except Exception as error:
            raise FirestoreHistoryError("Riwayat analisis gagal disimpan.") from error

    def list_for_work(self, firebase_uid: str, work_id: str) -> list[dict[str, Any]]:
        """Semua analisis Workspace milik satu cerita (log), terlama dulu."""
        try:
            snapshots = (
                self._client.collection("users")
                .document(firebase_uid)
                .collection("history")
                .where(filter=firestore.FieldFilter("work_id", "==", work_id))
                .stream()
            )
            items = []
            for snapshot in snapshots:
                item = snapshot.to_dict() or {}
                item["analysis_id"] = snapshot.id
                items.append(rows_to_probs(item))
        except Exception as error:
            raise FirestoreHistoryError("Log analisis tidak dapat dimuat.") from error
        # diurutkan di aplikasi supaya tidak perlu membuat composite index di Firestore
        return sorted(items, key=lambda i: i.get("created_at") or datetime.min.replace(tzinfo=timezone.utc))

    def link_to_workspace(self, firebase_uid: str, analysis_id: str, fields: dict[str, Any]) -> None:
        """Tandai Analisis Cepat sebagai bagian dari cerita Workspace (hanya MENAMBAH field)."""
        allowed = {"source", "work_id", "work_title", "chapter_id", "chapter_number", "chapter_title"}
        try:
            (
                self._client.collection("users")
                .document(firebase_uid)
                .collection("history")
                .document(analysis_id)
                .update({k: v for k, v in fields.items() if k in allowed})
            )
        except Exception as error:
            raise FirestoreHistoryError("Analisis gagal dipindahkan ke Workspace.") from error

    def delete_analysis(self, firebase_uid: str, analysis_id: str) -> None:
        """Permanently remove one history document of the active user."""
        try:
            (
                self._client.collection("users")
                .document(firebase_uid)
                .collection("history")
                .document(analysis_id)
                .delete()
            )
        except Exception as error:
            raise FirestoreHistoryError("Riwayat analisis gagal dihapus.") from error

    def get_analysis(self, firebase_uid: str, analysis_id: str) -> dict[str, Any] | None:
        """Return one history document of the active user, or None if it does not exist."""
        try:
            snapshot = (
                self._client.collection("users")
                .document(firebase_uid)
                .collection("history")
                .document(analysis_id)
                .get()
            )
        except Exception as error:
            raise FirestoreHistoryError("Detail riwayat tidak dapat dimuat.") from error
        if not snapshot.exists:
            return None
        item = snapshot.to_dict() or {}
        item["analysis_id"] = snapshot.id
        return rows_to_probs(item)

    def list_history(self, firebase_uid: str) -> list[dict[str, Any]]:
        """Return only the active user's history, newest first."""
        try:
            snapshots = (
                self._client.collection("users")
                .document(firebase_uid)
                .collection("history")
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .stream()
            )
            history = []
            for snapshot in snapshots:
                item = snapshot.to_dict() or {}
                item["analysis_id"] = snapshot.id
                history.append(item)
            return history
        except Exception as error:
            raise FirestoreHistoryError("Riwayat analisis tidak dapat dimuat.") from error
