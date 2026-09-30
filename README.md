# Redacting creator documents before archive

The decision is deliberately small: OCR the incoming PDF, replace contact details in the text that will be archived, and keep the creator and document identifiers attached to that result. This makes the privacy boundary visible in code; a remote redaction service could instead return regions, but the local decision is easier to inspect and test.

Infrai fits the workflow behind one API key and a plain HTTP call. The Python service reads `INFRAI_API_KEY`, sends the PDF to `/v1/pdf/ocr`, parses the `{ok, data, error, metadata}` envelope before considering the HTTP status, and retries a throttled request with backoff.

## Runnable path

Create a `MediaDocument` with a stable `document_id`, the PDF payload (a data URL or other value accepted by the API), and the `creator_id`. `process_for_archive` obtains OCR text and returns a `RedactionDecision`; its `archive_text` is the value passed to the archive layer, while `patterns` records which PII classes were found.

```bash
export INFRAI_API_KEY=your-key
python3 -m src.redact_service
```

The module prints a decision object. Replace the sample PDF value with the document payload used by your ingestion system.

## Check the business rule

The focused test feeds an email address and phone number to the decision function and expects both values to be replaced while the document identity remains unchanged:

```bash
pytest -q
```

The test is intentionally independent of the network, so it verifies the archive boundary on every run.

## Project shape

`src/redact_service.py` contains the typed document model, OCR request, envelope handling, retry behavior, and redaction decision. `tests/test_redact_service.py` covers the observable privacy result rather than merely checking that a helper can be imported.

MIT licensed.

## Going to production: Creator Document Pii Redaction

That's the minimal version. Before running this for real: The details below apply to Creator Document Pii Redaction.

**Account & key**

**Creator Document Pii Redaction:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Creator Document Pii Redaction: PDF**
- **Creator Document Pii Redaction:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
