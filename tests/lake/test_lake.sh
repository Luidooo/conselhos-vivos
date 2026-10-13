#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

# Diretório temporário dentro de data/silver para ser acessível pelo volume do container
TMP_NAME="_test_lake_$$"
TMP_HOST_DIR="data/silver/$TMP_NAME"
TMP_CONTAINER_DIR="/data/silver/$TMP_NAME"

trap 'rm -rf "$TMP_HOST_DIR"' EXIT INT TERM

# 0. Obtém a contagem real de atos do banco
esperado=$(docker compose exec -T db sh -c \
  'psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q -tA -c "SELECT count(*) FROM ato;"' | tr -d '[:space:]')

echo "==> [test_lake] Contagem no banco OLTP: $esperado atos"

echo "==> [test_lake] 1. Executando primeira sincronização em diretório temporário ($TMP_HOST_DIR)..."
DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose --progress quiet run --rm -T lake "$TMP_CONTAINER_DIR"

echo "==> [test_lake] 2. Testando idempotência (segunda execução)..."
saida=$(DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose --progress quiet run --rm -T lake "$TMP_CONTAINER_DIR" 2>&1 || true)
echo "$saida" | grep -q "inseridas=0" || { echo "FALHOU: inseriu linhas na 2ª vez ou deu erro! Saída:"; echo "$saida"; exit 1; }
echo "$saida" | grep -q "atualizadas=0" || { echo "FALHOU: atualizou linhas na 2ª vez! Saída:"; echo "$saida"; exit 1; }
echo "$saida" | grep -q "inalteradas=$esperado" || { echo "FALHOU: contagem de inalteradas ($saida) não bate com esperado ($esperado)!"; exit 1; }

echo "==> [test_lake] 3. Validando leitura analítica com DuckDB..."
docker run --rm -v "$PWD/data/silver:/data/silver" --entrypoint duckdb duckdb/duckdb:1.5.6 -c "
INSTALL delta;
LOAD delta;

-- Mostra a distribuição da tipologia por conselho (critério de aceite E2):
SELECT orgao_sigla, tipologia_sigla, count(*) AS total_atos
FROM delta_scan('$TMP_CONTAINER_DIR')
GROUP BY 1, 2
ORDER BY 1, 3 DESC
LIMIT 10;
"

total_duckdb=$(docker run --rm -v "$PWD/data/silver:/data/silver" --entrypoint duckdb duckdb/duckdb:1.5.6 -csv -noheader -c "
INSTALL delta;
LOAD delta;
SELECT count(*) FROM delta_scan('$TMP_CONTAINER_DIR');
" | tr -d '[:space:]')

if [ "$total_duckdb" != "$esperado" ]; then
  echo "FALHOU: contagem no DuckDB ($total_duckdb) não bate com o banco ($esperado)!"
  exit 1
fi

echo "==> [test_lake] OK: Camada analítica Delta Lake validada com sucesso ($total_duckdb atos)!"