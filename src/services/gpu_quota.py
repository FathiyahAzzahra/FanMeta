"""Perkiraan sisa kuota ZeroGPU harian, disimpan di Firestore (dokumen app_state/zerogpu_quota).

ZeroGPU tidak punya API untuk menanyakan sisa kuota, jadi aplikasi mencatat sendiri durasi GPU
setiap analisis. Semua analisis GPU memakai token akun pemilik Space, jadi catatan ini mewakili
kuota akun itu (kecuali akun yang sama dipakai di Space ZeroGPU lain).
Kalau Space melaporkan kuota habis, sisa detik dan waktu reset dari pesan ZeroGPU yang dipakai.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

DAILY_GPU_SECONDS = 40 * 60  # kuota harian akun Hugging Face PRO (akun gratis: 5 menit, tetapi tidak bisa host ZeroGPU)
WINDOW = timedelta(hours=24)  # kuota pulih 24 jam setelah pemakaian GPU pertama


def parse_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


class GpuQuota:
    def __init__(self, client: Any) -> None:
        self._doc = client.collection("app_state").document("zerogpu_quota")

    def _read(self) -> dict[str, Any]:
        try:
            snapshot = self._doc.get()
        except Exception:  # noqa: BLE001 - kuota hanya info, jangan ganggu analisis
            return {}
        return (snapshot.to_dict() or {}) if snapshot.exists else {}

    def status(self, now: datetime | None = None) -> dict[str, Any]:
        """{"left_seconds", "exhausted", "reset_at"} untuk ditampilkan di toggle CPU/GPU."""
        now = now or datetime.now(timezone.utc)
        data = self._read()
        window_start = data.get("window_start")
        used = float(data.get("used_seconds") or 0)
        if window_start is None or now >= window_start + WINDOW:
            window_start, used = None, 0.0
        exhausted_until = data.get("exhausted_until")
        if exhausted_until is not None and exhausted_until <= now:
            exhausted_until = None
        left = 0 if exhausted_until else max(0.0, DAILY_GPU_SECONDS - used)
        reset_at = exhausted_until or (window_start + WINDOW if window_start else None)
        return {"left_seconds": int(left), "exhausted": exhausted_until is not None, "reset_at": reset_at}

    def record(self, engine: dict[str, Any] | None, now: datetime | None = None) -> None:
        """Catat hasil satu analisis (info "engine" dari Space)."""
        if not engine:
            return
        used_gpu = engine.get("device") == "gpu"
        quota_hit = engine.get("fallback_reason") == "quota"
        if not (used_gpu or quota_hit):
            return
        now = now or datetime.now(timezone.utc)
        data = self._read()
        window_start = data.get("window_start")
        used = float(data.get("used_seconds") or 0)
        if window_start is None or now >= window_start + WINDOW:
            window_start, used = now, 0.0
        if used_gpu:
            used += float(engine.get("gpu_seconds") or 0)
        updates: dict[str, Any] = {"window_start": window_start, "used_seconds": used, "updated_at": now}
        if quota_hit:
            reset_at = parse_time(engine.get("quota_reset_at")) or window_start + WINDOW
            updates["exhausted_until"] = reset_at
            updates["window_start"] = reset_at - WINDOW  # samakan dengan waktu reset asli dari ZeroGPU
            if engine.get("quota_left_seconds") is not None:
                updates["used_seconds"] = DAILY_GPU_SECONDS - float(engine["quota_left_seconds"])
        try:
            self._doc.set(updates, merge=True)
        except Exception:  # noqa: BLE001
            pass
