-- Carga inicial das 5 tipologias de pesquisa
INSERT INTO tipologia (sigla, nome, descricao) VALUES
('DEF', 'Definição e Regulamentação', 'Atos que estabelecem normas gerais, diretrizes e regulamentos sobre políticas públicas.'),
('FISC', 'Fiscalização e Controle', 'Atos voltados à fiscalização de programas, monitoramento e aplicação de sanções.'),
('GEST', 'Gestão Interna', 'Atos relativos à organização operacional do conselho, regimento interno, orçamento e pessoal.'),
('AUTO', 'Autorização e Deliberação Específica', 'Decisões colegiadas sobre concessões, credenciamentos ou aprovações pontuais.'),
('IP', 'Informação e Publicidade', 'Comunicações públicas, relatórios, atas e notas de divulgação.')
ON CONFLICT (sigla) DO NOTHING;

-- Carga de revisores padrão para permitir testes imediatos
INSERT INTO revisor (nome, tipo, email) VALUES
('Pipeline Classificador v1', 'PIPELINE', 'pipeline-v1@sistema.local'),
('Pesquisadora Principal', 'HUMANO', 'curadoria@pesquisa.local')
ON CONFLICT (email) DO NOTHING;