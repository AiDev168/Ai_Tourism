"""Process-local owner API app for isolated HTTP contract tests only.

This module imports TourismRagApiV1's actual API DTOs and route factory. Its
engine and approval policy return one deterministic test fixture; no index,
embedding model, network provider, source record, or traveler data is loaded.
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

owner_root = Path(os.environ["OWNER_RAG_TEST_API_ROOT"]).resolve()
if not (owner_root / "owner_rag_api" / "app.py").is_file():
    raise RuntimeError("test owner API source root is invalid")
sys.path.insert(0, str(owner_root))

from owner_rag_api.app import create_app  # noqa: E402
from owner_rag_api.models import (  # noqa: E402
    EngineResult,
    EvidenceSource,
    RetrievedEvidence,
)

FIXTURE_KEY = "issue5-test-only-eram-garden"
FIXTURE_DOCUMENT = "issue5-test-only-document-v1"
FIXTURE_CLAIM = "issue5.test_only.claim"
FIXTURE_EVIDENCE = "issue5-test-only-evidence-v1"
FIXTURE_TEXT = "TEST FIXTURE ONLY: identity-mapping transport evidence; not visitor advice."
FIXTURE_SOURCE_ID = "990701"
FIXTURE_SOURCE_NAME = "Issue 5 isolated test fixture"
FIXTURE_SOURCE_URL = "https://example.invalid/issue5-test-fixture"
FIXTURE_SOURCE_ROLE = "test_fixture"
FIXTURE_LICENSE = "TEST ONLY"
FIXTURE_HASH = hashlib.sha256(FIXTURE_TEXT.encode("utf-8")).hexdigest()
FIXTURE_RETRIEVED_AT = datetime(2020, 1, 1, tzinfo=UTC)
FIXTURE_VALID_FROM = datetime(2020, 1, 1, tzinfo=UTC)
FIXTURE_VALID_UNTIL = datetime(2099, 1, 1, tzinfo=UTC)


class TestOnlyEngine:
    ready = True
    empty_approved_snapshot = False

    async def retrieve(self, request):
        if (
            request.filters.get("canonical_entity_key") != FIXTURE_KEY
            or request.locale != "fa-IR"
            or request.corpus.value != "spatial_destinations"
        ):
            return EngineResult(items=[], corpus_version="test-only-v1", retrieval_version="fixture-v1")
        source = EvidenceSource(
            source_id=FIXTURE_SOURCE_ID,
            source_name=FIXTURE_SOURCE_NAME,
            source_url=FIXTURE_SOURCE_URL,
            source_role=FIXTURE_SOURCE_ROLE,
            license=FIXTURE_LICENSE,
            retrieved_at=FIXTURE_RETRIEVED_AT,
            valid_from=FIXTURE_VALID_FROM,
            valid_until=FIXTURE_VALID_UNTIL,
        )
        return EngineResult(
            items=[RetrievedEvidence(
                evidence_id=FIXTURE_EVIDENCE,
                document_id=FIXTURE_DOCUMENT,
                content_hash=FIXTURE_HASH,
                text=FIXTURE_TEXT,
                locale=request.locale,
                corpus=request.corpus,
                canonical_entity_key=FIXTURE_KEY,
                claim_key=FIXTURE_CLAIM,
                score=0.73,
                sources=[source],
            )],
            corpus_version="test-only-approved-fixture-v1",
            retrieval_version="test-engine-v1",
        )


class TestOnlyApproval:
    ready = True

    def approved(self, item, request):
        return (
            item.evidence_id == FIXTURE_EVIDENCE
            and item.document_id == FIXTURE_DOCUMENT
            and item.content_hash == FIXTURE_HASH
            and item.canonical_entity_key == FIXTURE_KEY
            and item.claim_key == FIXTURE_CLAIM
            and item.text == FIXTURE_TEXT
            and request.filters.get("canonical_entity_key") == FIXTURE_KEY
        )


token = os.environ["OWNER_RAG_TEST_API_TOKEN"]
if len(token) < 24:
    raise RuntimeError("test owner API token is too short")

app = create_app(engine=TestOnlyEngine(), approval=TestOnlyApproval(), auth_token=token)
