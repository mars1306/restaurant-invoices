"""
Anthropic Claude Vision-based invoice extraction.
Supports PDF (first page converted via pdf2image) and image files.
"""
import base64
import io
import os
from typing import Any, Dict

from anthropic import Anthropic

from app.database.queries import get_config
from app.utils.helpers import safe_json_loads
from app.utils.logger import get_logger

logger = get_logger("extractor")

SYSTEM_PROMPT = (
    "Analyse cette facture fournisseur de restaurant. "
    "Extrais toutes les informations importantes et retourne STRICTEMENT un JSON valide "
    "avec la structure demandée. Si une donnée est absente, mets null. "
    "Ne fais aucun texte hors JSON."
)

JSON_STRUCTURE = """{
  "fournisseur": "",
  "date_facture": "",
  "date_echeance": "",
  "numero_facture": "",
  "produits": [
    {"nom": "", "quantite": "", "prix_unitaire": "", "prix_total": ""}
  ],
  "total_ht": "",
  "total_ttc": "",
  "tva": "",
  "statut": "non payé"
}"""

USER_PROMPT = (
    f"Extrais les informations de cette facture et retourne uniquement ce JSON complété :\n{JSON_STRUCTURE}"
)


def _get_client() -> Anthropic:
    api_key = get_config("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set. Please configure it in the Paramètres page.")
    return Anthropic(api_key=api_key)


def _file_to_base64_image(file_bytes: bytes, mime_type: str) -> str:
    """Return base64-encoded string of the image bytes."""
    return base64.b64encode(file_bytes).decode("utf-8")


def _pdf_first_page_to_image_bytes(pdf_bytes: bytes) -> bytes:
    """Convert first page of a PDF to PNG bytes using pdf2image."""
    try:
        from pdf2image import convert_from_bytes  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "pdf2image is required for PDF support. Install with: pip install pdf2image"
        ) from exc

    images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1, dpi=200)
    if not images:
        raise ValueError("Could not convert PDF to image — empty result from pdf2image.")

    buf = io.BytesIO()
    images[0].save(buf, format="PNG")
    return buf.getvalue()


def extract_invoice(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Extract invoice data from file bytes using Claude vision.

    Returns a dict with at minimum:
        {
          "fournisseur": ...,
          "date_facture": ...,
          ...
          "_extraction_error": None | str   # set if extraction partially failed
        }
    """
    ext = os.path.splitext(filename)[1].lower()

    try:
        if ext == ".pdf":
            logger.info("Converting PDF to image for extraction: %s", filename)
            image_bytes = _pdf_first_page_to_image_bytes(file_bytes)
            mime_type = "image/png"
        elif ext in (".jpg", ".jpeg"):
            image_bytes = file_bytes
            mime_type = "image/jpeg"
        elif ext == ".png":
            image_bytes = file_bytes
            mime_type = "image/png"
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        b64 = _file_to_base64_image(image_bytes, mime_type)
        client = _get_client()

        logger.info("Calling Claude vision for: %s", filename)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": USER_PROMPT},
                    ],
                }
            ],
        )

        raw_text = response.content[0].text if response.content else ""
        logger.debug("Raw extraction response: %s", raw_text[:500])

        parsed = safe_json_loads(raw_text)
        if parsed is None:
            logger.warning("JSON parsing failed for %s, returning partial data.", filename)
            return _empty_invoice(error=f"Could not parse JSON from model response: {raw_text[:200]}")

        parsed["_extraction_error"] = None
        return parsed

    except Exception as exc:
        logger.error("Extraction failed for %s: %s", filename, exc, exc_info=True)
        result = _empty_invoice(error=str(exc))
        return result


def _empty_invoice(error: str = "") -> Dict[str, Any]:
    return {
        "fournisseur": None,
        "date_facture": None,
        "date_echeance": None,
        "numero_facture": None,
        "produits": [],
        "total_ht": None,
        "total_ttc": None,
        "tva": None,
        "statut": "non payé",
        "_extraction_error": error,
    }
