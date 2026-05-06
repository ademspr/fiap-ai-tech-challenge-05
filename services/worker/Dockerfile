FROM python:3.12-slim

WORKDIR /repo
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/repo/services/worker/src \
    PIP_NO_CACHE_DIR=1

COPY packages/contracts /repo/packages/contracts
COPY packages/platform /repo/packages/platform
COPY services/worker /repo/services/worker

WORKDIR /repo/services/worker
RUN pip install --upgrade pip && \
    pip install -e /repo/packages/contracts && \
    pip install -e /repo/packages/platform && \
    pip install -e .

CMD ["python", "-m", "hackathon_worker"]
