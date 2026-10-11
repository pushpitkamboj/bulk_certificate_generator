import uvicorn

from bulk_certificate_generator.app import create_app
from bulk_certificate_generator.core.config import Settings

app = create_app()


def run() -> None:
    settings = Settings()
    uvicorn.run(
        "bulk_certificate_generator.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
