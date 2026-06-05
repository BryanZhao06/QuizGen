FROM python:3.11-slim

WORKDIR /app/src

COPY requirements.txt .

RUN pip install -r /app/requirements.txt

COPY src/ ./src/

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]