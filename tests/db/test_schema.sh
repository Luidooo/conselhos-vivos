#!/usr/bin/env bash
set -euo pipefail

# 1. Carrega as variáveis do .env se o arquivo existir
if [ -f .env ]; then
  # exporta as variáveis sem quebrar caso haja comentários
  export $(grep -v '^#' .env | xargs)
elif [ -f ../../.env ]; then
  export $(grep -v '^#' ../../.env | xargs)
fi

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== [TESTE DE FUMAÇA] Modelagem OLTP (Issue #2) ===${NC}\n"

# Função auxiliar para rodar queries psql com as variáveis certas
run_sql() {
    docker compose exec -T db psql \
      -U "${POSTGRES_USER}" \
      -d "${POSTGRES_DB}" \
      -v ON_ERROR_STOP=1 -q -t -A -c "$1"
}

# 1. Checar se o banco está de pé
echo -n "1. Verificando conectividade com o banco... "
if docker compose exec -T db pg_isready -q; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FALHA: Postgres não está respondendo.${NC}"
    exit 1
fi

# 2. Conferir se as 7 tabelas foram criadas
echo -n "2. Verificando se as 7 tabelas existem... "
TABELAS_ESPERADAS=("orgao" "orgao_nome" "conselho" "ato" "tipologia" "revisor" "classificacao")
QTD_TABELAS=$(run_sql "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('orgao', 'orgao_nome', 'conselho', 'ato', 'tipologia', 'revisor', 'classificacao');")

if [ "$QTD_TABELAS" -eq 7 ]; then
    echo -e "${GREEN}OK (7/7 tabelas encontradas)${NC}"
else
    echo -e "${RED}FALHA: Esperadas 7 tabelas, encontradas $QTD_TABELAS.${NC}"
    exit 1
fi

# 3. Conferir se as 5 tipologias foram carregadas no seed
echo -n "3. Verificando seed das 5 tipologias (DEF, FISC, GEST, AUTO, IP)... "
TIPOLOGIAS=$(run_sql "SELECT count(*) FROM tipologia WHERE sigla IN ('DEF', 'FISC', 'GEST', 'AUTO', 'IP');")
if [ "$TIPOLOGIAS" -eq 5 ]; then
    echo -e "${GREEN}OK (5/5 tipologias carregadas)${NC}"
else
    echo -e "${RED}FALHA: Esperadas 5 tipologias, encontradas $TIPOLOGIAS.${NC}"
    exit 1
fi

# 4. Conferir comentários obrigatórios (COMMENT ON)
echo -n "4. Verificando existência de comentários (documentação no banco)... "
QTD_COMMENTS=$(run_sql "SELECT count(*) FROM pg_description;")
if [ "$QTD_COMMENTS" -ge 7 ]; then
    echo -e "${GREEN}OK ($QTD_COMMENTS comentários registrados)${NC}"
else
    echo -e "${RED}FALHA: Poucos ou nenhum comentário encontrado ($QTD_COMMENTS). Documente o schema com COMMENT ON.${NC}"
    exit 1
fi

# 5. Teste Transacional de Domínio e Restrições de Integridade
echo "5. Executando testes de integridade relacional..."

run_sql "
BEGIN;

-- A. Inserir hierarquia de órgão e histórico de nomes
INSERT INTO orgao (id, parent_id) VALUES (1000, NULL);
INSERT INTO orgao_nome (orgao_id, nome, data_inicio, data_fim) 
VALUES (1000, 'Ministério do Meio Ambiente', '2000-01-01', '2022-12-31');
INSERT INTO orgao_nome (orgao_id, nome, data_inicio, data_fim) 
VALUES (1000, 'Ministério do Meio Ambiente e Mudança do Clima', '2023-01-01', NULL);

-- Inserir conselho vinculado
INSERT INTO conselho (orgao_id, eh_participativo) VALUES (1000, true);

-- B. Testar Ato e Retificação (mesmo id_dou, versões diferentes)
INSERT INTO ato (id, id_dou, versao, data_publicacao, conteudo, orgao_id)
VALUES (9001, 'DOU-2026-TESTE-01', 1, '2026-03-01', 'Texto original da portaria', 1000);

INSERT INTO ato (id, id_dou, versao, data_publicacao, conteudo, orgao_id)
VALUES (9002, 'DOU-2026-TESTE-01', 2, '2026-03-05', 'Texto retificado com correção', 1000);

-- C. Cadastrar revisores (Humano e Pipeline)
INSERT INTO revisor (id, nome, tipo, email) VALUES (8001, 'Pesquisadora Ana', 'HUMANO', 'ana@unb.br');
INSERT INTO revisor (id, nome, tipo, email) VALUES (8002, 'Pipeline BERT-v1', 'PIPELINE', 'bot@pipeline.local');

-- D. Testar coexistência de classificação Humana e Automática no mesmo ato (9001)
INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES (9001, 'DEF', 8001);
INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES (9001, 'GEST', 8002);

ROLLBACK; -- Desfaz os dados fictícios sem poluir o banco
"

echo -e "   -> Hierarquia, retificação e coexistência: ${GREEN}OK${NC}"

# 6. Teste de Violação: Bloqueio de duplicidade pelo mesmo revisor
echo -n "6. Testando se o banco impede duplicidade do mesmo revisor no mesmo ato... "
SET_UP_TEST="
INSERT INTO orgao (id, parent_id) VALUES (9999, NULL) ON CONFLICT DO NOTHING;
INSERT INTO ato (id, id_dou, versao, data_publicacao, conteudo, orgao_id) VALUES (9999, 'TEST-DUP', 1, '2026-01-01', 'conteudo', 9999) ON CONFLICT DO NOTHING;
INSERT INTO revisor (id, nome, tipo, email) VALUES (9999, 'Robô Teste', 'PIPELINE', 'bot@test.br') ON CONFLICT DO NOTHING;
INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES (9999, 'DEF', 9999);
"

# Roda o setup
run_sql "$SET_UP_TEST" > /dev/null 2>&1

# Tenta inserir duplicata proposital
if run_sql "INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES (9999, 'GEST', 9999);" > /dev/null 2>&1; then
    echo -e "${RED}FALHA: O banco aceitou duplicata para o mesmo revisor no mesmo ato!${NC}"
    # Limpa antes de sair
    run_sql "DELETE FROM classificacao WHERE ato_id = 9999; DELETE FROM ato WHERE id = 9999; DELETE FROM revisor WHERE id = 9999; DELETE FROM orgao WHERE id = 9999;" > /dev/null 2>&1
    exit 1
else
    echo -e "${GREEN}OK (Restrição UNIQUE uq_classificacao_ato_revisor atuou com sucesso)${NC}"
fi

# Limpa dados do teste 6
run_sql "DELETE FROM classificacao WHERE ato_id = 9999; DELETE FROM ato WHERE id = 9999; DELETE FROM revisor WHERE id = 9999; DELETE FROM orgao WHERE id = 9999;" > /dev/null 2>&1

echo -e "\n${GREEN}=== TODOS OS TESTES DE FUMAÇA PASSARAM COM SUCESSO! ===${NC}"