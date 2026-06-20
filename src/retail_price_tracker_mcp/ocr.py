from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

PRICE_RE = re.compile(r"(?:NT\$|TWD|\$)?\s*([0-9][0-9,]{1,6})(?:\s*元)?", re.IGNORECASE)
# A single garment size token; longest/most-specific alternatives first so that,
# e.g., "XXL" is preferred over a partial "XL" match.
_SIZE_TOKEN = r"(?:XXXL|XXL|XXS|XS|XL|[345]XL|S|M|L)"
# A line that is *only* size tokens separated by spaces/slashes/commas/dashes,
# e.g. "S M L XL XXL", "S/M/L", "XS-S", or a lone "M".
SIZE_ONLY_RE = re.compile(
    rf"^{_SIZE_TOKEN}(?:[\s/,\-]+{_SIZE_TOKEN})*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class OCRResult:
    provider: str
    text_lines: list[str]
    raw: dict[str, Any]


class OCRProvider(Protocol):
    name: str

    def extract_text(self, image_path: str | Path) -> OCRResult: ...


class StaticOCRProvider:
    """Test/demo OCR provider that returns predefined lines without model I/O."""

    name = "static"

    def __init__(self, lines: list[str]):
        self.lines = lines

    def extract_text(self, image_path: str | Path) -> OCRResult:
        return OCRResult(provider=self.name, text_lines=self.lines, raw={"source": "static"})


class PaddleOCRProvider:
    """Lazy PaddleOCR wrapper.

    PaddleOCR is intentionally optional because its model dependencies are large.
    Install with the package's `ocr` extra before using this provider.
    """

    name = "paddleocr"

    def __init__(self, lang: str = "ch"):
        self.lang = lang
        self._engine: Any | None = None

    def extract_text(self, image_path: str | Path) -> OCRResult:
        engine = self._get_engine()
        raw_result = engine.predict(str(image_path))
        lines = _lines_from_paddle_result(raw_result)
        return OCRResult(provider=self.name, text_lines=lines, raw={"engine": self.name})

    def _get_engine(self) -> Any:
        if self._engine is None:
            try:
                from paddleocr import PaddleOCR
            except ImportError as exc:  # pragma: no cover - optional dependency path
                raise RuntimeError(
                    "PaddleOCR is not installed. Install OCR extras, "
                    "e.g. `uv pip install -e '.[ocr]'`."
                ) from exc
            # PaddleOCR 3.x. oneDNN/MKLDNN is disabled because its PIR runtime
            # path raises NotImplementedError on the PP-OCRv6 models on some
            # CPUs; the default CPU backend is slower but works everywhere.
            self._engine = PaddleOCR(lang=self.lang, enable_mkldnn=False)
        return self._engine


def default_ocr_provider() -> OCRProvider:
    return PaddleOCRProvider()


def parse_price_hint(lines: list[str]) -> int | None:
    prices: list[int] = []
    for line in lines:
        for match in PRICE_RE.finditer(line.replace(",", "")):
            value = int(match.group(1))
            if 10 <= value <= 100000:
                prices.append(value)
    return min(prices) if prices else None


def text_hints_from_ocr(lines: list[str]) -> list[str]:
    hints: list[str] = []
    for line in lines:
        cleaned = " ".join(line.strip().split())
        if not cleaned:
            continue
        if PRICE_RE.fullmatch(cleaned.replace(",", "")):
            continue
        if SIZE_ONLY_RE.fullmatch(cleaned):
            continue
        if cleaned.upper().startswith(("NT$", "TWD")):
            continue
        hints.append(cleaned)
    return hints


def query_from_ocr(lines: list[str]) -> str:
    return " ".join(text_hints_from_ocr(lines))


def _lines_from_paddle_result(raw_result: Any) -> list[str]:
    # PaddleOCR 3.x predict() returns a list of dict-like OCRResult objects,
    # each exposing the recognized strings under "rec_texts".
    lines: list[str] = []
    for page in raw_result or []:
        texts = page.get("rec_texts") if hasattr(page, "get") else None
        for text in texts or []:
            cleaned = str(text).strip()
            if cleaned:
                lines.append(cleaned)
    return lines
