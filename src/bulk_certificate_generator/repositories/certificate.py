from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from bulk_certificate_generator.models.certificate import CertificateJob, CertificateRecipient
from bulk_certificate_generator.models.enums import RecipientStatus


class CertificateJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, job: CertificateJob) -> CertificateJob:
        self.session.add(job)
        return job

    def get(self, job_id: str) -> CertificateJob | None:
        return self.session.get(CertificateJob, job_id)

    def get_with_recipients(self, job_id: str) -> CertificateJob | None:
        statement = (
            select(CertificateJob)
            .options(selectinload(CertificateJob.recipients))
            .where(CertificateJob.id == job_id)
        )
        return self.session.scalars(statement).first()


class CertificateRecipientRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_all(self, recipients: list[CertificateRecipient]) -> None:
        self.session.add_all(recipients)

    def list_pending_for_job(self, job_id: str) -> list[CertificateRecipient]:
        statement = select(CertificateRecipient).where(
            CertificateRecipient.job_id == job_id,
            CertificateRecipient.status == RecipientStatus.PENDING,
        )
        return list(self.session.scalars(statement).all())

    def get_successful(self, job_id: str) -> list[CertificateRecipient]:
        statement = select(CertificateRecipient).where(
            CertificateRecipient.job_id == job_id,
            CertificateRecipient.status == RecipientStatus.SUCCEEDED,
        )
        return list(self.session.scalars(statement).all())

    def get_for_job(self, job_id: str, recipient_id: str) -> CertificateRecipient | None:
        statement = select(CertificateRecipient).where(
            CertificateRecipient.job_id == job_id,
            CertificateRecipient.id == recipient_id,
        )
        return self.session.scalars(statement).first()
