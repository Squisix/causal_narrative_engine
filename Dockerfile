FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY cne_core/ cne_core/
COPY api/ api/
COPY adapters/ adapters/
COPY persistence/ persistence/
COPY web/ web/
COPY cli/ cli/
COPY migrations/ migrations/
COPY alembic.ini .

RUN pip install --no-cache-dir -e ".[all]"

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
