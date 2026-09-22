FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WORKER_DATABASE_PATH=/data/worker.db \
    WORKER_ARTIFACT_ROOT=/data/artifacts

RUN addgroup --system worker \
    && adduser --system --ingroup worker --home /worker worker \
    && mkdir -p /worker /data/artifacts \
    && chown -R worker:worker /worker /data

WORKDIR /worker
COPY worker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt
COPY --chown=worker:worker worker ./worker

USER worker
EXPOSE 8010
VOLUME ["/data"]
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/v1/health', timeout=3).read()"]

CMD ["python", "-m", "uvicorn", "worker.app.main:app", "--host", "0.0.0.0", "--port", "8010", "--proxy-headers", "--forwarded-allow-ips", "*"]
