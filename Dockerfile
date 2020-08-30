FROM python:3.8-slim-buster

WORKDIR /app
COPY requirements.txt .

RUN apt-get update && \
    apt-get install --no-install-recommends -y tesseract-ocr tesseract-ocr-eng libmagic1 libpq-dev python3-dev build-essential postgresql && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get remove -y libpq-dev python3-dev build-essential postgresql && \
    apt-get purge -y && \
    apt-get clean -y && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

COPY . .

RUN adduser --disabled-password --gecos "" user && \
    chown -R user:user /app && \
    chmod -R 755 /app
USER user

ENTRYPOINT ["gunicorn", "-b", "0.0.0.0:8000", "main:app", "--log-file", "-"]

EXPOSE 8000
