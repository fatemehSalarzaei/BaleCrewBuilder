# Codex Runbook — Local Execution and Testing

## Repository setup

```bash
git clone https://github.com/fatemehSalarzaei/BaleCrewBuilder.git
cd BaleCrewBuilder

python3.12 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
cp .env.example .env
```

## Start local services

```bash
docker-compose up -d
```

Services:

```text
PostgreSQL: localhost:5432
Redis:      localhost:6379
```

## Apply migrations

```bash
alembic upgrade head
```

## Run API

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000/docs
```

## Run tests

```bash
pytest
pytest -q
pytest -x
```

Focused tests:

```bash
pytest tests/test_blueprint_validation.py -q
pytest tests/test_generation_gate.py -q
pytest tests/test_e2e_sample_generation.py -q
```

After Phase 10 is implemented:

```bash
pytest tests/test_artifact_download.py -q
pytest tests/test_generation_gate.py -q
pytest tests/test_e2e_sample_generation.py -q
pytest
```

## Manual generation workflow

Create a project:

```bash
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Sample Bale Platform", "description": "Sample project for artifact download test."}'
```

Create document manually:

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/documents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sample Project Document",
    "content": "# Overview\n\n## User Flow\n\n## Admin Flow"
  }'
```

Submit document for review:

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/documents/{DOCUMENT_ID}/submit-review
```

Approve document:

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/document/approve \
  -H "Content-Type: application/json" \
  -d '{"reviewer_name": "Codex Reviewer"}'
```

Generate Blueprint:

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/blueprint/generate
```

Validate Blueprint:

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/blueprint/validate
```

Generate implementation:

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/generate
```

After Phase 10:

```bash
curl -L -o generated-project.zip http://localhost:8000/projects/{PROJECT_ID}/download
```
