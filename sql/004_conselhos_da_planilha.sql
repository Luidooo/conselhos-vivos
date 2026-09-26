-- Os 5 conselhos da planilha da pesquisadora, para a carga da #3 (todo ato exige orgao_id).
-- Só o nome vigente, com a data do ato legal que o instituiu, conferida no planalto.gov.br
-- em 26/09. Sem ministério pai nem nomes anteriores: a hierarquia e os aliases são da #4,
-- que reaproveita estes 5 órgãos (a carga os encontra pelo nome vigente).
--
--   CNAS        Lei nº 8.742, de 7/12/1993, art. 17
--   CONAMA      Lei nº 6.938, de 31/8/1981, art. 6º
--   CONCIDADES  Lei nº 10.683, de 28/5/2003, arts. 31 e 33: renomeia o Conselho Nacional
--               de Desenvolvimento Urbano para Conselho das Cidades (nome anterior: #4)
--   CONDRAF     Decreto nº 3.508, de 14/6/2000 (sigla CNDRS); o Decreto nº 4.854, de
--               8/10/2003, mantém o nome e adota a sigla CONDRAF
--   CNPIR       Lei nº 10.678, de 23/5/2003, art. 2º

CREATE TEMP TABLE conselho_planilha (nome text, data_inicio date, descricao text) ON COMMIT DROP;
INSERT INTO conselho_planilha VALUES
('Conselho Nacional de Assistência Social',               '1993-12-07', 'CNAS. Aba CNAS da planilha da pesquisadora.'),
('Conselho Nacional do Meio Ambiente',                    '1981-08-31', 'CONAMA. Aba CONAMA da planilha da pesquisadora.'),
('Conselho das Cidades',                                  '2003-05-28', 'ConCidades. Aba CONCIDADES da planilha da pesquisadora.'),
('Conselho Nacional de Desenvolvimento Rural Sustentável', '2000-06-14', 'CONDRAF. Aba CONDRAF da planilha da pesquisadora.'),
('Conselho Nacional de Promoção da Igualdade Racial',     '2003-05-23', 'CNPIR. Aba CNPIR da planilha da pesquisadora.');

DO $$
DECLARE c record; novo int;
BEGIN
  FOR c IN SELECT * FROM conselho_planilha LOOP
    CONTINUE WHEN EXISTS (SELECT 1 FROM orgao_nome WHERE nome = c.nome AND data_fim IS NULL);
    INSERT INTO orgao DEFAULT VALUES RETURNING id INTO novo;
    INSERT INTO orgao_nome (orgao_id, nome, data_inicio) VALUES (novo, c.nome, c.data_inicio);
    INSERT INTO conselho (orgao_id, eh_participativo, descricao) VALUES (novo, TRUE, c.descricao);
  END LOOP;
END $$;
