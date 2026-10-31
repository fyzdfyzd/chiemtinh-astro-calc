# astro-calc: dịch vụ tính vị trí (Kerykeion + Swiss Ephemeris), AGPL-3.0.
# Dựng từ thư mục astro-engine: docker build -f calc-service/Dockerfile -t astro-calc .
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    KERYKEION_BACKEND=swisseph ASTRO_CALC_EPHE_DIR=/app/ephe
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY services/astro-calc/ ./calc-service/
RUN pip install --no-cache-dir "./calc-service[swiss]" \
 && apt-get purge -y build-essential && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
COPY _nguon/astro-engine/data/ephe ./ephe
RUN useradd --create-home --uid 10002 calc
USER calc
EXPOSE 8027
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8027/v1/health')"
CMD ["astro-calc", "--host", "0.0.0.0", "--port", "8027"]
