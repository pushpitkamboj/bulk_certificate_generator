import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from bulk_certificate_generator.models.certificate import CertificateJob, CertificateRecipient
from bulk_certificate_generator.models.enums import JobStatus, RecipientStatus
from bulk_certificate_generator.repositories.certificate import (
    CertificateJobRepository,
    CertificateRecipientRepository,
)
from bulk_certificate_generator.services.pdf_generator import PdfCertificateGenerator

logger = logging.getLogger(__name__)


class CertificateJobProcessor:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        certificate_storage_dir: Path,
        generator: PdfCertificateGenerator | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.generator = generator or PdfCertificateGenerator(certificate_storage_dir)

    def process(self, job_id: str) -> None:
        with self.session_factory() as session:
            job_repo = CertificateJobRepository(session)
            recipient_repo = CertificateRecipientRepository(session)
            job = job_repo.get_with_recipients(job_id)
            if not job:
                logger.warning("certificate job not found", extra={"job_id": job_id})
                return

            try:
                job.status = JobStatus.PROCESSING
                session.commit()
                logger.info("certificate job processing started", extra={"job_id": job_id})

                for recipient in recipient_repo.list_pending_for_job(job_id):
                    self._process_recipient(session, job, recipient)

                self._finalize_job(session, job)
                logger.info(
                    "certificate job processing finished",
                    extra={
                        "job_id": job_id,
                        "status": job.status,
                        "success_count": job.success_count,
                        "failed_count": job.failed_count,
                    },
                )
            except Exception as exc:
                logger.exception("certificate job processing failed", extra={"job_id": job_id})
                session.rollback()
                job = job_repo.get(job_id)
                if job:
                    job.status = JobStatus.FAILED
                    job.failure_reason = str(exc)
                    job.completed_at = datetime.now(timezone.utc)
                    session.commit()

    def _process_recipient(
        self,
        session: Session,
        job: CertificateJob,
        recipient: CertificateRecipient,
    ) -> None:
        try:
            path = self.generator.generate(job, recipient)
            recipient.status = RecipientStatus.SUCCEEDED
            recipient.certificate_path = str(path)
            recipient.generated_at = datetime.now(timezone.utc)
            recipient.error_message = None
        except Exception as exc:
            recipient.status = RecipientStatus.FAILED
            recipient.error_message = str(exc)
            logger.warning(
                "certificate recipient generation failed",
                extra={"job_id": job.id, "recipient_id": recipient.id},
            )
        finally:
            session.commit()

    def _finalize_job(self, session: Session, job: CertificateJob) -> None:
        session.refresh(job, attribute_names=["recipients"])
        job.success_count = self._count(job.recipients, RecipientStatus.SUCCEEDED)
        job.failed_count = self._count(job.recipients, RecipientStatus.FAILED)
        job.status = JobStatus.COMPLETED if job.failed_count == 0 else JobStatus.COMPLETED_WITH_ERRORS
        job.completed_at = datetime.now(timezone.utc)
        session.commit()

    @staticmethod
    def _count(recipients: list[CertificateRecipient], status: RecipientStatus) -> int:
        return sum(1 for recipient in recipients if recipient.status == status)
