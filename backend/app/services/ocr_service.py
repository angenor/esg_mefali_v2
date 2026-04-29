"""F22 - OcrService MVP (extraction texte natif PDF via pypdf).

Scope MVP :
- ``extract_text_from_pdf(data, timeout_s)`` : extrait le texte natif d'un PDF
  via pypdf, dans un thread isole avec timeout dur (default 30s, FR-015).
- ``extract_text(mime, data)`` : dispatcher haut niveau qui retourne un
  ``OcrOutcome`` (status, text, error) selon le mime :
    - PDF -> tente extraction native ; vide -> deferred ; ok -> done ; erreur -> failed
    - JPG/PNG/HEIC/DOCX/XLSX -> deferred (extraction reportee post-MVP)
    - autre -> failed (mime non supporte ; ne devrait pas arriver si la
      validation amont est correcte).

DEFERRED post-MVP : Tesseract pour images, python-docx, openpyxl,
Replicate Whisper audio, embeddings Voyage.
"""

from __future__ import annotations

import io
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DEFAULT_OCR_TIMEOUT_S: float = 30.0

_PDF_MIME = "application/pdf"
_DEFERRED_IMAGE_MIMES = frozenset({"image/jpeg", "image/png", "image/heic"})
_DEFERRED_OFFICE_MIMES = frozenset({
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
})


@dataclass(frozen=True)
class OcrOutcome:
    """Resultat d'une tentative d'extraction de texte.

    - status : 'done' | 'deferred' | 'failed'
    - text : texte extrait (uniquement si status == 'done', sinon None)
    - error : message lisible (uniquement si status in {'deferred','failed'})
    """

    status: str
    text: str | None
    error: str | None


def _read_pdf_text_sync(data: bytes) -> str:
    """Lecture pypdf synchrone (a executer dans un thread).

    Retourne la concatenation du texte natif des pages, separees par '\n'.
    Chaine vide si aucun texte natif extractible.
    """
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("pypdf: page extract_text failed: %s", exc)
            txt = ""
        if txt:
            parts.append(txt)
    return "\n".join(parts).strip()


def extract_text_from_pdf(
    data: bytes,
    *,
    timeout_s: float = DEFAULT_OCR_TIMEOUT_S,
) -> str:
    """Extrait le texte natif d'un PDF avec timeout dur.

    Leve ``TimeoutError`` si l'extraction depasse ``timeout_s`` secondes.
    Leve toute autre exception remontee par pypdf (PDF corrompu,
    encryption non supportee, ...).
    """
    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(_read_pdf_text_sync, data)
        try:
            return future.result(timeout=timeout_s)
        except FuturesTimeoutError as exc:
            future.cancel()
            raise TimeoutError(f"OCR PDF timeout > {timeout_s}s") from exc


def extract_text(
    mime: str,
    data: bytes,
    *,
    timeout_s: float = DEFAULT_OCR_TIMEOUT_S,
) -> OcrOutcome:
    """Dispatcher MVP : applique l'extraction selon le mime.

    Ne leve jamais : encapsule toutes les erreurs en OcrOutcome(failed, ...).
    """
    if mime == _PDF_MIME:
        try:
            text = extract_text_from_pdf(data, timeout_s=timeout_s)
        except TimeoutError as exc:
            return OcrOutcome(status="failed", text=None, error=str(exc))
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("OCR PDF extraction failed: %s", exc)
            return OcrOutcome(
                status="failed",
                text=None,
                error=f"pdf_extract_error: {type(exc).__name__}",
            )
        if not text:
            return OcrOutcome(
                status="deferred",
                text=None,
                error="pdf_no_native_text",
            )
        return OcrOutcome(status="done", text=text, error=None)

    if mime in _DEFERRED_IMAGE_MIMES:
        return OcrOutcome(
            status="deferred",
            text=None,
            error="mvp_image_unsupported",
        )

    if mime in _DEFERRED_OFFICE_MIMES:
        return OcrOutcome(
            status="deferred",
            text=None,
            error="mvp_office_unsupported",
        )

    return OcrOutcome(
        status="failed",
        text=None,
        error=f"mime_not_supported: {mime}",
    )
