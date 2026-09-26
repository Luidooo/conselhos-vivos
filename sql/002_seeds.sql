-- Carga inicial das 5 tipologias de pesquisa
INSERT INTO tipologia (sigla, nome, descricao) VALUES
('DEF',  'Define a política',        'Diretrizes, regulação, orçamento. Ato vinculante, antes da execução.'),
('FISC', 'Fiscaliza',                'Aprova ou reprova contas, responsabiliza, aplica sanção.'),
('GEST', 'Gestão administrativa',    'Gestão administrativa da política já definida.'),
('AUTO', 'Autorregulação',           'O conselho falando de si mesmo: regimento, eleições internas, grupos de trabalho.'),
('IP',   'Instâncias participativas','Gere outras instâncias participativas: conferências, eleições, comissões setoriais.')
ON CONFLICT (sigla) DO UPDATE SET nome = EXCLUDED.nome, descricao = EXCLUDED.descricao;

-- Carga de revisores padrão para permitir testes imediatos
INSERT INTO revisor (nome, tipo, email) VALUES
('Pipeline Classificador v1', 'PIPELINE', 'pipeline-v1@sistema.local'),
('Pesquisadora Principal', 'HUMANO', 'curadoria@pesquisa.local')
ON CONFLICT (email) DO NOTHING;