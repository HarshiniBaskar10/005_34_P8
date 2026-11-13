# Build React UI, then serve UI + Flask API from one gunicorn process (SQLite lock needs a single worker)
FROM node:20-alpine AS ui
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend
COPY --from=ui /ui/dist ./frontend/dist
RUN mkdir -p /data
ENV LOAN_DB=/data/loan.db PORT=8000
WORKDIR /app/backend
CMD gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT wsgi:app
