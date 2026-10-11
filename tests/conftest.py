from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bulk_certificate_generator.app import create_app
from bulk_certificate_generator.core.config import Settings


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        certificate_storage_dir=tmp_path / "certificates",
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def valid_payload() -> dict:
    return {
        "title": "Backend Engineering Bootcamp",
        "issuer": "BULK",
        "issue_date": "2026-10-11",
        "recipients": [
            {
                "name": "Aarav Mehta",
                "email": "aarav@example.com",
                "custom_fields": {"grade": "A"},
            }
        ],
    }
