-- 1. Tabela: orgao
CREATE TABLE orgao (
    id SERIAL PRIMARY KEY,
    parent_id INT REFERENCES orgao(id) ON DELETE SET NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE orgao IS 'Nó da hierarquia administrativa do DOU (ministérios, conselhos, comissões).';
COMMENT ON COLUMN orgao.parent_id IS 'Auto-relacionamento hierárquico (ex: CONAMA tem como pai o Ministério do Meio Ambiente).';

-- 2. Tabela: orgao_nome (histórico e vigência temporal de nomes)
CREATE TABLE orgao_nome (
    id SERIAL PRIMARY KEY,
    orgao_id INT NOT NULL REFERENCES orgao(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_orgao_nome_vigencia CHECK (data_fim IS NULL OR data_fim >= data_inicio)
);

COMMENT ON TABLE orgao_nome IS 'Histórico de variações de nomes dos órgãos ao longo do tempo com vigência.';
COMMENT ON COLUMN orgao_nome.data_fim IS 'Data final de vigência do nome. Se NULL, indica o nome em uso corrente.';

-- 3. Tabela: conselho (subconjunto dos órgãos que são objeto de estudo)
CREATE TABLE conselho (
    orgao_id INT PRIMARY KEY REFERENCES orgao(id) ON DELETE CASCADE,
    eh_participativo BOOLEAN NOT NULL DEFAULT TRUE,
    descricao TEXT,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE conselho IS 'Especialização de órgãos que são conselhos sob o escopo da pesquisa de participação social.';
COMMENT ON COLUMN conselho.eh_participativo IS 'Distingue conselhos com participação da sociedade civil daqueles puramente corporativos/consultivos (ex: CFM, CFF).';

-- 4. Tabela: ato (matérias publicadas no DOU sujeitas a retificação)
CREATE TABLE ato (
    id BIGSERIAL PRIMARY KEY,
    id_dou VARCHAR(100) NOT NULL,
    versao INT NOT NULL DEFAULT 1,
    orgao_id INT NOT NULL REFERENCES orgao(id) ON DELETE RESTRICT,
    data_publicacao DATE NOT NULL,
    ementa TEXT,
    conteudo TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ato_dou_versao UNIQUE (id_dou, versao),
    CONSTRAINT ck_ato_versao_positiva CHECK (versao >= 1)
);

COMMENT ON TABLE ato IS 'Matéria publicada no DOU por um conselho. Armazena versões de retificação preservando a chave de negócio.';
COMMENT ON COLUMN ato.id_dou IS 'Identificador natural da matéria emitido pela Imprensa Nacional.';
COMMENT ON COLUMN ato.versao IS 'Versão da publicação. Atos retificados recebem nova versão com o mesmo id_dou sem sobrescrever a original.';

-- 5. Tabela: tipologia (tabela de domínio das 5 categorias)
CREATE TABLE tipologia (
    sigla VARCHAR(10) PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT NOT NULL
);

COMMENT ON TABLE tipologia IS 'Domínio fechado com as 5 tipologias de atos normativos analisadas no projeto.';

-- 6. Tabela: revisor (atores do processo de curadoria)
CREATE TABLE revisor (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('HUMANO', 'PIPELINE')),
    email VARCHAR(255) UNIQUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE revisor IS 'Identificação dos agentes responsáveis pela classificação de atos (pesquisadores ou modelos automáticos).';
COMMENT ON COLUMN revisor.tipo IS 'Classifica o revisor entre HUMANO (bolsista, pesquisador) ou PIPELINE (modelo automatizado).';

-- 7. Tabela: classificacao (coração transacional do OLTP)
CREATE TABLE classificacao (
    id BIGSERIAL PRIMARY KEY,
    ato_id BIGINT NOT NULL REFERENCES ato(id) ON DELETE CASCADE,
    tipologia_sigla VARCHAR(10) NOT NULL REFERENCES tipologia(sigla) ON DELETE RESTRICT,
    revisor_id INT NOT NULL REFERENCES revisor(id) ON DELETE RESTRICT,
    confianca NUMERIC(4,3) NULL CHECK (confianca IS NULL OR (confianca >= 0 AND confianca <= 1)),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_classificacao_ato_revisor UNIQUE (ato_id, revisor_id)
);

COMMENT ON TABLE classificacao IS 'Julgamento classificatório de um ato normativo segundo uma tipologia, emitido por um revisor.';
COMMENT ON COLUMN classificacao.confianca IS 'Score de confiança da predição (utilizado quando revisor.tipo = PIPELINE, valor entre 0 e 1).';
COMMENT ON CONSTRAINT uq_classificacao_ato_revisor ON classificacao IS 'Garante que o mesmo revisor não duplique a classificação de um ato, permitindo convivência entre humano e máquina.';