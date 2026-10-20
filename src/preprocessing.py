"""Text preparation preserved from the research pipeline."""

import re
import unicodedata


SEGMENT_WORDS = 200
OVERLAP_WORDS = 50
SEGMENT_STEP = SEGMENT_WORDS - OVERLAP_WORDS

HTML_PATTERN = re.compile(r"<[^>]+>")
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", flags=re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"\s+")


def preprocess_text(text: str) -> str:
    """Apply the Notebook 1+2 preprocessing used to produce training text."""
    text = str(text)
    text = HTML_PATTERN.sub(" ", text)
    text = URL_PATTERN.sub(" ", text)
    text = unicodedata.normalize("NFKC", text)
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def split_segments(
    text: str,
    segment_words: int = SEGMENT_WORDS,
    overlap_words: int = OVERLAP_WORDS,
) -> list[str]:
    """Split text exactly as in Notebook 3: word windows with overlap."""
    words = str(text).split()

    if not words:
        return [""]
    if len(words) <= segment_words:
        return [" ".join(words)]

    segments = []
    for start in range(0, len(words), segment_words - overlap_words):
        segment = words[start : start + segment_words]
        if not segment:
            break
        segments.append(" ".join(segment))
        if start + segment_words >= len(words):
            break

    return segments
