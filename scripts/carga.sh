#!/usr/bin/env bash
# Carrega a planilha da pesquisadora no OLTP (#3) e atualiza o relatório de carga.
# Idempotente: rodar de novo não duplica ato nem classificação, e gera o mesmo relatório.
# Pré-requisito: banco no ar e migrado (make migrate). Uso: bash scripts/carga.sh (ou make carga)
set -euo pipefail
cd "$(dirname "$0")/.."

carga() { docker compose --progress quiet run --rm -T carga "$@"; }
psql_db() {
  docker compose exec -T db sh -c 'psql -X -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -f -'
}

# O SQL vai para um arquivo antes do psql: se a leitura da planilha falhar no meio,
# nada chega ao banco (num pipe, o psql executaria o começo).
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
carga sql > "$tmp/carga.sql"
psql_db < "$tmp/carga.sql"

carga relatorio > "$tmp/relatorio.md"
mkdir -p docs/carga
mv "$tmp/relatorio.md" docs/carga/relatorio-planilha.md
mkdir -p data/interim/planilha
carga csv > "$tmp/atos.csv"
mv "$tmp/atos.csv" data/interim/planilha/atos.csv
echo "→ relatório em docs/carga/relatorio-planilha.md · atos normalizados em data/interim/planilha/atos.csv"
