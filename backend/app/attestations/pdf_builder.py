"""F30 - Generation PDF basique d'attestation verifiable.

Template minimaliste reportlab + QR code via la lib ``qrcode``. Pas de polish
typographique en MVP : on optimise pour la verification.

Le PDF inclut :
- entete (nom PME, date emission, identifiant public, validite),
- tableau des scores avec versions de referentiels,
- QR code pointant vers ``verify_url``,
- pied de page : signature Ed25519 hex tronquee, fingerprint cle publique.

Aucun acces reseau ni base : function pure (input -> bytes).
"""

from __future__ import annotations

import io
from typing import Any

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def _build_qr_png_bytes(url: str) -> bytes:
    """Render a QR code as PNG bytes."""
    qr = qrcode.QRCode(box_size=4, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _truncate(value: str, head: int = 8, tail: int = 8) -> str:
    if len(value) <= head + tail + 1:
        return value
    return f"{value[:head]}...{value[-tail:]}"


def render_attestation_pdf(
    *,
    entreprise_name: str,
    public_id: str,
    generated_at_iso: str,
    valid_until_iso: str,
    scores: dict[str, Any],
    referentiels_versions: dict[str, str],
    verify_url: str,
    signature_hex: str,
    pubkey_fingerprint: str,
) -> bytes:
    """Render the attestation PDF and return its bytes.

    Pure function: same inputs -> same bytes (modulo reportlab metadata).
    """
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    margin = 20 * mm

    # ---- Header
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, height - margin, "Attestation ESG Mefali")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin, height - margin - 6 * mm, f"PME : {entreprise_name}")
    pdf.drawString(
        margin, height - margin - 12 * mm, f"Identifiant public : {public_id}"
    )
    pdf.drawString(margin, height - margin - 18 * mm, f"Emise le : {generated_at_iso}")
    pdf.drawString(
        margin, height - margin - 24 * mm, f"Valide jusqu'au : {valid_until_iso}"
    )

    # ---- Scores
    y = height - margin - 40 * mm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "Scores inclus")
    y -= 6 * mm
    pdf.setFont("Helvetica", 10)
    if not scores:
        pdf.drawString(margin, y, "(aucun score selectionne)")
        y -= 6 * mm
    else:
        for key, value in sorted(scores.items()):
            pdf.drawString(margin, y, f"- {key}: {value}")
            y -= 5 * mm

    # ---- Referentiels versions
    y -= 4 * mm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "Versions des referentiels")
    y -= 6 * mm
    pdf.setFont("Helvetica", 10)
    if not referentiels_versions:
        pdf.drawString(margin, y, "(aucun referentiel applicable)")
        y -= 6 * mm
    else:
        for ref, version in sorted(referentiels_versions.items()):
            pdf.drawString(margin, y, f"- {ref}: {version}")
            y -= 5 * mm

    # ---- QR
    qr_bytes = _build_qr_png_bytes(verify_url)
    qr_size = 35 * mm
    pdf.drawImage(
        ImageReader(io.BytesIO(qr_bytes)),
        width - margin - qr_size,
        height - margin - qr_size - 8 * mm,
        width=qr_size,
        height=qr_size,
        preserveAspectRatio=True,
        mask="auto",
    )
    pdf.setFont("Helvetica-Oblique", 8)
    pdf.drawString(
        width - margin - qr_size,
        height - margin - qr_size - 12 * mm,
        "Verifier sur :",
    )
    pdf.drawString(
        width - margin - qr_size,
        height - margin - qr_size - 16 * mm,
        verify_url,
    )

    # ---- Footer signature
    pdf.setFont("Helvetica", 8)
    pdf.drawString(
        margin,
        margin + 16 * mm,
        f"Signature Ed25519 : {_truncate(signature_hex, 16, 16)}",
    )
    pdf.drawString(
        margin,
        margin + 10 * mm,
        f"Empreinte cle publique : {_truncate(pubkey_fingerprint, 12, 12)}",
    )
    pdf.drawString(
        margin,
        margin + 4 * mm,
        "Preuve d'integrite technique. Verification : "
        "scanner le QR ou ouvrir le lien ci-dessus.",
    )

    pdf.showPage()
    pdf.save()
    return buf.getvalue()
