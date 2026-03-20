"""
GAP-10 — Digital Signature Engine for Legal Module.

Shared utility that stamps approval events on legal documents stored in DRS.
The DRS stamp overlay embeds:
  - QR code (bottom-left) linking to a verification URL
  - Approver's signature image (bottom-right, fetched from IAM by DRS)
  - "Digitally approved — {datetime}" text
  - Separator line

This module wraps `DocumentServiceClient.generate_approved_stamp()` and follows
the same non-blocking, idempotent pattern established by the Declaration of
Independence stamp flow (GAP-9 in the audit module).

Usage
-----
Call `stamp_legal_document()` from the workflow-action view AFTER the
`transaction.atomic()` block has committed (external HTTP calls must not
run inside a DB transaction).
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def stamp_legal_document(
    entity,
    document_id_field: str,
    approver_id: str,
    entity_type: str,
    auth_token=None,
):
    """
    Apply the DRS digital-signature stamp to a legal entity's document.

    Parameters
    ----------
    entity : Model instance
        The Django model instance (e.g. FilingDefendant, JudgmentDefendant, …).
        Must have `stamped_document_url` and the field named by *document_id_field*.
    document_id_field : str
        Name of the UUID field that holds the DRS document ID on *entity*
        (e.g. ``'document_id'`` for filings/judgments, ``'agreement_document_id'``
        for settlements).
    approver_id : str
        UUID of the user whose signature should appear on the stamp (the final
        workflow approver).
    entity_type : str
        Entity type string passed to DRS for the QR verification URL
        (e.g. ``'filing_defendant'``, ``'judgment_plaintiff'``).
    auth_token : str | None
        Bearer JWT forwarded to DRS.  Must be present for user-triggered stamps.

    Returns
    -------
    bool
        ``True`` if the stamp was applied; ``False`` otherwise (logged, not raised).
    """
    doc_id = getattr(entity, document_id_field, None)
    if not doc_id:
        logger.info(
            "GAP-10: Skipping stamp for %s %s — no %s set.",
            entity_type, entity.id, document_id_field,
        )
        return False

    try:
        from apps.infrastructure.external.document_service_client import DocumentServiceClient

        client = DocumentServiceClient(auth_token=auth_token)
        result = client.generate_approved_stamp(
            document_id=str(doc_id),
            approver_id=approver_id,
            entity_type=entity_type,
            entity_id=str(entity.id),
        )

        stamped_url = result.get('stamped_document_url')
        if stamped_url:
            # Rewrite internal Docker URL → public API Gateway URL
            internal_base = settings.DOCUMENT_SERVICE_URL.rstrip('/')
            public_base = getattr(settings, 'DOCUMENT_SERVICE_PUBLIC_URL', '').rstrip('/')
            if public_base and stamped_url.startswith(internal_base):
                stamped_url = public_base + stamped_url[len(internal_base):]
            entity.stamped_document_url = stamped_url
            entity.save(update_fields=['stamped_document_url'])

        logger.info(
            "GAP-10: Stamped %s %s (document %s).",
            entity_type, entity.id, doc_id,
        )
        return True

    except Exception as exc:
        logger.warning(
            "GAP-10: Stamp failed for %s %s: %s",
            entity_type, entity.id, exc,
        )
        return False
