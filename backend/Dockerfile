# Python 3.13.16 is the exact interpreter the classifier artifact was trained on.
FROM python:3.13.16-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    HOST=0.0.0.0

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin tutor

WORKDIR /srv/backend

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# models/ is copied byte-for-byte: its SHA-256 hashes are verified at startup.
COPY --chown=tutor:tutor app ./app
COPY --chown=tutor:tutor models ./models

USER tutor
EXPOSE 8001

# Passes only if /health reports "status": "ok". A degraded start (model failed
# verification) still exits 0, so this is what marks the container unhealthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import json,sys,urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=4); sys.exit(0 if json.load(r).get('status')=='ok' else 1)"]

CMD ["python", "-m", "app"]


FROM runtime AS test

USER root
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY --chown=tutor:tutor tests ./tests
COPY --chown=tutor:tutor scripts ./scripts
# only the README (a test checks it records the one-revision rule), plus the one result file the
# blind rating sheet is built from (tests/test_blind_sheet.py); the rest of benchmarks/llm/ stays
# out of the image
COPY --chown=tutor:tutor benchmarks/llm/README.md ./benchmarks/llm/README.md
COPY --chown=tutor:tutor benchmarks/llm/llama3.2_3b_2026-10-15_np110_r2.json ./benchmarks/llm/llama3.2_3b_2026-10-15_np110_r2.json
# Tests build their own temp copies; the image's models/ is never modified.
RUN chown tutor:tutor /srv/backend
USER tutor

# No server runs in the test target, so the inherited health check does not apply.
HEALTHCHECK NONE
CMD ["python", "-m", "pytest"]
