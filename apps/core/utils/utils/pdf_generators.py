"""
PDF generation utilities for GRC formal output documents.

WeasyPrint (already in requirements.txt) renders an HTML Django template
into PDF bytes, which are then uploaded to DRS.

The bottom page margin in every template MUST be at least 55 mm so that
the DRS stamp (QR code 30×30 mm bottom-left + signature image 65×22 mm
bottom-right) fits without overlapping the document text.
"""

import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def generate_declaration_pdf(decl) -> bytes:
    """
    Render a Declaration of Independence as PDF bytes.

    Args:
        decl: DeclarationOfIndependence model instance (with audit_engagement
              already select_related so no extra DB hit occurs).

    Returns:
        Raw PDF bytes ready to be uploaded to DRS.

    Raises:
        ImportError: if WeasyPrint is not installed (it is in requirements.txt).
        Exception:   any WeasyPrint rendering error is propagated to the caller,
                     which should catch and log it non-blocking.
    """
    from django.template.loader import render_to_string
    from weasyprint import HTML

    context = {
        'decl': decl,
        'engagement': decl.audit_engagement,
        'generated_at': timezone.now(),
    }
    html_str = render_to_string('grc/declaration_of_independence.html', context)
    return HTML(string=html_str).write_pdf()
