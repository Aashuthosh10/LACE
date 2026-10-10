FROM python:3.12.12-slim-bookworm@sha256:2986c55feb36e6cae00fa1fefb454283e4b33f35e75ff8bdd123b134130be301

LABEL org.opencontainers.image.title="LACE approved pytest runtime" \
      org.opencontainers.image.base.name="python:3.12.12-slim-bookworm" \
      org.lace.pytest-image="3.12-v1" \
      org.lace.python-version="3.12.12" \
      org.lace.pytest-version="9.0.2"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
    HOME=/tmp

COPY requirements.lock /tmp/requirements.lock
RUN python -m pip install --no-cache-dir --disable-pip-version-check \
      --require-hashes --only-binary=:all: -r /tmp/requirements.lock \
    && python -m pytest --version \
    && rm -rf /root/.cache /tmp/requirements.lock

WORKDIR /workspace
USER 65534:65534

CMD ["python", "-m", "pytest", "-q", "--disable-warnings", "--maxfail=20"]
