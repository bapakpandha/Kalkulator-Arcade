FROM python:3.10.18-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_ENV=production

CMD ["gunicorn", "-t", "60", "--keep-alive", "2", "-b", "0.0.0.0:8000", "app:app", "--access-logfile", "-", "--error-logfile", "-", "log-level=info"]
