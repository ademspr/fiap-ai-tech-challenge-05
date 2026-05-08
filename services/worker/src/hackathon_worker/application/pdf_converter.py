"""Convert PDF documents to PNG images for LLM vision input."""

import io

import pypdfium2 as pdfium


def pdf_to_png_bytes(pdf_bytes: bytes, max_pages: int = 3, scale: float = 2.0) -> list[bytes]:
    """Render up to *max_pages* pages of a PDF as PNG bytes.

    Args:
        pdf_bytes: Raw PDF file content.
        max_pages: Maximum number of pages to render (first N pages).
        scale: Rendering scale factor (2.0 gives ~144 DPI from 72 DPI base).

    Returns:
        List of PNG image bytes, one per rendered page.
    """
    pdf = pdfium.PdfDocument(pdf_bytes)
    pages_to_render = min(len(pdf), max_pages)
    result: list[bytes] = []

    for i in range(pages_to_render):
        page = pdf[i]
        bitmap = page.render(scale=scale, rotation=0)
        pil_image = bitmap.to_pil()
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        result.append(buf.getvalue())

    return result
