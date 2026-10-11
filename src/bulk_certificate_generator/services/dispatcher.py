from abc import ABC, abstractmethod
from collections.abc import Callable

from fastapi import BackgroundTasks

from bulk_certificate_generator.services.processor import CertificateJobProcessor


class JobDispatcher(ABC):
    @abstractmethod
    def dispatch(self, job_id: str, background_tasks: BackgroundTasks) -> None:
        raise NotImplementedError


class LocalBackgroundDispatcher(JobDispatcher):
    def __init__(self, processor_factory: Callable[[], CertificateJobProcessor]) -> None:
        self.processor_factory = processor_factory

    def dispatch(self, job_id: str, background_tasks: BackgroundTasks) -> None:
        background_tasks.add_task(self._run, job_id)

    def _run(self, job_id: str) -> None:
        self.processor_factory().process(job_id)
