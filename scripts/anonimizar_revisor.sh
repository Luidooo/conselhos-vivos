#!/usr/bin/env bash
# Descarte do dado pessoal de um revisor que saiu do projeto (LGPD, docs/lgpd.md): chama a função
# anonimizar_revisor da migração 007, a mesma que o tests/db/test_acesso.sh testa.
# Uso: bash scripts/anonimizar_revisor.sh ID   (ou make anonimizar-revisor ID=n)
set -euo pipefail
cd "$(dirname "$0")/.."
id=${1:?id do revisor}
[[ "$id" =~ ^[0-9]+$ ]] || { echo "o id é um número"; exit 1; }
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "SELECT anonimizar_revisor($1)"' sh "$id"
