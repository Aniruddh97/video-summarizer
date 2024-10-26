FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN pip install -r /app/requirements.txt

ENTRYPOINT ["python", "main.py"]
