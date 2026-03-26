# GlucoSense - Type 1 Diabetes Clinical Support (FastAPI + React)
# Build: docker build -t glucosense .
# Requires: data/SmartSensor_DiabetesMonitoring.csv at repo root (Glucosense/Glucosense)

# --- Frontend (Vite) — embed URLs must match your public meal app + API ports ---
FROM node:20-alpine AS frontend-builder
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_MEAL_PLAN_URL=http://localhost:8082
ARG VITE_MEAL_PLAN_API_URL=http://localhost:8081
ARG VITE_MEAL_PLAN_EMBED_SECRET=change-me-in-production
ENV VITE_MEAL_PLAN_URL=$VITE_MEAL_PLAN_URL
ENV VITE_MEAL_PLAN_API_URL=$VITE_MEAL_PLAN_API_URL
ENV VITE_MEAL_PLAN_EMBED_SECRET=$VITE_MEAL_PLAN_EMBED_SECRET
RUN npm run build

# --- Python dependencies ---
FROM python:3.11-slim AS pybuilder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend/src

COPY --from=pybuilder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY app.py .
COPY backend/ backend/
COPY config/ config/
COPY data/SmartSensor_DiabetesMonitoring.csv ./data/

RUN mkdir -p outputs/best_model outputs/audit

COPY --from=frontend-builder /build/dist frontend/dist/

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
