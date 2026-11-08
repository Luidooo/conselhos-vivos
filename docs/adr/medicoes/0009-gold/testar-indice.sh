#!/usr/bin/env bash
# Mede a extração do lake com um índice candidato e DESFAZ tudo (ROLLBACK): nada fica no banco.
# Salva o plano de cada cenário em explain-com-indice*.txt e imprime o melhor de 5 execuções.
# Uso (banco no ar e migrado):
#   bash docs/adr/medicoes/0009-gold/testar-indice.sh
#   INDICE='' bash ...    # sem índice novo: só mostra se o planner usa um índice que já existe
# Para outro candidato, passe INDICE='CREATE INDEX ix_teste ON tabela (...)' e TABELA=tabela.
set -euo pipefail
cd "$(dirname "$0")/../../../.."
dir=docs/adr/medicoes/0009-gold
export INDICE="${INDICE-CREATE INDEX ix_teste ON orgao_nome (orgao_id, data_inicio, data_fim)}" TABELA="${TABELA:-orgao_nome}"
docker compose --progress quiet run --rm -T -e INDICE -e TABELA lake python -c "
import os, re
from lake.sync import QUERY_OLTP, obter_conexao

def medir(c, nome):
    tempos = []
    for _ in range(5):
        plano = '\n'.join(l for (l,) in c.execute('EXPLAIN (ANALYZE, BUFFERS) ' + QUERY_OLTP, {'ato_ids': None}))
        tempos.append(float(re.search(r'Execution Time: ([\d.]+)', plano).group(1)))
    print(f'RESULTADO {nome}: {min(tempos):.1f} ms (melhor de 5)')
    print(f'ARQUIVO {nome}'); print(plano)

with obter_conexao() as c:
    c.execute('BEGIN')
    if os.environ['INDICE']:
        c.execute(os.environ['INDICE']); c.execute('ANALYZE ' + os.environ['TABELA'])
        medir(c, 'explain-com-indice')
    # jit off: o custo inflado do seqscan off dispara o JIT (~335 ms), que não tem a ver com o índice.
    c.execute('SET LOCAL enable_seqscan = off'); c.execute('SET LOCAL jit = off')
    medir(c, 'explain-com-indice-seqscan-off' if os.environ['INDICE'] else 'explain-seqscan-off')
    c.execute('ROLLBACK')
" 2> >(grep -v 'notice\|level=warning' >&2) | awk -v d="$dir" '/^RESULTADO/{print; next} /^ARQUIVO/{f=d"/"$2".txt"; printf "" > f; next} f{print > f}'
