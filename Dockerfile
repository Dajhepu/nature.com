# Build stage - Frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Runtime stage - Backend
FROM python:3.11-slim
WORKDIR /app

# Python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend from previous stage
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Copy wsgi and migrations
COPY wsgi.py ./backend/
COPY backend/migrations ./backend/migrations

# Copy and set up the entrypoint script
COPY entrypoint.sh ./backend/
RUN chmod +x ./backend/entrypoint.sh

WORKDIR /app/backend

# Set Flask environment variables
ENV FLASK_APP=wsgi:app
ENV PYTHONPATH=/app

CMD ["./entrypoint.sh"]
