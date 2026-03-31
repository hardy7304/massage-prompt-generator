FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY server.py .
COPY static/ ./static/

# 平台若指定 PORT，請在 Zeabur / 主機設定中對應對外埠與此埠一致（預設 8000）
EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
