#!/usr/bin/env bash
# Testa um índice candidato sem deixar rastro: cria, mede (melhor de 5 execuções) e desfaz (ROLLBACK).
# Uso: bash docs/adr/medicoes/0009-gold/testar-indice.sh   (banco no ar e migrado)
# Para testar outro índice, troque INDICE abaixo.
set -euo pipefail
cd "$(dirname "$0")/../../../.."
INDICE='CREATE INDEX ix_teste ON orgao_nome (orgao_id, data_inicio, data_fim)' \
TABELA='orgao_nome' \
docker compose --progress quiet run --rm -T -e INDICE -e TABELA lake python -c "
import os, re
from lake.sync import QUERY_OLTP, obter_conexao

def medir(c, rotulo):
    tempos = []
    for _ in range(5):
        plano = '\n'.join(l for (l,) in c.execute('EXPLAIN (ANALYZE, BUFFERS) ' + QUERY_OLTP, {'ato_ids': None}))
        tempos.append(float(re.search(r'Execution Time: ([\d.]+)', plano).group(1)))
    print(f'{rotulo}: {min(tempos):.1f} ms', '(usa ix_teste)' if 'ix_teste' in plano else '')

with obter_conexao() as c:
    medir(c, 'sem índice')
    c.execute('BEGIN')
    c.execute(os.environ['INDICE'])
    c.execute('ANALYZE ' + os.environ['TABELA'])
    medir(c, 'com o índice')
    c.execute('SET LOCAL enable_seqscan = off')
    medir(c, 'com o índice, seqscan off')
    c.execute('ROLLBACK')
" 2>&1 | grep -v 'notice\|level=warning'
