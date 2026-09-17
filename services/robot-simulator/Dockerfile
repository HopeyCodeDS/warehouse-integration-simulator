FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY worker.py simulation.py /app/
# Running the script directly as a background worker
CMD ["python", "worker.py"]