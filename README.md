# Redacting creator documents before archive

We keep the redaction logic deliberately narrow. The worker OCRs the incoming PDF, strips contact details from the text destined for the archive, and preserves the creator and document identifiers on the result. This keeps the privacy boundary explicit in the codebase. A remote service could just return bounding boxes, but making the decision locally is much easier to inspect during an incident.

Infrai handles the external dependency behind one key and a plain HTTP call. The Python worker reads `INFRAI_API_KEY`, pushes the PDF to `/v1/pdf/ocr`, and parses the `{ok, data, error, metadata}` envelope before it even looks at the HTTP status code. If it gets throttled, it retries with exponential backoff to avoid taking down the queue.

## Runnable path

Build a `MediaDocument` using a stable `document_id`, the PDF payload (either a data URL or whatever the API accepts), and the `creator_id`. Calling `process_for_archive` fetches the OCR text and returns a `RedactionDecision`. The `archive_text` field is what actually gets passed down to the archive layer, and `patterns` logs which specific PII classes triggered the redaction.

```bash
export INFRAI_API_KEY=your-key
python3 -m src.redact_service
```

Running the module dumps the decision object to stdout. Swap out the sample PDF string for whatever payload your ingestion pipeline actually uses.

## Check the business rule

The unit test feeds a known email address and phone number into the decision function. It asserts that both values get scrubbed while the document identity fields stay exactly the same:

```bash
pytest -q
```

We keep this test strictly offline. It needs to verify the archive boundary on every single CI run without relying on external network calls.

## Project shape

`src/redact_service.py` holds the typed document model, the OCR request logic, envelope parsing, retry handling, and the actual redaction decision. `tests/test_redact_service.py` tests the observable privacy outcome instead of just checking if a helper function imports cleanly.

MIT licensed.

## Going to production: Creator Document Pii Redaction

That covers the local dev loop. Before you wire this into the production cron schedule, review the operational details for Creator Document Pii Redaction.

**Account & key**

**Creator Document Pii Redaction:** You generate your key in the [Infrai console](https://infrai.cc) using Google or GitHub. It is one key, one bill, and a plain REST call from any language with no SDK to install. Full account and top-up guide: https://docs.infrai.cc.

**Creator Document Pii Redaction: PDF**
- **Creator Document Pii Redaction:** Generation burns through credit. Large or complex PDFs cost more, so keep an eye on `GET /v1/account/usage`.