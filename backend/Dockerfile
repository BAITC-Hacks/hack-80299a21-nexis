FROM python:3.14.7-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    NEXIS_DB_PATH=/data/nexis.sqlite3 \
    NEXIS_KNOWLEDGE_DB_PATH=/data/knowledge.sqlite3 \
    NEXIS_CATALOG_DB_PATH=/data/catalog.sqlite3 \
    TESSERACT_CMD=/usr/bin/tesseract

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus tesseract-ocr-kaz \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements-lock.txt /app/backend/requirements-lock.txt
RUN python -m pip install --no-cache-dir -r /app/backend/requirements-lock.txt

RUN groupadd --gid 10001 nexis \
    && useradd --uid 10001 --gid nexis --no-create-home --shell /usr/sbin/nologin nexis \
    && mkdir -p /data \
    && chown nexis:nexis /data

COPY --chown=nexis:nexis backend /app/backend
COPY --chown=nexis:nexis database/knowledge /app/database/knowledge

USER nexis
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).read()"
CMD ["python", "backend/main.py"]
