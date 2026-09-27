-- Identidade dos conselhos (issue #4, ADR 0004). Renomeação continua em orgao_nome, com
-- vigência; grafia vai para orgao_alias, sem vigência, porque não é mudança legal.

-- Dos órgãos da lista da pesquisadora, só uma parte tem a data do ato de criação conferida.
-- Nulo quer dizer "não verificada": inventar uma data seria gravar um dado falso.
ALTER TABLE orgao_nome ALTER COLUMN data_inicio DROP NOT NULL;
COMMENT ON COLUMN orgao_nome.data_inicio IS 'Início da vigência do nome: data do ato legal que o criou ou deu. NULL = data não verificada (ADR 0004); consulta por vigência precisa tratar o nulo.';

ALTER TABLE orgao ADD COLUMN codigo_siorg INT NULL;
ALTER TABLE orgao ADD CONSTRAINT uq_orgao_codigo_siorg UNIQUE (codigo_siorg);
ALTER TABLE orgao ADD COLUMN sigla VARCHAR(30) NULL;
COMMENT ON COLUMN orgao.codigo_siorg IS 'Código da unidade no SIORG, quando o nome casa com exatamente uma unidade. Vínculo externo, não identidade (ADR 0004).';
COMMENT ON COLUMN orgao.sigla IS 'Sigla do órgão (SIORG ou a da planilha). Não é única: CNE e CNT se repetem entre conselhos diferentes.';

CREATE TABLE IF NOT EXISTS orgao_alias (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    chave VARCHAR(255) NOT NULL,
    fonte VARCHAR(20) NOT NULL CHECK (fonte IN ('PLANILHA', 'DOU')),
    orgao_id INT NULL REFERENCES orgao(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL CHECK (status IN ('RESOLVIDO', 'INDEFINIDO', 'AMBIGUO')),
    motivo TEXT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_orgao_alias_fonte_nome UNIQUE (fonte, nome),
    CONSTRAINT ck_orgao_alias_resolvido_tem_orgao CHECK ((status = 'RESOLVIDO') = (orgao_id IS NOT NULL)),
    CONSTRAINT ck_orgao_alias_pendente_tem_motivo CHECK (status = 'RESOLVIDO' OR motivo IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS ix_orgao_alias_chave ON orgao_alias (chave);

COMMENT ON TABLE orgao_alias IS 'Todo nome de órgão já visto numa fonte, apontando para o órgão (ADR 0004). Nome indefinido ou ambíguo fica aqui sem órgão e com o motivo: não some.';
COMMENT ON COLUMN orgao_alias.nome IS 'Nome como aparece na fonte, com espaços e quebras de linha reduzidos a um espaço.';
COMMENT ON COLUMN orgao_alias.chave IS 'Nome sem caixa, acento, espaços repetidos e sigla no fim (src/conselhos). Nomes com a mesma chave são o mesmo órgão.';
COMMENT ON COLUMN orgao_alias.status IS 'RESOLVIDO: aponta para um órgão. INDEFINIDO: nome genérico, sem como saber o órgão. AMBIGUO: à espera de decisão da squad ou da pesquisadora.';
