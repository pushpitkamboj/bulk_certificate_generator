# Bulk Certificate Generator Backend

FastAPI backend for creating bulk certificate generation jobs, tracking progress, and downloading generated PDF certificates.

## Tech Stack

- Python 3.14
- FastAPI and Pydantic v2
- SQLAlchemy with SQLite
- ReportLab for PDF generation
- pytest and HTTPX/TestClient
- Docker and `uv`

## Local Setup

```bash
uv venv
source .venv/bin/activate
uv sync
cp .env.example .env
```

Run the API:

```bash
uv run uvicorn bulk_certificate_generator.main:app --reload
```

The app will be available at `http://localhost:8000`.

## Run Tests

```bash
uv run pytest
```

## API Usage

Create a certificate generation job:

```bash
curl -X POST http://localhost:8000/api/v1/certificate-jobs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Backend Engineering Bootcamp",
    "issuer": "BULK",
    "issue_date": "2026-10-11",
    "recipients": [
      {
        "name": "Aarav Mehta",
        "email": "aarav@example.com",
        "custom_fields": {"grade": "A"}
      },
      {
        "name": "Mira Kapoor",
        "email": "mira@example.com",
        "custom_fields": {"grade": "A+"}
      }
    ]
  }'
```

Check job status:

```bash
curl http://localhost:8000/api/v1/certificate-jobs/{job_id}
```

List generated certificates:

```bash
curl http://localhost:8000/api/v1/certificate-jobs/{job_id}/certificates
```

Download a certificate:

```bash
curl -L http://localhost:8000/api/v1/certificate-jobs/{job_id}/certificates/{recipient_id} \
  -o certificate.pdf
```

Health check:

```bash
curl http://localhost:8000/health
```

## Docker

Build the image:

```bash
docker build -t bulk-certificate-generator .
```

Run the container:

```bash
docker run --rm -p 8000:8000 \
  -v "$(pwd)/data:/app/data" \
  bulk-certificate-generator
```

## Configuration

Environment variables use the `CERTGEN_` prefix.

| Variable | Default |
| --- | --- |
| `CERTGEN_DATABASE_URL` | `sqlite:///./data/app.db` |
| `CERTGEN_CERTIFICATE_STORAGE_DIR` | `./data/certificates` |
| `CERTGEN_LOG_LEVEL` | `INFO` |
| `CERTGEN_HOST` | `0.0.0.0` |
| `CERTGEN_PORT` | `8000` |
| `CERTGEN_RELOAD` | `false` |

## Design Decisions

- Jobs are accepted in bulk and processed through a dispatcher abstraction. The current dispatcher uses FastAPI background tasks, while the processor can be moved behind Celery, RQ, or another queue without changing route contracts.
- SQLite is used because the assignment asks for a relational database and the workload fits a local submission. SQLAlchemy keeps the code portable to PostgreSQL or MySQL later.
- Generated PDFs are stored on disk and referenced from the database. This keeps the DB small and makes downloads simple.
- Recipient validation is partial. Invalid recipients are stored as failed rows, and valid recipients in the same job still generate certificates.
- The app creates tables at startup for easy local review. Alembic is included for migration readiness if the schema evolves.

## Logging and Production Reliability

- The app logs job creation, processing start/completion, recipient-level generation failures, missing jobs, and job-level crashes through Python logging. Configure verbosity with `CERTGEN_LOG_LEVEL`.
- The current dispatcher uses FastAPI background tasks to keep the assignment lightweight and easy to run locally.
- Production deployments should replace the local dispatcher with a durable queue such as Celery/RQ with Redis, SQS, RabbitMQ, or a similar broker.
- Transient failures such as network or storage hiccups should use bounded retries with exponential backoff and jitter.
- Permanently failed jobs should move to a dead-letter queue for inspection, alerting, and safe replay.
- Certificate generation should remain idempotent by job ID and recipient ID so retries do not create duplicate logical certificates.

## Project Layout

```text
src/bulk_certificate_generator/
  api/              HTTP routes
  core/             settings
  db/               engine/session setup
  models/           SQLAlchemy models and enums
  repositories/     database access
  schemas/          Pydantic request/response models
  services/         validation, dispatching, processing, PDF generation
```
