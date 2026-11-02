FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libexpat1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bathymetry/ ./bathymetry/
COPY data/ ./data/
COPY static/ ./static/

# Terrain cache
RUN mkdir -p /app/site_cache

EXPOSE 8000
CMD ["uvicorn", "bathymetry.app:app", "--host", "0.0.0.0", "--port", "8000"]
