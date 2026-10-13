#!/usr/bin/env bash
# Teste da janela de reprocessamento (issue #31): quais dias o make ingest
# reprocessa, dados DATA e JANELA. Não baixa nada e não toca o banco.
# Uso: bash tests/ingest/test_janela.sh   (a partir de qualquer diretório)
set -euo pipefail
cd "$(dirname "$0")/../.."

falhas=0
ok()    { echo "  ok    $1"; }
falha() { echo "  FALHA $1"; falhas=$((falhas + 1)); }

espera_dias() {
  local nome=$1 esperado=$2 out; shift 2
  if out=$(make -s janela "$@" 2>&1) && [ "$out" = "$esperado" ]; then ok "$nome"
  else falha "$nome — esperava '$esperado', veio: $out"; fi
}

espera_erro() {
  local nome=$1 out; shift
  if out=$(make -s janela "$@" 2>&1); then falha "$nome — deveria ter sido recusado, veio: $out"
  else ok "$nome"; fi
}

echo "janela"
espera_dias "o padrão são 7 dias, terminando em DATA" \
  "2026-10-05 2026-10-06 2026-10-07 2026-10-08 2026-10-09 2026-10-10 2026-10-11" DATA=2026-10-11
espera_dias "JANELA=1 é só o dia" "2026-10-11" DATA=2026-10-11 JANELA=1
espera_dias "a janela atravessa o mês, do mais antigo para o mais novo" \
  "2026-09-29 2026-09-30 2026-10-01 2026-10-02" DATA=2026-10-02 JANELA=4
espera_dias "e atravessa o 29 de fevereiro" "2028-02-28 2028-02-29 2028-03-01" DATA=2028-03-01 JANELA=3
espera_erro "JANELA=0 é recusada" DATA=2026-10-11 JANELA=0
espera_erro "JANELA que não é número é recusada" DATA=2026-10-11 JANELA=semana
espera_erro "DATA malformada é recusada" DATA=11/10/2026

echo
if [ "$falhas" -gt 0 ]; then echo "FALHOU: $falhas caso(s)"; exit 1; fi
echo "OK"
