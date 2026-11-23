-- E4 (ADR 0011): os alertas do ETL reverso e os papéis com privilégio mínimo.
-- As senhas vêm do ambiente do container do banco (docker-compose.yml), nunca do repositório.

CREATE TABLE IF NOT EXISTS alerta (
    id BIGSERIAL PRIMARY KEY,
    orgao_id INT NOT NULL REFERENCES orgao(id) ON DELETE RESTRICT,
    tipo VARCHAR(30) NOT NULL CHECK (tipo IN ('em_silencio', 'citado_sem_ato_proprio')),
    mes_referencia DATE NOT NULL,
    detalhe TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tratado_em TIMESTAMPTZ NULL,
    tratado_por INT NULL REFERENCES revisor(id) ON DELETE RESTRICT,
    nota TEXT NULL,
    CONSTRAINT uq_alerta UNIQUE (orgao_id, tipo, mes_referencia),
    CONSTRAINT ck_alerta_tratado CHECK ((tratado_em IS NULL) = (tratado_por IS NULL))
);
COMMENT ON TABLE alerta IS 'ETL reverso (E4): a situação de um conselho, tratada na gold, que pede ação da curadoria. Um alerta por conselho, tipo e mês de referência.';
COMMENT ON COLUMN alerta.tratado_em IS 'Quando a curadoria tratou o alerta, na página Revisar. Nulo: aberto.';

\getenv senha_etl ETL_REVERSO_PASSWORD
\getenv senha_app APP_CURADORIA_PASSWORD
\getenv senha_leitor LEITOR_ANALITICO_PASSWORD

-- Descarte do dado pessoal de um revisor que saiu (LGPD, docs/lgpd.md). Ele não pode ser apagado: as classificações
-- dele são o histórico da curadoria (ADR 0001). Perde o nome e o e-mail, e o registro fica.
CREATE FUNCTION anonimizar_revisor(p_id INT) RETURNS VOID LANGUAGE sql AS $$
    UPDATE revisor SET nome = 'Revisor removido', email = NULL WHERE id = p_id AND tipo = 'HUMANO';
$$;
REVOKE EXECUTE ON FUNCTION anonimizar_revisor(INT) FROM PUBLIC;

CREATE ROLE etl_reverso LOGIN PASSWORD :'senha_etl';
CREATE ROLE app_curadoria LOGIN PASSWORD :'senha_app';
CREATE ROLE leitor_analitico LOGIN PASSWORD :'senha_leitor';

-- etl_reverso: escreve alerta e só atualiza o texto dele; quem trata é a curadoria.
GRANT SELECT, INSERT ON alerta TO etl_reverso;
GRANT UPDATE (detalhe) ON alerta TO etl_reverso;
GRANT USAGE ON SEQUENCE alerta_id_seq TO etl_reverso;

-- app_curadoria: lê o que a página Revisar mostra e marca o alerta como tratado.
-- O recorte de coluna (LGPD): do revisor, só id, nome e tipo; o e-mail fica de fora.
GRANT SELECT ON alerta, orgao_nome, conselho TO app_curadoria;
GRANT SELECT (id, nome, tipo) ON revisor TO app_curadoria;
GRANT UPDATE (tratado_em, tratado_por, nota) ON alerta TO app_curadoria;

-- leitor_analitico: o dbt anexa o OLTP só para ler os órgãos.
GRANT SELECT ON orgao, orgao_nome, conselho TO leitor_analitico;
