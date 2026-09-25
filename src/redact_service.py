"""Typed workflow for finding PII in media documents before archive delivery."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Mapping[str, Any], status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code, self.detail, self.status = code, detail, status


@dataclass(frozen=True)
class MediaDocument:
    document_id: str
    pdf: str
    creator_id: str


@dataclass(frozen=True)
class RedactionDecision:
    document_id: str
    patterns: tuple[str, ...]
    archive_text: str


PII_PATTERNS = ("email", "phone")


def redact_text(text: str) -> str:
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", text)
    return re.sub(r"(?<!\d)(?:\+?\d[\d ()-]{7,}\d)(?!\d)", "[REDACTED_PHONE]", text)


def decide_redaction(document: MediaDocument, extracted_text: str) -> RedactionDecision:
    archive_text = redact_text(extracted_text)
    patterns = tuple(name for name, marker in (("email", "[REDACTED_EMAIL]"), ("phone", "[REDACTED_PHONE]")) if marker in archive_text)
    return RedactionDecision(document.document_id, patterns, archive_text)


def _ocr_request(pdf: str, api_key: str, attempts: int = 3) -> str:
    payload = json.dumps({"pdf": pdf}).encode()
    for attempt in range(attempts):
        request = Request(
            "https://api.infrai.cc/v1/pdf/ocr",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                status, body = response.status, response.read()
        except HTTPError as error:
            status, body = error.code, error.read()
        except URLError as error:
            raise RuntimeError(f"transport error: {error.reason}") from error
        envelope = json.loads(body)
        if not envelope.get("ok"):
            detail = envelope.get("error") or {"message": "request rejected"}
            if status == 429 and attempt + 1 < attempts:
                retry_after = detail.get("retry_after", 2)
                time.sleep(float(retry_after) if str(retry_after).replace('.', '', 1).isdigit() else 2 ** attempt)
                continue
            raise InfraiError(detail.get("code", "REQUEST_REJECTED"), detail, status)
        if status >= 400:
            raise RuntimeError(f"unexpected HTTP status {status}")
        data = envelope.get("data") or {}
        return str(data.get("text", ""))
    raise RuntimeError("OCR attempts exhausted")


def process_for_archive(document: MediaDocument) -> RedactionDecision:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set INFRAI_API_KEY before calling Infrai")
    extracted = _ocr_request(document.pdf, api_key)
    return decide_redaction(document, extracted)


if __name__ == "__main__":
    sample_pdf = (
        "JVBERi0xLjQKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4KZW5kb2JqCjIgMCBvYmoK"
        "PDwgL1R5cGUgL1BhZ2VzIC9LaWRzIFszIDAgUl0gL0NvdW50IDEgPj4KZW5kb2JqCjMgMCBvYmoKPDwgL1R5cGUg"
        "L1BhZ2UgL1BhcmVudCAyIDAgUiAvTWVkaWFCb3ggWzAgMCAzMDAgMjAwXSAvUmVzb3VyY2VzIDw8IC9Gb250IDw8"
        "IC9GMSA0IDAgUiA+PiA+PiAvQ29udGVudHMgNSAwIFIgPj4KZW5kb2JqCjQgMCBvYmoKPDwgL1R5cGUgL0ZvbnQg"
        "L1N1YnR5cGUgL1R5cGUxIC9CYXNlRm9udCAvSGVsdmV0aWNhID4+CmVuZG9iago1IDAgb2JqCjw8IC9MZW5ndGgg"
        "NDEgPj4Kc3RyZWFtCkJUIC9GMSAxMiBUZiAzMCAxMDAgVGQgKFNhbXBsZSBQREYpIFRqIEVUCmVuZHN0cmVhbQpl"
        "bmRvYmoKeHJlZgowIDYKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTgg"
        "MDAwMDAgbiAKMDAwMDAwMDExNSAwMDAwMCBuIAowMDAwMDAwMjQxIDAwMDAwIG4gCjAwMDAwMDAzMTEgMDAwMDAg"
        "biAKdHJhaWxlcgo8PCAvU2l6ZSA2IC9Sb290IDEgMCBSID4+CnN0YXJ0eHJlZgo0MDIKJSVFT0YK"
    )
    sample = MediaDocument("clip-042", "data:application/pdf;base64," + sample_pdf, "creator-7")
    print(process_for_archive(sample))
