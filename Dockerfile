FROM python:3.12.12-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.lock requirements-dev.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml README.md ./
COPY src ./src
COPY migrations ./migrations
RUN pip install --no-cache-dir --no-deps -e .
RUN chmod -R a+rX /app
USER 10001:10001
CMD ["bola-lab", "serve"]

FROM base AS test
USER root
RUN pip install --no-cache-dir -r requirements-dev.lock
COPY tests ./tests
COPY compose.yaml ./compose.yaml
COPY .github/workflows/ci.yml ./.github/workflows/ci.yml
RUN chmod -R a+rX /app
USER 10001:10001

FROM base AS runtime
