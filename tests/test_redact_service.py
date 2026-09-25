from src.redact_service import MediaDocument, decide_redaction


def test_archive_decision_masks_email_and_phone():
    document = MediaDocument("doc-1", "inline-pdf", "creator-1")
    decision = decide_redaction(document, "Contact ada@example.com or +1 555-010-1234 for delivery")

    assert decision.document_id == "doc-1"
    assert decision.patterns == ("email", "phone")
    assert "ada@example.com" not in decision.archive_text
    assert "[REDACTED_PHONE]" in decision.archive_text
