from datetime import date
from pathlib import Path

from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

from bulk_certificate_generator.core.config import Settings
from bulk_certificate_generator.models.certificate import CertificateJob, CertificateRecipient
from bulk_certificate_generator.models.enums import JobStatus, RecipientStatus
from bulk_certificate_generator.services.dispatcher import JobDispatcher
from bulk_certificate_generator.services.pdf_generator import PdfCertificateGenerator
from bulk_certificate_generator.services.processor import CertificateJobProcessor


def test_create_generation_job(client: TestClient, valid_payload: dict) -> None:
    response = client.post("/api/v1/certificate-jobs", json=valid_payload)

    assert response.status_code == 202
    body = response.json()
    assert body["job_id"]
    assert body["total_count"] == 1


def test_input_validation_rejects_empty_recipient_list(client: TestClient, valid_payload: dict) -> None:
    valid_payload["recipients"] = []

    response = client.post("/api/v1/certificate-jobs", json=valid_payload)

    assert response.status_code == 422


def test_invalid_recipient_does_not_block_valid_recipients(client: TestClient, valid_payload: dict) -> None:
    valid_payload["recipients"].append({"name": "", "email": "bad-email"})

    create_response = client.post("/api/v1/certificate-jobs", json=valid_payload)
    job_id = create_response.json()["job_id"]
    status_response = client.get(f"/api/v1/certificate-jobs/{job_id}")

    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == JobStatus.COMPLETED_WITH_ERRORS
    assert body["success_count"] == 1
    assert body["failed_count"] == 1
    assert body["progress_percent"] == 100


def test_retrieves_generated_certificate(client: TestClient, valid_payload: dict) -> None:
    create_response = client.post("/api/v1/certificate-jobs", json=valid_payload)
    job_id = create_response.json()["job_id"]

    list_response = client.get(f"/api/v1/certificate-jobs/{job_id}/certificates")
    assert list_response.status_code == 200
    certificates = list_response.json()
    assert len(certificates) == 1

    download_response = client.get(certificates[0]["download_url"])
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/pdf"
    assert download_response.content.startswith(b"%PDF")


def test_pdf_generator_creates_pdf(tmp_path: Path) -> None:
    job = CertificateJob(
        id="job-1",
        title="Python APIs",
        issuer="BULK",
        issue_date=date(2026, 10, 11),
    )
    recipient = CertificateRecipient(
        id="recipient-1",
        job_id="job-1",
        name="Mira Kapoor",
        email="mira@example.com",
    )

    path = PdfCertificateGenerator(tmp_path).generate(job, recipient)

    assert path.exists()
    assert path.read_bytes().startswith(b"%PDF")


def test_individual_certificate_failure_is_recorded(tmp_path: Path) -> None:
    from bulk_certificate_generator.app import create_app

    class FailingGenerator(PdfCertificateGenerator):
        def generate(self, job: CertificateJob, recipient: CertificateRecipient) -> Path:
            if recipient.email == "fail@example.com":
                raise RuntimeError("PDF rendering failed")
            return super().generate(job, recipient)

    class ImmediateDispatcher(JobDispatcher):
        def __init__(self, app):
            self.app = app

        def dispatch(self, job_id: str, background_tasks: BackgroundTasks) -> None:
            self.app.state.processor_factory().process(job_id)

    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'failure.db'}",
        certificate_storage_dir=tmp_path / "certificates",
    )
    app = create_app(settings, dispatcher_factory=lambda app: ImmediateDispatcher(app))
    app.state.processor_factory = lambda: CertificateJobProcessor(
        app.state.session_factory,
        settings.certificate_storage_dir,
        FailingGenerator(settings.certificate_storage_dir),
    )

    payload = {
        "title": "Backend Engineering Bootcamp",
        "issuer": "BULK",
        "issue_date": "2026-10-11",
        "recipients": [
            {"name": "Aarav Mehta", "email": "aarav@example.com"},
            {"name": "Broken Recipient", "email": "fail@example.com"},
        ],
    }

    with TestClient(app) as client:
        create_response = client.post("/api/v1/certificate-jobs", json=payload)
        job_id = create_response.json()["job_id"]
        status_response = client.get(f"/api/v1/certificate-jobs/{job_id}")

    body = status_response.json()
    failed = [item for item in body["recipients"] if item["status"] == RecipientStatus.FAILED]

    assert body["status"] == JobStatus.COMPLETED_WITH_ERRORS
    assert body["success_count"] == 1
    assert body["failed_count"] == 1
    assert failed[0]["error_message"] == "PDF rendering failed"
