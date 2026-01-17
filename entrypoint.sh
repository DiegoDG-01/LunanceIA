#!/bin/sh
set -e

DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-3306}

echo "Esperando a que MySQL esté listo..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done
echo "MySQL está listo"

echo "Ejecutando migraciones..."
uv run alembic upgrade head

echo "Iniciando FastAPI..."
exec uv run uvicorn src.main:app --host 0.0.0.0 --port 8000