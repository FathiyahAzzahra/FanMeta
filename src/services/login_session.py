"""Sesi login 2 jam yang tetap ada walau koneksi putus (mis. layar HP mati) atau halaman dimuat ulang.

Login Streamlit hanya hidup di memori sesi. Supaya tidak ter-logout, browser menyimpan cookie berisi
"tiket" bertanda tangan server (uid, email, waktu kedaluwarsa), BUKAN token Firebase. Server menolak
tiket yang isinya diubah atau sudah lewat 2 jam, jadi setelah itu pengguna harus login lagi.
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Any

import streamlit as st

COOKIE_NAME = "fanmeta_session"
SESSION_SECONDS = 2 * 60 * 60


def signing_key(service_account: dict[str, Any] | None) -> bytes | None:
    """Kunci tanda tangan diturunkan dari kunci rahasia Firebase, jadi tidak perlu secret baru."""
    private_key = str((service_account or {}).get("private_key") or "")
    return hashlib.sha256(f"fanmeta-login-session:{private_key}".encode()).digest() if private_key else None


def _sign(payload: str, key: bytes) -> str:
    return hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()


def create_token(user: dict[str, str], key: bytes, now: float | None = None) -> str:
    expires = int((now if now is not None else time.time()) + SESSION_SECONDS)
    data = json.dumps({"uid": user["uid"], "email": user.get("email", ""), "exp": expires})
    payload = base64.urlsafe_b64encode(data.encode()).decode().rstrip("=")
    return f"{payload}.{_sign(payload, key)}"


def read_token(token: str | None, key: bytes, now: float | None = None) -> dict[str, Any] | None:
    """Isi tiket {"uid", "email", "exp"}, atau None kalau palsu, rusak, atau kedaluwarsa."""
    try:
        payload, signature = str(token).split(".")
        if not hmac.compare_digest(signature, _sign(payload, key)):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(data["exp"]) <= (now if now is not None else time.time()):
            return None
        return {"uid": str(data["uid"]), "email": str(data["email"]), "exp": int(data["exp"])}
    except (ValueError, KeyError, TypeError):
        return None


def restore_login(key: bytes | None) -> None:
    """Sesi baru tanpa login: pulihkan dari cookie. Tidak berlaku setelah pengguna menekan Keluar."""
    if key is None or st.session_state.get("firebase_user") or st.session_state.get("logged_out"):
        return
    data = read_token(st.context.cookies.get(COOKIE_NAME), key)
    if data is not None:
        st.session_state["firebase_user"] = {"uid": data["uid"], "email": data["email"]}
        st.session_state["login_expires"] = data["exp"]  # cookie sudah ada, tidak perlu ditulis ulang


def _set_cookie_script(value: str, max_age: int) -> str:
    return ("<script>document.cookie = "
            f'"{COOKIE_NAME}={value}; path=/; max-age={max_age}; SameSite=Lax"'
            ' + (location.protocol === "https:" ? "; Secure" : "");</script>')


def sync_cookie(key: bytes | None) -> None:
    """Tulis cookie setelah login, hapus setelah Keluar. Skrip diulang tiap render karena st.rerun
    bisa terjadi sebelum browser sempat menjalankannya; hasilnya tetap sama (kedaluwarsa tidak bergeser)."""
    if key is None:
        return
    user = st.session_state.get("firebase_user")
    if st.session_state.get("logged_out") and not user:
        st.html(_set_cookie_script("", 0), unsafe_allow_javascript=True)
    elif user:
        st.session_state.pop("logged_out", None)
        if "login_token" not in st.session_state and "login_expires" not in st.session_state:
            st.session_state["login_token"] = create_token(user, key)
            st.session_state["login_expires"] = int(time.time()) + SESSION_SECONDS
        token = st.session_state.get("login_token")
        remaining = int(st.session_state["login_expires"] - time.time())
        if token and remaining > 0:
            st.html(_set_cookie_script(token, remaining), unsafe_allow_javascript=True)
