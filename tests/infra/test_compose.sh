#!/usr/bin/env bash
# Teste de fumaça da issue #1: o banco sobe healthy, só escuta em 127.0.0.1
# e preserva dados entre down/up.
# Uso: bash tests/infra/test_compose.sh   (a partir de qualquer diretório)
set -euo pipefail
cd "$(dirname "$0")/../.."

[ -f .env ] || { echo "falta .env — rode: cp .env.example .env"; exit 1; }

# As credenciais são lidas dentro do container, e não com `source .env`:
# o .env é formato do Compose, e senha com espaço ou `$` quebraria o bash.
psql_db() {
  docker compose exec -T db sh -c \
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -tAc "$1"' sh "$1"
}

# O pgAdmin roda sem login: publicar fora de 127.0.0.1 expõe o banco na rede.
assert_local_only() {
  local service=$1 port=$2 bind
  bind=$(docker compose port "$service" "$port")
  case "$bind" in
    127.0.0.1:*) ;;
    *) echo "FALHOU: $service publicado em '$bind', esperava 127.0.0.1:*"; exit 1 ;;
  esac
}

echo "1/5 subindo (espera o healthcheck)"
docker compose up -d --wait --wait-timeout 90

echo "2/5 conferindo que as portas só escutam em 127.0.0.1"
assert_local_only db 5432
assert_local_only pgadmin 80

echo "3/5 gravando marcador"
psql_db "CREATE TABLE IF NOT EXISTS _smoke (id int PRIMARY KEY);"
psql_db "INSERT INTO _smoke VALUES (1) ON CONFLICT DO NOTHING;"

echo "4/5 down + up"
docker compose down
docker compose up -d --wait --wait-timeout 90

echo "5/5 conferindo persistência"
if [ "$(psql_db "SELECT to_regclass('public._smoke') IS NOT NULL;")" != "t" ]; then
  echo "FALHOU: a tabela _smoke sumiu após down/up — o volume não persistiu"; exit 1
fi
n=$(psql_db "SELECT count(*) FROM _smoke;")
psql_db "DROP TABLE _smoke;"
[ "$n" = "1" ] || { echo "FALHOU: esperava 1 linha após down/up, veio '$n'"; exit 1; }

echo "OK"
