# Multi-stage build für kleinere Image-Größe
FROM python:3.11-slim as builder

# System-Dependencies installieren
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies installieren
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime Stage
FROM python:3.11-slim

# Non-root User erstellen
RUN groupadd -r dtsu666 && useradd -r -g dtsu666 dtsu666

# System-Dependencies für Runtime
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Python packages vom Builder kopieren
COPY --from=builder /root/.local /home/dtsu666/.local

# Arbeitsverzeichnis erstellen
WORKDIR /app

# Application Code kopieren
COPY dtsu666_fullFeature.py .

# Ownership ändern
RUN chown -R dtsu666:dtsu666 /app

# User wechseln
USER dtsu666

# PATH für lokale Python packages
ENV PATH=/home/dtsu666/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import paho.mqtt.client as mqtt; import sys; sys.exit(0)" || exit 1

# Startkommando
CMD ["python", "dtsu666_fullFeature.py"]