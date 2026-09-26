#!/usr/bin/env bash
# Aplica sql/NNN_*.sql em ordem, uma vez cada, registrando em schema_migrations.
# Cada arquivo roda numa transação: se falhar, nada dele fica no banco.
# Uso: bash scripts/migrate.sh   (ou make migrate)
set -euo pipefail
cd "$(dirname "$0")/.."

psql_db() {
  docker compose exec -T db sh -c \
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q "$@"' sh "$@"
}

psql_db -c "SET client_min_messages = warning;
CREATE TABLE IF NOT EXISTS schema_migrations (
  arquivo     text PRIMARY KEY,
  aplicado_em timestamptz NOT NULL DEFAULT now()
);"

for f in sql/[0-9][0-9][0-9]_*.sql; do
  n=$(basename "$f")
  [ -n "$(psql_db -tAc "SELECT 1 FROM schema_migrations WHERE arquivo = '$n'")" ] && continue
  echo "→ aplicando $n"
  { cat "$f"; echo; echo "INSERT INTO schema_migrations (arquivo) VALUES ('$n');"; } \
    | psql_db -1 -f -
done
echo "migrações em dia"
