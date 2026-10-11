from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from bulk_certificate_generator.db.dependencies import get_db_session
from bulk_certificate_generator.models.enums import RecipientStatus
from bulk_certificate_generator.repositories.certificate import CertificateRecipientRepository
from bulk_certificate_generator.schemas.certificate import (
    CertificateJobCreate,
    CertificateMetadata,
    JobCreatedResponse,
    JobStatusResponse,
    RecipientResult,
)
from bulk_certificate_generator.services.jobs import CertificateJobService

router = APIRouter()
api_router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@api_router.post(
    "/certificate-jobs",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_certificate_job(
    payload: CertificateJobCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    session: Session = Depends(get_db_session),
) -> JobCreatedResponse:
    service = CertificateJobService(session, request.app.state.dispatcher)
    job = service.create(payload, background_tasks)
    return JobCreatedResponse(
        job_id=job.id,
        status=job.status,
        total_count=job.total_count,
        failed_count=job.failed_count,
    )


@api_router.get("/certificate-jobs/{job_id}", response_model=JobStatusResponse)
def get_certificate_job(
    job_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
) -> JobStatusResponse:
    service = CertificateJobService(session, request.app.state.dispatcher)
    job = service.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return _job_response(job)


@api_router.get("/certificate-jobs/{job_id}/certificates", response_model=list[CertificateMetadata])
def list_certificates(
    job_id: str,
    session: Session = Depends(get_db_session),
) -> list[CertificateMetadata]:
    recipient_repo = CertificateRecipientRepository(session)
    certificates = []
    for recipient in recipient_repo.get_successful(job_id):
        certificates.append(
            CertificateMetadata(
                recipient_id=recipient.id,
                name=recipient.name or "",
                email=recipient.email or "",
                download_url=f"/api/v1/certificate-jobs/{job_id}/certificates/{recipient.id}",
            )
        )
    return certificates


@api_router.get("/certificate-jobs/{job_id}/certificates/{recipient_id}")
def download_certificate(
    job_id: str,
    recipient_id: str,
    session: Session = Depends(get_db_session),
) -> FileResponse:
    recipient_repo = CertificateRecipientRepository(session)
    recipient = recipient_repo.get_for_job(job_id, recipient_id)
    if not recipient or recipient.status != RecipientStatus.SUCCEEDED or not recipient.certificate_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found.")

    path = Path(recipient.certificate_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate file not found.")

    filename = f"{recipient.name or recipient.id}-certificate.pdf"
    return FileResponse(path, media_type="application/pdf", filename=filename)


def _job_response(job) -> JobStatusResponse:
    return JobStatusResponse(
        id=job.id,
        title=job.title,
        issuer=job.issuer,
        issue_date=job.issue_date,
        status=job.status,
        total_count=job.total_count,
        success_count=job.success_count,
        failed_count=job.failed_count,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        failure_reason=job.failure_reason,
        recipients=[
            RecipientResult(
                id=recipient.id,
                name=recipient.name,
                email=recipient.email,
                status=recipient.status,
                error_message=recipient.error_message,
                certificate_url=(
                    f"/api/v1/certificate-jobs/{job.id}/certificates/{recipient.id}"
                    if recipient.status == RecipientStatus.SUCCEEDED
                    else None
                ),
            )
            for recipient in job.recipients
        ],
    )


router.include_router(api_router)
