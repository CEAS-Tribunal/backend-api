# Django API image. The entrypoint migrates, then runs the command.
# Default command is Gunicorn. Local Compose overrides it with runserver.
#
#   docker build -t tribunal-api .
#   docker run --rm -p 8000:8000 --env-file .env tribunal-api

FROM python:3.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /bin/

WORKDIR /app

# Venv lives outside /app so a source bind mount does not hide installed packages.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN useradd --create-home --uid 1000 --shell /bin/sh app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=app:app . .
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh \
    && chmod +x /docker-entrypoint.sh \
    && mkdir -p /app/media /app/static \
    && chown -R app:app /app /opt/venv

USER app

# WhiteNoise manifest. Env vars here are build-only and are not kept in the image.
RUN DEBUG=0 \
    CORS_ORIGINS=http://localhost \
    SECRET_KEY=collectstatic-build-only \
    ALLOWED_HOSTS=localhost,127.0.0.1 \
    python manage.py collectstatic --noinput

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gunicorn", "backendapi.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
