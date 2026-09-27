-- Chave dos atos da planilha da pesquisadora: conselho + ID_VERSAO (diário de 26/09, #3).
-- Substitui a D3 (ref_legal + órgão), que não se sustenta na planilha: o CNAS não tem
-- referência legal, o DISP_LEG do CONAMA traz só o tipo do ato e o CONDRAF repete
-- "Resolução Nº 61" em dois atos diferentes. O ID_VERSAO é único dentro de cada aba.

ALTER TABLE ato ADD COLUMN id_planilha INT NULL;

ALTER TABLE ato ADD CONSTRAINT ck_ato_planilha_completo
    CHECK (origem <> 'PLANILHA' OR id_planilha IS NOT NULL);

-- Recusa a mesma linha da planilha duas vezes: é o que torna a carga idempotente.
CREATE UNIQUE INDEX uq_ato_planilha ON ato (orgao_id, id_planilha) WHERE origem = 'PLANILHA';

COMMENT ON COLUMN ato.id_planilha IS 'ID_VERSAO da planilha da pesquisadora. Com orgao_id, é a chave dos atos de origem PLANILHA; NULL para os do DOU.';
COMMENT ON COLUMN ato.ref_legal IS 'Referência legal como aparece na fonte (ex.: Resolução Nº 18). Informativa: não é única e falta em parte da planilha.';
COMMENT ON COLUMN ato.origem IS 'DOU: matéria lida do Diário Oficial (exige id_dou e conteudo). PLANILHA: ato da carga inicial da pesquisadora, 2003–2020 (exige id_planilha); ementa é o resumo dela e conteudo o texto que ela transcreveu, quando há.';
