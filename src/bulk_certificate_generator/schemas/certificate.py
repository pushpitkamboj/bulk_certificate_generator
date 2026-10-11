from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field

from bulk_certificate_generator.models.enums import JobStatus, RecipientStatus


class RecipientInput(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class CertificateJobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    issuer: str = Field(min_length=1, max_length=200)
    issue_date: date
    recipients: list[RecipientInput] = Field(min_length=1, max_length=5000)


class JobCreatedResponse(BaseModel):
    job_id: str
    status: JobStatus
    total_count: int
    failed_count: int


class RecipientResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str | None
    email: str | None
    status: RecipientStatus
    error_message: str | None
    certificate_url: str | None = None


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    issuer: str
    issue_date: date
    status: JobStatus
    total_count: int
    success_count: int
    failed_count: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    failure_reason: str | None
    recipients: list[RecipientResult]

    @computed_field
    @property
    def progress_percent(self) -> float:
        if self.total_count == 0:
            return 0.0
        processed = self.success_count + self.failed_count
        return round((processed / self.total_count) * 100, 2)


class CertificateMetadata(BaseModel):
    recipient_id: str
    name: str
    email: str
    download_url: str
