# Stage 1: Build the frontend (Vite React app)
FROM node:20 AS frontend-builder

WORKDIR /app/frontend

# Copy frontend dependency files
COPY frontend/package.json frontend/package-lock.json* ./

# Install dependencies
RUN npm install

# Copy frontend source code
COPY frontend/ ./

# Build the frontend (outputs to /app/frontend/dist)
RUN npm run build


# Stage 2: Build the backend and serve the application
FROM python:3.9-slim

WORKDIR /app

# System dependencies for cryptography, postgres etc.
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install uvicorn

# Copy backend source code
COPY ./app ./app
COPY ./start.sh ./start.sh

# Ensure start.sh is executable
RUN chmod +x ./start.sh

# Copy built frontend from Stage 1 into the backend directory
# We will mount this directory in FastAPI
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose the port the app runs on
EXPOSE 8000

# Run the start script (runs migrations and starts uvicorn)
CMD ["./start.sh"]
