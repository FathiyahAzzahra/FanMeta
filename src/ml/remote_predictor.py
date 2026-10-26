"""Predictor jarak jauh: memanggil Space FanMeta Model API (hf_space/app.py) lewat gradio_client.

Hasilnya sama dengan FanMetaPredictor.predict, ditambah kunci "engine" dari Space:
perangkat yang dipakai, alasan pindah ke CPU, dan info kuota ZeroGPU.
"""
from collections.abc import Callable
from typing import Any

_INDONESIAN = {"id", "ind", "indonesian", "bahasa", "ind-latn", "ind_latn"}


class RemotePredictor:
    def __init__(self, space: str, hf_token: str | None = None) -> None:
        from gradio_client import Client

        self.space = space
        # Token wajib supaya kuota ZeroGPU dihitung ke akun pemilik (bukan kuota anonim per IP server).
        self._client = Client(space, token=hf_token, verbose=False)

    def predict(
        self,
        text: str,
        source_language: str = "en",
        *,
        language: str | None = None,
        on_stage: Callable[[str], None] | None = None,
        use_gpu: bool = False,
    ) -> dict[str, Any]:
        if language is not None:
            source_language = language
        lang = "id" if source_language.strip().lower() in _INDONESIAN else "en"
        if on_stage:
            on_stage("translating" if lang == "id" else "classifying")
        response = self._client.predict(text, lang, bool(use_gpu), api_name="/analyze")
        result = dict(response["result"])
        result["engine"] = dict(response.get("info") or {})
        return result
