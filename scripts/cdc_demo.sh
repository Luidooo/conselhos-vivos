#!/usr/bin/env bash
# Demonstração do fluxo de mudanças OLTP -> Delta (ADR 0007): reclassifica um ato
# (insert-only: entra uma linha nova em classificacao, nada é alterado) e mostra a
# mudança atravessando o slot lógico até a tabela Delta.
# Uso: bash scripts/cdc_demo.sh        (ou make cdc-demo; ATO_ID=123 escolhe o ato)
set -euo pipefail
cd "$(dirname "$0")/.."

psql_db() {
  docker compose exec -T db sh -c \
    'psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q -tA -c "$1"' sh "$1"
}

delta_do_ato() {
  docker run --rm -v "$PWD/data/silver:/data/silver:ro" --entrypoint duckdb duckdb/duckdb:1.5.6 -c "
INSTALL delta; LOAD delta;
SELECT ato_id, orgao_sigla, tipologia_sigla, revisor_tipo, atualizado_em
FROM delta_scan('/data/silver/atos') WHERE ato_id = $1;" 2>&1 | grep -v -E 'Installing|Loading|^$' || true
}

docker compose up -d --wait --wait-timeout 90 db
[ "$(psql_db 'SHOW wal_level')" = logical ] || { echo "wal_level não é logical: rode make down && make up"; exit 1; }

echo "==> 1. Carga completa no Delta e slot criado (make lake; make cdc)"
make --no-print-directory lake
make --no-print-directory cdc   # cria o slot, se faltar, e zera o que já estava pendente

ato=${ATO_ID:-$(psql_db "SELECT id FROM ato ORDER BY id LIMIT 1")}
revisor=$(psql_db "INSERT INTO revisor (nome, tipo, email) VALUES ('Curador da Demonstração', 'HUMANO', 'curador-demo@pesquisa.local') ON CONFLICT (email) DO UPDATE SET nome = EXCLUDED.nome RETURNING id")
atual=$(psql_db "SELECT COALESCE((SELECT tipologia_sigla FROM classificacao_vigente cv JOIN revisor r ON r.id = cv.revisor_id WHERE cv.ato_id = $ato ORDER BY (r.tipo='HUMANO') DESC, cv.criado_em DESC LIMIT 1), '')")
nova=$(psql_db "SELECT sigla FROM tipologia WHERE sigla <> '$atual' ORDER BY sigla DESC LIMIT 1")

echo "==> 2. Ato $ato no Delta ANTES (tipologia vigente: '${atual:-nenhuma}')"
delta_do_ato "$ato"

echo "==> 3. Reclassificando o ato $ato como '$nova' (INSERT em classificacao, revisor $revisor)"
psql_db "INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES ($ato, '$nova', $revisor)"

echo "==> 4. Consumindo o slot (make cdc)"
make --no-print-directory cdc

echo "==> 5. Ato $ato no Delta DEPOIS"
delta_do_ato "$ato"
echo "==> Reexecutar make cdc agora não encontra nada pendente (pendentes=0)."
echo ""
echo "==> A reclassificação permanece registrada no banco histórico (insert-only, ADR 0001)."
echo "==> Como usa revisor próprio, ela não afeta 'make test' nem exige 'make reset'."
