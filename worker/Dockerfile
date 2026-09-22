FROM python:3.11-slim

WORKDIR /worker
COPY worker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY worker ./worker

ENV PYTHONPATH=/worker
EXPOSE 8010
CMD ["python", "-m", "uvicorn", "worker.app.main:app", "--host", "0.0.0.0", "--port", "8010"]
