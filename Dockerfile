# Base image with uv package manager and Python 3.13 on Alpine Linux
FROM ghcr.io/astral-sh/uv:0.7.19-python3.13-alpine

# Environment variables for Python optimization and uv configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/uv/bin:$PATH" \
    PYTHONPATH="/app/src"

# Set working directory inside the container
WORKDIR /app

# Expose port 8000 for FastAPI application
EXPOSE 8000

# Install netcat for database connection testing
RUN apk add --no-cache netcat-openbsd

# Copy dependency files for layer caching optimization
COPY pyproject.toml ./
COPY uv.lock ./

# Install Python dependencies (production only)
RUN uv sync --no-dev

# Copy application source code and database migration files
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create non-root user for security
RUN addgroup -S lunance && adduser -S lunance -G lunance
RUN chown -R lunance:lunance /app
USER lunance

# Health check to monitor container status
HEALTHCHECK --interval=10s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

# Wait for database, run migrations, then start the application
COPY entrypoint.sh ./
ENTRYPOINT ["./entrypoint.sh"]