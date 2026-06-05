FROM python:3.11-slim

WORKDIR /app/src

COPY requirements.txt /app/

RUN pip install -r /app/requirements.txt

COPY src/ /app/src/

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]