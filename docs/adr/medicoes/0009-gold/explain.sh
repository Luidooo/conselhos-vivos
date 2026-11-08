#!/usr/bin/env bash
# EXPLAIN (ANALYZE, BUFFERS) da extração do lake, a mesma consulta do código (sem cópia do SQL).
# Caminho do `make lake` (todos os atos):
#   bash docs/adr/medicoes/0009-gold/explain.sh > docs/adr/medicoes/0009-gold/explain-antes.txt
# Caminho do `make cdc` (só os atos afetados, `a.id = ANY(...)`):
#   ATO_IDS=1,2,3 bash docs/adr/medicoes/0009-gold/explain.sh > docs/adr/medicoes/0009-gold/explain-antes-cdc.txt
set -euo pipefail
cd "$(dirname "$0")/../../../.."
docker compose --progress quiet run --rm -T -e ATO_IDS="${ATO_IDS:-}" lake python -c "
import os
from lake.sync import QUERY_OLTP, obter_conexao
ids = [int(i) for i in os.environ['ATO_IDS'].split(',')] if os.environ['ATO_IDS'] else None
with obter_conexao() as c:
    for (linha,) in c.execute('EXPLAIN (ANALYZE, BUFFERS) ' + QUERY_OLTP, {'ato_ids': ids}):
        print(linha)
" 2> >(grep -v 'notice\|level=warning' >&2)
