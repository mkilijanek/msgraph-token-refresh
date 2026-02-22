FROM python:3.12-alpine

RUN pip install --no-cache-dir msal requests

WORKDIR /app
COPY token_refresher.py /app/token_refresher.py

# uruchamiaj jako nie-root (sensownie)
RUN adduser -D -u 10001 appuser && chown -R appuser:appuser /app
USER 10001

CMD ["python", "/app/token_refresher.py"]
