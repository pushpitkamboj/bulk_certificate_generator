import logging

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from bulk_certificate_generator.models.certificate import CertificateJob, CertificateRecipient
from bulk_certificate_generator.models.enums import RecipientStatus
from bulk_certificate_generator.repositories.certificate import (
    CertificateJobRepository,
    CertificateRecipientRepository,
)
from bulk_certificate_generator.schemas.certificate import CertificateJobCreate
from bulk_certificate_generator.services.dispatcher import JobDispatcher
from bulk_certificate_generator.services.validation import RecipientValidator

logger = logging.getLogger(__name__)


class CertificateJobService:
    def __init__(
        self,
        session: Session,
        dispatcher: JobDispatcher,
        validator: RecipientValidator | None = None,
    ) -> None:
        self.session = session
        self.dispatcher = dispatcher
        self.validator = validator or RecipientValidator()
        self.job_repo = CertificateJobRepository(session)
        self.recipient_repo = CertificateRecipientRepository(session)

    def create(self, payload: CertificateJobCreate, background_tasks: BackgroundTasks) -> CertificateJob:
        job = CertificateJob(
            title=payload.title.strip(),
            issuer=payload.issuer.strip(),
            issue_date=payload.issue_date,
            total_count=len(payload.recipients),
        )
        self.job_repo.add(job)
        self.session.flush()

        recipients = []
        for item in payload.recipients:
            error_message = self.validator.validate(item)
            recipients.append(
                CertificateRecipient(
                    job_id=job.id,
                    name=item.name.strip() if item.name else item.name,
                    email=item.email.strip().lower() if item.email else item.email,
                    custom_fields=item.custom_fields,
                    status=RecipientStatus.FAILED if error_message else RecipientStatus.PENDING,
                    error_message=error_message,
                )
            )

        job.failed_count = sum(1 for recipient in recipients if recipient.status == RecipientStatus.FAILED)
        self.recipient_repo.add_all(recipients)
        self.session.commit()
        self.session.refresh(job)

        logger.info(
            "certificate job created",
            extra={
                "job_id": job.id,
                "total_count": job.total_count,
                "failed_count": job.failed_count,
            },
        )
        self.dispatcher.dispatch(job.id, background_tasks)
        return job

    def get(self, job_id: str) -> CertificateJob | None:
        return self.job_repo.get_with_recipients(job_id)
