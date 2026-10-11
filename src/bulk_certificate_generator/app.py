from collections.abc import Callable

from fastapi import FastAPI

from bulk_certificate_generator.api.routes import router
from bulk_certificate_generator.core.config import Settings
from bulk_certificate_generator.core.logging import configure_logging
from bulk_certificate_generator.db.base import Base
from bulk_certificate_generator.db.session import build_engine, build_session_factory
from bulk_certificate_generator.models import certificate  # noqa: F401
from bulk_certificate_generator.services.dispatcher import JobDispatcher, LocalBackgroundDispatcher
from bulk_certificate_generator.services.processor import CertificateJobProcessor


def create_app(
    settings: Settings | None = None,
    dispatcher_factory: Callable[[FastAPI], JobDispatcher] | None = None,
) -> FastAPI:
    settings = settings or Settings()
    settings.ensure_directories()
    configure_logging(settings.log_level)

    engine = build_engine(settings.database_url)
    session_factory = build_session_factory(engine)
    Base.metadata.create_all(bind=engine)

    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory

    def processor_factory() -> CertificateJobProcessor:
        return CertificateJobProcessor(session_factory, settings.certificate_storage_dir)

    app.state.processor_factory = processor_factory
    app.state.dispatcher = (
        dispatcher_factory(app)
        if dispatcher_factory
        else LocalBackgroundDispatcher(processor_factory)
    )

    app.include_router(router)
    return app
