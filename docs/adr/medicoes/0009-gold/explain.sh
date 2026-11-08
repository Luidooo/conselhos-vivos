#!/usr/bin/env bash
# EXPLAIN (ANALYZE, BUFFERS) da extração do lake, a mesma consulta do código (sem cópia do SQL).
# Uso: bash docs/adr/medicoes/0009-gold/explain.sh > docs/adr/medicoes/0009-gold/explain-antes.txt
set -euo pipefail
cd "$(dirname "$0")/../../../.."
docker compose --progress quiet run --rm -T lake python -c "
from lake.sync import QUERY_OLTP, obter_conexao
with obter_conexao() as c:
    for (linha,) in c.execute('EXPLAIN (ANALYZE, BUFFERS) ' + QUERY_OLTP, {'ato_ids': None}):
        print(linha)
"
