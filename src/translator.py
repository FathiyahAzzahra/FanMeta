"""Indonesian-to-English translation used before FanMeta inference.

The translation model is intentionally independent from the FanMeta models so
loading or using it cannot change the trained FanMeta checkpoints.
"""

from collections.abc import Sequence

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


NLLB_MODEL_NAME = "facebook/nllb-200-distilled-600M"
SRC_LANG = "ind_Latn"
TGT_LANG = "eng_Latn"


class IndonesianToEnglishTranslator:
    """Lazy-load NLLB-200 and translate Indonesian text chunks to English."""

    def __init__(
        self,
        model_name: str = NLLB_MODEL_NAME,
        device: str | torch.device | None = None,
    ) -> None:
        self.model_name = model_name
        self.device = torch.device(
            device if device is not None else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self._tokenizer = None
        self._model = None

    def _load(self) -> None:
        """Load the translation model only when Indonesian input is received."""
        if self._model is not None:
            return

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name).to(self.device)
        self._model.eval()

    def translate_batch(
        self,
        text_list: Sequence[str],
        batch_size: int = 64,
        max_length: int = 160,
    ) -> list[str]:
        """Translate chunks using the STEP 15 NLLB-200 generation settings."""
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1.")
        if max_length < 1:
            raise ValueError("max_length must be at least 1.")
        if not text_list:
            return []

        self._load()
        assert self._tokenizer is not None
        assert self._model is not None

        self._tokenizer.src_lang = SRC_LANG
        forced_bos_token_id = self._tokenizer.convert_tokens_to_ids(TGT_LANG)
        if forced_bos_token_id is None or forced_bos_token_id == self._tokenizer.unk_token_id:
            raise ValueError(f"NLLB target language token is unavailable: {TGT_LANG}")

        translated: list[str] = []
        for start in range(0, len(text_list), batch_size):
            batch = list(text_list[start : start + batch_size])
            inputs = self._tokenizer(
                batch,
                return_tensors="pt",
                truncation=True,
                max_length=max_length,
                padding=True,
            ).to(self.device)
            with torch.inference_mode():
                generated = self._model.generate(
                    **inputs,
                    forced_bos_token_id=forced_bos_token_id,
                    max_length=max_length,
                    num_beams=1,
                )
            translated.extend(
                self._tokenizer.batch_decode(generated, skip_special_tokens=True)
            )

        return translated

    def translate(self, text: str, max_length: int = 160) -> str:
        """Translate one Indonesian text chunk to English."""
        return self.translate_batch([text], max_length=max_length)[0]
