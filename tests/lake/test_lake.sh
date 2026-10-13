#!/usr/bin/env bash
set -euo pipefail

# Limpa resquício anterior para testar do zero
rm -rf data/silver/atos

echo "==> [test_lake] 1. Executando primeira sincronização..."
make lake

echo "==> [test_lake] 2. Testando idempotência (segunda execução)..."
saida=$(make lake 2>&1 || true)
echo "$saida" | grep -q "inseridas=0" || { echo "FALHOU: inseriu linhas na 2ª vez ou deu erro! Saída:"; echo "$saida"; exit 1; }
echo "$saida" | grep -q "atualizadas=0" || { echo "FALHOU: atualizou linhas na 2ª vez! Saída:"; echo "$saida"; exit 1; }

echo "==> [test_lake] 3. Validando leitura analítica com DuckDB..."
# --entrypoint duckdb garante que o binário correto seja chamado
docker run --rm -v "$PWD/data/silver:/data/silver" --entrypoint duckdb duckdb/duckdb -c "
INSTALL delta;
LOAD delta;

-- Mostra a distribuição da tipologia por conselho (critério de aceite E2):
SELECT orgao_sigla, tipologia_sigla, count(*) AS total_atos
FROM delta_scan('/data/silver/atos')
GROUP BY 1, 2
ORDER BY 1, 3 DESC
LIMIT 10;

-- Validação de contagem total:
SELECT count(*) AS total_geral FROM delta_scan('/data/silver/atos');
" | grep -qE "215|311" || { echo "FALHOU: contagem no DuckDB não bate com o esperado!"; exit 1; }

echo "==> [test_lake] OK: Camada analítica Delta Lake validada com sucesso!"