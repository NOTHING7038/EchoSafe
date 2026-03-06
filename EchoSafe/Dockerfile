FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy frontend
COPY frontend/ ./frontend/

# Copy AI model
COPY ai_model/ ./ai_model/

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["python", "backend/app.py"]
