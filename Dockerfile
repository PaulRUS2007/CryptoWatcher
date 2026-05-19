FROM python:3.12-slim

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
WORKDIR /app

# RUN (python /app/migrations/0001.py || true) && (python /app/migrations/0002.py || true)

CMD ["python", "/app/bot.py"]