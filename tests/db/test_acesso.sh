#!/usr/bin/env bash
# Controle de acesso da E4 (ADR 0011): o que cada papel pode e não pode, e o descarte do dado pessoal do revisor.
# Cada caso roda numa transação desfeita: o superusuário cria um órgão e um ato de teste, e o comando roda depois
# de SET LOCAL ROLE, com os privilégios do papel. Não depende da carga: roda num banco só migrado, como no CI.
# Pré-requisito: banco no ar e migrado (make migrate). Uso: bash tests/db/test_acesso.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

falhas=0
ok()    { echo "  ok    $1"; }
falha() { echo "  FALHA $1"; falhas=$((falhas + 1)); }

psql_db() {
  docker compose exec -T db sh -c \
    'psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q -tA -c "$1"' sh "$1" 2>&1
}

# O órgão e o ato de teste. O id do órgão fica numa configuração da transação, que qualquer papel lê
# sem privilégio: o etl_reverso não lê a tabela conselho.
BASE="INSERT INTO orgao DEFAULT VALUES;
INSERT INTO ato (origem, id_dou, orgao_id, data_publicacao, conteudo)
  VALUES ('DOU', 'TESTE-ACESSO', currval('orgao_id_seq'), '2026-09-01', 'texto');
SELECT set_config('teste.orgao', currval('orgao_id_seq')::text, true)"

como() { psql_db "BEGIN; $BASE; SET LOCAL ROLE $1; $2; ROLLBACK;"; }  # como PAPEL SQL
pode()     { if out=$(como "$2" "$3"); then ok "$1"; else falha "$1 — recusado: $out"; fi; }
nao_pode() { if out=$(como "$2" "$3"); then falha "$1 — o banco aceitou"; elif grep -q "permission denied" <<<"$out"; then ok "$1"; else falha "$1 — recusou por outro motivo: $out"; fi; }

ALERTA="INSERT INTO alerta (orgao_id, tipo, mes_referencia, detalhe)
  VALUES (current_setting('teste.orgao')::int, 'em_silencio', DATE '2026-09-01', 'x')"

echo "etl_reverso"
pode     "insere alerta"                        etl_reverso "$ALERTA"
pode     "atualiza o detalhe"                   etl_reverso "$ALERTA; UPDATE alerta SET detalhe = 'y'"
nao_pode "não marca alerta como tratado"        etl_reverso "$ALERTA; UPDATE alerta SET nota = 'y'"
nao_pode "não lê os atos"                       etl_reverso "SELECT count(*) FROM ato"
nao_pode "não lê os revisores"                  etl_reverso "SELECT count(*) FROM revisor"

echo "app_curadoria"
pode     "lê alerta e nome do conselho"         app_curadoria "SELECT count(*) FROM alerta a JOIN orgao_nome n ON n.orgao_id = a.orgao_id"
pode     "lê id, nome e tipo do revisor"        app_curadoria "SELECT id, nome, tipo FROM revisor"
nao_pode "não lê o e-mail do revisor"           app_curadoria "SELECT email FROM revisor"
nao_pode "não insere alerta"                    app_curadoria "$ALERTA"
nao_pode "não apaga alerta"                     app_curadoria "DELETE FROM alerta"

echo "leitor_analitico"
pode     "lê órgãos, nomes e conselhos"         leitor_analitico "SELECT count(*) FROM orgao o JOIN orgao_nome n ON n.orgao_id = o.id JOIN conselho c ON c.orgao_id = o.id"
nao_pode "não lê os atos"                       leitor_analitico "SELECT count(*) FROM ato"
nao_pode "não escreve"                          leitor_analitico "UPDATE conselho SET descricao = descricao"

echo "descarte do revisor (LGPD)"
anon=$(psql_db "BEGIN; $BASE;
  INSERT INTO revisor (nome, tipo, email) VALUES ('Fulana', 'HUMANO', 'fulana@exemplo.org');
  INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES (currval('ato_id_seq'), 'GEST', currval('revisor_id_seq'));
  SELECT anonimizar_revisor(currval('revisor_id_seq')::int);
  SELECT (SELECT count(*) FROM classificacao WHERE revisor_id = r.id) || ',' || coalesce(r.email, 'nulo') || ',' || r.nome
    FROM revisor r WHERE r.id = currval('revisor_id_seq');
  ROLLBACK;" | tail -1)
[ "$anon" = "1,nulo,Revisor removido" ] && ok "anonimiza e mantém a classificação" || falha "anonimizar — veio: $anon"

echo
[ "$falhas" -eq 0 ] && echo "acesso: todos os casos passaram" || { echo "acesso: $falhas falha(s)"; exit 1; }
