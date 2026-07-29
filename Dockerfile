# ---- Stage 1: Compile Rust financial core ----
FROM python:3.13-alpine AS rust-builder

RUN apk add --no-cache curl gcc musl-dev patchelf libgcc

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /build/fincore

# Fija el directorio de build: la variable de entorno gana sobre cualquier
# build.target-dir de un .cargo/config.toml, así que un override local del
# desarrollador no puede desviar el wheel fuera de la ruta que espera el COPY.
ENV CARGO_TARGET_DIR=/build/fincore/target

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir maturin[patchelf]

COPY fincore/ .

RUN --mount=type=cache,target=/build/fincore/target,id=lunance-cargo-cache \
    maturin build --release --strip --interpreter python3.13 && \
    mkdir -p /build/fincore/dist && \
    cp /build/fincore/target/wheels/*.whl /build/fincore/dist/


# ---- Stage 2: Final production image ----
FROM python:3.13-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/src" \
    UV_COMPILE_BYTECODE=1

RUN apk update && apk upgrade --no-cache && \
    apk add --no-cache netcat-openbsd libgcc curl && \
    curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh && \
    pip install --no-cache-dir --upgrade pip && \
    addgroup -S lunance && adduser -S lunance -G lunance

WORKDIR /app

COPY --chown=lunance:lunance pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY --chown=lunance:lunance --from=rust-builder /build/fincore/dist/*.whl /tmp/
RUN uv pip install /tmp/*.whl && rm /tmp/*.whl && \
    chown -R lunance:lunance /app/.venv

COPY --chown=lunance:lunance src/ ./src/
COPY --chown=lunance:lunance alembic/ ./alembic/
COPY --chown=lunance:lunance alembic.ini ./

COPY --chown=lunance:lunance entrypoint.sh ./
RUN chmod +x entrypoint.sh

USER lunance

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
