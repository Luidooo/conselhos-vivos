#!/usr/bin/env bash
# Teste de fumaça da issue #1: o banco sobe healthy e preserva dados entre down/up.
# Uso: bash tests/infra/test_compose.sh   (a partir de qualquer diretório)
set -euo pipefail
cd "$(dirname "$0")/../.."

[ -f .env ] || { echo "falta .env — rode: cp .env.example .env"; exit 1; }
set -a; . ./.env; set +a

psql_db() {
  docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -tAc "$1"
}

echo "1/4 subindo (espera o healthcheck)"
docker compose up -d --wait --wait-timeout 90

echo "2/4 gravando marcador"
psql_db "CREATE TABLE IF NOT EXISTS _smoke (id int PRIMARY KEY);"
psql_db "INSERT INTO _smoke VALUES (1) ON CONFLICT DO NOTHING;"

echo "3/4 down + up"
docker compose down
docker compose up -d --wait --wait-timeout 90

echo "4/4 conferindo persistência"
n=$(psql_db "SELECT count(*) FROM _smoke;")
psql_db "DROP TABLE _smoke;"
[ "$n" = "1" ] || { echo "FALHOU: esperava 1 linha após down/up, veio '$n'"; exit 1; }

echo "OK"
