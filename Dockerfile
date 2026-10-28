FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FT_DATA_DIR=/data

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .

RUN useradd --create-home pipeline && mkdir /data && chown pipeline /data
USER pipeline
VOLUME ["/data"]

ENTRYPOINT ["python", "-m", "jobmarket"]
CMD ["run"]
