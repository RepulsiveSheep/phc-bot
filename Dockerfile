FROM python:3.10-slim-buster

WORKDIR /app
COPY ./requirements.txt .

RUN apt-get update && \
    apt-get install --no-install-recommends -y tesseract-ocr tesseract-ocr-eng libmagic1 libpq-dev python3-dev build-essential postgresql && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get remove -y libpq-dev python3-dev build-essential postgresql && \
    apt-get purge -y && \
    apt-get clean -y && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir .

CMD ["gunicorn", "-b", "0.0.0.0:8000", "phc_bot.main:app", "--log-file", "-"]

EXPOSE 8000
