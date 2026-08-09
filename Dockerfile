FROM python:3.12-slim

WORKDIR /app
COPY gates/ ./gates/
COPY server.py ./

ENV PORT=8080 PYTHONUNBUFFERED=1
USER nobody
EXPOSE 8080
CMD ["python", "server.py"]
