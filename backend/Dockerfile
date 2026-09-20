FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# No local volume needed -- Pinecone holds all vector data remotely, so
# this container is fully stateless and safe to redeploy/restart anytime.

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
