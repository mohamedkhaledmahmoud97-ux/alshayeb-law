"""
Arabic text normalization for ALSHAYEB LAW.

Applies character-level normalization only.
Does NOT use camel-tools here to keep the ingestion pipeline dependency-light;
camel-tools is reserved for query-time normalization where morphological analysis
is needed.
"""

import re
import unicodedata


# Alef variants → bare alef
_ALEF_RE = re.compile(r"[أإآٱ]")
# Teh marbuta → heh
_TEH_MARBUTA_RE = re.compile(r"ة")
# Yeh variants → dotless yeh
_YEH_RE = re.compile(r"[ىئ]")
# Tatweel (kashida)
_TATWEEL_RE = re.compile(r"\u0640")
# Arabic diacritics (harakat + shadda + sukun + tanwin)
_DIACRITICS_RE = re.compile(r"[\u064B-\u065F\u0670]")
# Collapse multiple whitespace
_WHITESPACE_RE = re.compile(r"[ \t]+")


def normalize_arabic(text: str, *, remove_diacritics: bool = True) -> str:
    """
    Normalize Arabic text for indexing.

    Steps applied in order:
    1. Unicode NFC normalization.
    2. Alef variants → bare alef (ا).
    3. Teh marbuta → heh (ه).
    4. Yeh variants → dotless yeh (ي).
    5. Remove tatweel.
    6. Optionally remove diacritics (default: True).
    7. Collapse multiple spaces/tabs to a single space.
    8. Strip leading/trailing whitespace.

    Args:
        text: Raw Arabic text.
        remove_diacritics: Whether to strip harakat. Default True.

    Returns:
        Normalized text string.
    """
    text = unicodedata.normalize("NFC", text)
    text = _ALEF_RE.sub("ا", text)
    text = _TEH_MARBUTA_RE.sub("ه", text)
    text = _YEH_RE.sub("ي", text)
    text = _TATWEEL_RE.sub("", text)
    if remove_diacritics:
        text = _DIACRITICS_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()
