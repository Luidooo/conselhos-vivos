#!/usr/bin/env bash
# Medições do ADR 0011. Uso:
#   bash docs/adr/medicoes/0011-disponibilizacao/medir.sh | tee docs/adr/medicoes/0011-disponibilizacao/medicoes.txt
set -euo pipefail
cd "$(dirname "$0")/../../../.."
echo "# Medições do ADR 0011, $(date -u '+%Y-%m-%d %H:%M') UTC"
docker compose --progress quiet run --rm -T orquestrador sh -c 'cd /app/dbt && dbt parse -q && python /app/docs/adr/medicoes/0011-disponibilizacao/medir.py'
echo "## tamanho do que o consumo lê"
du -h data/gold/conselhos.duckdb data/gold/metricas/*.csv
