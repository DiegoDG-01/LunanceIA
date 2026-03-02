# ---- Stage 1: Compile Rust financial core ----
FROM python:3.13-alpine AS rust-builder

RUN apk add --no-cache curl gcc musl-dev
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN pip install maturin[patchelf]

COPY fincore/ /build/fincore/
RUN cd /build/fincore && rm -rf target/wheels && maturin build --release

# ---- Stage 2: Final production image ----
FROM ghcr.io/astral-sh/uv:python3.13-alpine

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

# Install pre-compiled fincore wheel from builder stage
COPY --from=rust-builder /build/fincore/target/wheels/*.whl /tmp/
RUN uv pip install /tmp/*.whl && rm /tmp/*.whl

# Copy application source code and database migration files
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create non-root user for security
RUN addgroup -S lunance && adduser -S lunance -G lunance
RUN chown -R lunance:lunance /app
USER lunance

# Wait for database, run migrations, then start the application
COPY entrypoint.sh ./
ENTRYPOINT ["./entrypoint.sh"]
