# Locked production derivative of the exact Harvey LAB sandbox.
# The upstream Dockerfile remains untouched under research/harvey-recovery.
FROM docker.io/library/python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36

LABEL org.opencontainers.image.source="https://github.com/blobfishai/legal-agent-simulation"
LABEL org.opencontainers.image.description="Reproducible Harvey LAB-compatible document sandbox"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# The base image was built from this Debian snapshot. Reusing it makes apt
# dependency resolution stable instead of following mutable trixie mirrors.
COPY debian.sources /etc/apt/sources.list.d/debian.sources
RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        curl \
        file \
        findutils \
        gawk \
        gcc \
        g++ \
        git \
        grep \
        procps \
        jq \
        libreoffice \
        nodejs \
        npm \
        pandoc \
        poppler-utils \
        ripgrep \
        sed \
        tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN python -m pip install --no-cache-dir --require-hashes --only-binary=:all: \
        -r /tmp/requirements.lock \
    && rm /tmp/requirements.lock

COPY package.json package-lock.json /opt/harvey-js/
RUN npm ci --prefix /opt/harvey-js --omit=dev --ignore-scripts --no-audit --no-fund \
    && npm cache clean --force
ENV NODE_PATH=/opt/harvey-js/node_modules

COPY parsers/parse_doc.py /usr/local/bin/parse-doc
RUN chmod +x /usr/local/bin/parse-doc \
    && mkdir -p /workspace/documents /workspace/output

WORKDIR /workspace
CMD ["sleep", "infinity"]
