# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

ENV POETRY_VERSION=2.5.1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock README.md ./
COPY src ./src

RUN poetry install --only main --all-extras --no-root \
    && poetry install --only main --all-extras

FROM python:3.12-slim AS runtime

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --uid 10001 iot

COPY --from=builder /app/.venv /app/.venv
COPY projects ./projects
COPY docs ./docs

RUN mkdir -p /app/data \
    && chown -R iot:iot /app

USER iot

ENTRYPOINT ["iot-weather"]
CMD ["--simulation", "--samples", "1"]
