# Plano: menções aos conselhos em atos de outros órgãos

**Objetivo.** Enriquecer a gold com um segundo sinal de vida de cada conselho: as matérias da Seção 1 do DOU publicadas por **outro** órgão que citam o conselho, como a homologação de um parecer, a renovação da composição, a aprovação do regimento ou a estrutura regimental que o lista. A ingestão é automática, no mesmo asset mensal do Dagster, e lê o ZIP que já está no bronze.

**Medição que motivou (09/11/2026, bronze de julho a outubro de 2026, só leitura):**
- **Volume:** 34.828 matérias lidas. 317 foram publicadas pelos próprios conselhos e já estão no fato. Outras 429, publicadas por outros órgãos, citam algum conselho, e cobrem 40 dos 59.
- **Ruído:** com o nome procurado no texto inteiro, ele aparece em matérias que só citam o conselho de passagem.

Daí a regra conservadora da Tarefa 1.

**Fora deste plano:**
- mudar a regra de "ativo" da vitalidade, que segue para a squad decidir: as menções entram como coluna ao lado;
- a lista de exclusões do ADR 0010, que precisa de decisão da squad. CNPq, CONTRAN e o Conselho Curador do FGTS aparecem entre os mais citados.

## Tarefas

1. **Extração pura (`src/mencoes/`).**
   - Normalizar os nomes.
   - Casar os nomes de todos os órgãos que começam com "Conselho" no título, na ementa e no primeiro parágrafo do texto.
   - Descartar a matéria publicada pelo próprio conselho citado.
   - Classificar o assunto pela ementa e pelo primeiro parágrafo: homologação, composição, regimento, estrutura, criação, extinção ou outro.
   - Testes unitários sem banco e sem Delta.
   - Medir no bronze a regra conservadora contra a busca no texto inteiro.
2. **Gravação na silver.**
   - `python -m mencoes ZIP...` lê os nomes do OLTP e grava `data/silver/mencoes` em Delta.
   - A tabela é particionada por ano, com `MERGE` idempotente na chave (`id_dou`, `orgao_id`).
   - Teste: a segunda execução não grava nada.
3. **Dagster.**
   - Asset `silver/mencoes`, particionado por mês, depois do `atos_do_mes`.
   - A gold passa a depender dele pela fonte do dbt.
   - `dagster definitions validate`.
4. **dbt.**
   - Fonte `silver.mencoes`, `stg_mencoes` e `fct_mencao`, com uma linha por matéria × conselho citado, no escopo da `dim_conselho`.
   - Testes de unicidade, relacionamento, valores aceitos e um teste unitário.
   - A `mart_vitalidade` ganha `mencoes_no_periodo` e `ultimo_mes_citado`, na mesma janela do DOU.
5. **Painel.** A tabela por conselho ganha "Citado por outros órgãos", com testes.
6. **Carga dos quatro meses.** Os ZIPs de julho a outubro, que já estão no bronze, passam pelo `mencoes` e depois pelo `make gold`. Não roda o `make lake`, para não mudar a silver dos atos antes da squad decidir a regra da vitalidade. A prova vai para `docs/adr/medicoes/0009-gold/`.
7. **Documentação.** ADR 0009 (o enriquecimento e os gatilhos: Seção 2, SIORG completo, Brasil Participativo e IBGE), página da E3, README e `AI-USAGE.md`.
