"""
PDF utility — extracts PDF pages as PNG images for Gemini vision.

Uses PyMuPDF (fitz) to render PDF pages at high resolution.
"""

import io
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def get_pdf_path(pdf_key: str) -> Optional[str]:
    """Resolve PDF key to filesystem path."""
    if not pdf_key:
        return None
    pdfs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pdfs")
    path = os.path.join(pdfs_dir, pdf_key)
    if os.path.exists(path):
        return path
    return None


def extract_slide_image(pdf_path: str, page_number: int, dpi: int = 200) -> Optional[bytes]:
    """Extract a single page from a PDF as PNG bytes.

    Args:
        pdf_path: Path to the PDF file.
        page_number: 1-based page number.
        dpi: Resolution for rendering (200 = good quality, ~400KB per page).

    Returns:
        PNG image bytes, or None if extraction fails.
    """
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)

        if page_number < 1 or page_number > len(doc):
            logger.warning(f"Page {page_number} out of range (PDF has {len(doc)} pages)")
            doc.close()
            return None

        page = doc[page_number - 1]  # 0-based index

        # Render at specified DPI
        zoom = dpi / 72  # 72 is default PDF DPI
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        png_bytes = pix.tobytes("png")
        doc.close()

        logger.info(f"Extracted slide {page_number}: {len(png_bytes)} bytes ({pix.width}x{pix.height})")
        return png_bytes

    except ImportError:
        logger.error("PyMuPDF (fitz) not installed. Run: pip install pymupdf")
        return None
    except Exception as e:
        logger.error(f"Failed to extract slide {page_number} from {pdf_path}: {e}")
        return None
