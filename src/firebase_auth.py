"""Small Firebase Authentication REST client for the Streamlit interface."""

from typing import Any

import requests

from src.i18n import tr


class FirebaseAuthError(RuntimeError):
    """A user-safe authentication error returned by Firebase."""


class FirebaseAuth:
    """Register and sign in users through Firebase Identity Toolkit REST APIs."""

    base_url = "https://identitytoolkit.googleapis.com/v1/accounts"

    def __init__(self, api_key: str) -> None:
        if not api_key.strip():
            raise ValueError("Firebase API key is empty.")
        self.api_key = api_key

    def register(self, email: str, password: str) -> dict[str, str]:
        return self._authenticate("signUp", email, password)

    def login(self, email: str, password: str) -> dict[str, str]:
        return self._authenticate("signInWithPassword", email, password)

    def _authenticate(self, action: str, email: str, password: str) -> dict[str, str]:
        try:
            response = requests.post(
                f"{self.base_url}:{action}?key={self.api_key}",
                json={"email": email, "password": password, "returnSecureToken": True},
                timeout=15,
            )
        except requests.RequestException as error:
            raise FirebaseAuthError(tr("Could not connect to the authentication service.", "Tidak dapat terhubung ke layanan autentikasi.")) from error

        payload: dict[str, Any] = response.json() if response.content else {}
        if not response.ok:
            code = payload.get("error", {}).get("message", "AUTHENTICATION_FAILED")
            raise FirebaseAuthError(f"Firebase error: {code}")

        if not all(key in payload for key in ("localId", "email", "idToken")):
            raise FirebaseAuthError(tr("The authentication response was incomplete.", "Respons autentikasi tidak lengkap."))

        return {
            "uid": str(payload["localId"]),
            "email": str(payload["email"]),
            "id_token": str(payload["idToken"]),
        }


def _friendly_error(code: str) -> str:
    """Avoid showing raw Firebase errors or sensitive request details in the UI."""
    messages = {
        "EMAIL_EXISTS": tr("That email is already registered.", "Email tersebut sudah terdaftar."),
        "EMAIL_NOT_FOUND": tr("Invalid email or password.", "Email atau password tidak valid."),
        "INVALID_PASSWORD": tr("Invalid email or password.", "Email atau password tidak valid."),
        "INVALID_LOGIN_CREDENTIALS": tr("Invalid email or password.", "Email atau password tidak valid."),
        "WEAK_PASSWORD : Password should be at least 6 characters": (
            tr("Password must be at least 6 characters.", "Password minimal harus terdiri dari 6 karakter.")
        ),
        "OPERATION_NOT_ALLOWED": tr("Email/password sign-in is not enabled in Firebase.", "Login email/password belum diaktifkan di Firebase."),
        "TOO_MANY_ATTEMPTS_TRY_LATER": tr("Too many attempts. Please try again later.", "Terlalu banyak percobaan. Silakan coba lagi nanti."),
    }
    return messages.get(code, tr("Authentication failed. Please try again.", "Autentikasi gagal. Silakan coba lagi."))
