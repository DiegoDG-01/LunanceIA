#!/bin/sh
set -e

echo "Esperando a que MySQL esté listo..."
while ! nc -z db 3306; do
  sleep 1
done
echo "MySQL está listo"

echo "Ejecutando migraciones..."
uv run alembic upgrade head

echo "Iniciando FastAPI..."
exec uv run uvicorn src.main:app --host 0.0.0.0 --port 8000