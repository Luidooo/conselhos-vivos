-- Código 99 da planilha da pesquisadora (decisão da squad em 26/09, #3). Seis atos o usam:
-- moções do CONAMA e do CNPIR, uma menção honrosa do CNAS e duas recomendações do ConCidades.
-- Entra como rótulo para a carga não perder a classificação dela; não é uma sexta categoria
-- da tipologia de Gurza Lavalle et al. O significado exato do código está em aberto na #3.
INSERT INTO tipologia (sigla, nome, descricao) VALUES
('99', 'Fora da tipologia', 'Código 99 da planilha da pesquisadora: ato que ela não enquadrou em nenhuma das 5 categorias.')
ON CONFLICT (sigla) DO NOTHING;
