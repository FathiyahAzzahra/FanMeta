"""Inference-only loader and predictor for the final FanMeta models.

Semua aturan (preprocessing, segmentasi, NLLB, model, threshold, inference)
diambil dari ``fanmeta_utils.py`` — file yang SAMA dengan notebook training.
Model dan threshold dibaca dari ``checkpoints/06_model_app.json`` hasil notebook 01.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from . import fanmeta_utils as U

NLLB_MODEL_NAME = "facebook/nllb-200-distilled-600M"


class FanMetaPredictor:
    """Load final checkpoints once and predict labels for one story at a time."""

    def __init__(
        self,
        checkpoint_dir: str | Path | None = None,
        device: str | torch.device | None = None,
    ) -> None:
        project_root = Path(__file__).resolve().parents[1]
        checkpoint_dir = Path(checkpoint_dir or project_root / "checkpoints")

        self.device = torch.device(
            device if device is not None else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.use_amp = self.device.type == "cuda"

        with (checkpoint_dir / "06_model_app.json").open("r", encoding="utf-8") as file:
            self.config = json.load(file)

        self.tokenizer = AutoTokenizer.from_pretrained(U.ENCODER_MODEL_NAME)
        self.segment_model = U.RoBERTaSegmentMultiTask().to(self.device)
        self.task_model = U.LSTM_MODELS[self.config["lstm_type"]]().to(self.device)

        self._load_checkpoint(self.segment_model, checkpoint_dir / self.config["roberta_checkpoint"], "RoBERTa")
        self._load_checkpoint(self.task_model, checkpoint_dir / self.config["lstm_checkpoint"], "LSTM")

        self.segment_model.eval()
        self.task_model.eval()

        # NLLB baru dimuat saat pertama kali ada input bahasa Indonesia.
        self._nllb_tokenizer = None
        self._nllb_model = None
        self._nllb_bos = None

    def _load_checkpoint(self, model: torch.nn.Module, path: Path, model_name: str) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"{model_name} checkpoint not found: {path}")

        checkpoint = torch.load(path, map_location=self.device, weights_only=True)
        if "model_state_dict" not in checkpoint:
            raise KeyError(f"{model_name} checkpoint has no 'model_state_dict': {path}")
        model.load_state_dict(checkpoint["model_state_dict"], strict=True)

    def _load_nllb(self) -> None:
        if self._nllb_model is not None:
            return
        self._nllb_tokenizer = AutoTokenizer.from_pretrained(NLLB_MODEL_NAME, src_lang="ind_Latn")
        model = AutoModelForSeq2SeqLM.from_pretrained(NLLB_MODEL_NAME)
        if self.use_amp:
            model = model.half()
        self._nllb_model = model.to(self.device).eval()
        self._nllb_bos = self._nllb_tokenizer.convert_tokens_to_ids("eng_Latn")

    def predict(
        self,
        text: str,
        source_language: str = "en",
        *,
        language: str | None = None,
        on_stage: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Predict labels from English or Indonesian text.

        Use ``source_language="id"`` (or ``language="id"``) for Indonesian.
        ``on_stage`` (optional) is called with "translating" and "classifying"
        so the UI can show progress.
        """
        if language is not None:
            source_language = language
        normalized_language = source_language.strip().lower().replace("_", "-")
        if normalized_language in {"en", "eng", "english", "eng-latn"}:
            is_indonesian = False
        elif normalized_language in {"id", "ind", "indonesian", "bahasa", "ind-latn"}:
            is_indonesian = True
        else:
            raise ValueError(
                "source_language must be English ('en') or Indonesian ('id')."
            )

        common = dict(
            roberta=self.segment_model,
            tokenizer=self.tokenizer,
            lstm_model=self.task_model,
            device=self.device,
            warn_thr=self.config["warning_thresholds"],
            tag_thr=self.config["tag_thresholds"],
            max_tags=self.config["max_tags"],
            use_amp=self.use_amp,
        )

        if is_indonesian:
            if on_stage:
                on_stage("translating")
            self._load_nllb()
            result = U.predict_indonesian(
                text, self._nllb_tokenizer, self._nllb_model, self._nllb_bos,
                on_stage=on_stage, **common,
            )
        else:
            if on_stage:
                on_stage("classifying")
            result = U.predict_document(text, **common)

        result["source_language"] = "id" if is_indonesian else "en"
        result["translated_to_english"] = is_indonesian
        return result
