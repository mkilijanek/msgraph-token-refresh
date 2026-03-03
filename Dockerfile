FROM python:3.12-alpine3.20

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN apk upgrade --no-cache \
  && apk add --no-cache libcurl \
  && apk add --no-cache --virtual .build-deps curl-dev gcc musl-dev \
  && pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r /app/requirements.txt \
  && apk del .build-deps

COPY token_refresher.py /app/token_refresher.py

RUN adduser -D -u 10001 appuser \
  && chown -R appuser:appuser /app

USER 10001

CMD ["python", "/app/token_refresher.py"]
