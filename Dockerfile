FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN useradd -m appuser
COPY pyproject.toml README.md ./
COPY src/ src/
COPY config/ config/
COPY data/.gitkeep data/.gitkeep
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" "pydantic>=2.7" pydantic-settings httpx tenacity pyyaml
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["python", "-m", "uvicorn", "changeguard.api:app", "--host", "0.0.0.0", "--port", "8000"]
