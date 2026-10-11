from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Bulk Certificate Generator"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/app.db"
    certificate_storage_dir: Path = Path("data/certificates")
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CERTGEN_",
        extra="ignore",
    )

    def ensure_directories(self) -> None:
        if self.database_url.startswith("sqlite:///"):
            db_path = Path(self.database_url.removeprefix("sqlite:///"))
            if db_path.parent != Path("."):
                db_path.parent.mkdir(parents=True, exist_ok=True)
        self.certificate_storage_dir.mkdir(parents=True, exist_ok=True)
