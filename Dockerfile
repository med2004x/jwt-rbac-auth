FROM python:3.12-slim

WORKDIR /service

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/service/src

COPY src/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY src /service/src
COPY scripts /service/scripts
COPY tests /service/tests

CMD ["sh", "-c", "python scripts/apply_migrations.py && uvicorn app.main:build_application --factory --host 0.0.0.0 --port 8080"]
