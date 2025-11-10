FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY ./config/gcp-keys.json /app/config/gcp-keys.json

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]