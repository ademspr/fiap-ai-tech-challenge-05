FROM python:3.12-slim

WORKDIR /repo
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/repo/services/api/src \
    PIP_NO_CACHE_DIR=1

COPY packages/contracts /repo/packages/contracts
COPY packages/platform /repo/packages/platform
COPY services/api /repo/services/api

WORKDIR /repo/services/api
RUN pip install --upgrade pip && \
    pip install -e /repo/packages/contracts && \
    pip install -e /repo/packages/platform && \
    pip install -e .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn hackathon_api.main:app --host 0.0.0.0 --port 8000"]
