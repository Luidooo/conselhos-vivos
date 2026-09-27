#!/usr/bin/env bash
# Carrega a planilha da pesquisadora no OLTP e atualiza os relatórios: primeiro a identidade
# dos conselhos (#4, ADR 0004), depois os atos (#3). Idempotente: rodar de novo não duplica
# órgão, alias, ato nem classificação, e gera os mesmos relatórios.
# Pré-requisito: banco no ar e migrado (make migrate). Uso: bash scripts/carga.sh (ou make carga)
set -euo pipefail
cd "$(dirname "$0")/.."

carga() { docker compose --progress quiet run --rm -T carga "$@"; }
conselhos() { docker compose --progress quiet run --rm -T --entrypoint python carga -m conselhos "$@"; }
psql_db() {
  docker compose exec -T db sh -c 'psql -X -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -f -'
}

# O SQL vai para um arquivo antes do psql: se a leitura da planilha falhar no meio,
# nada chega ao banco (num pipe, o psql executaria o começo).
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p docs/carga
conselhos sql > "$tmp/conselhos.sql"
psql_db < "$tmp/conselhos.sql"
conselhos relatorio > "$tmp/relatorio-conselhos.md"
mv "$tmp/relatorio-conselhos.md" docs/carga/relatorio-conselhos.md

carga sql > "$tmp/carga.sql"
psql_db < "$tmp/carga.sql"

carga relatorio > "$tmp/relatorio.md"
mv "$tmp/relatorio.md" docs/carga/relatorio-planilha.md
mkdir -p data/interim/planilha
carga csv > "$tmp/atos.csv"
mv "$tmp/atos.csv" data/interim/planilha/atos.csv
echo "→ relatórios em docs/carga/ (conselhos e planilha) · atos normalizados em data/interim/planilha/atos.csv"
