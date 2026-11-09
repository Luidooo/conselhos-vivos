# 0009 — Modelar a gold em estrela com dbt sobre DuckDB e orquestrar com Dagster

- **Status:** proposto
- **Data:** 2026-11-09
- **Decisores:** a confirmar no PR — Luis (@Luidooo), Bruno (@BrunoBReis), Moura (@thegm445), Iago (@iagorrr), Luiza (@LuizaMaluf)

## Contexto

A E2 terminou com a silver pronta: uma tabela Delta consolidada dos atos (ADR 0006), alimentada do OLTP por carga completa e por CDC lógico (ADR 0007). A E3 pede a camada de consumo em cima dela: um modelo dimensional com fato e dimensão, grão declarado e variação lenta; transformações em camadas com testes que pegam erro silencioso; orquestração agendada com retry e backfill; freshness com SLA; e um painel que responda à pergunta da E1: **quais conselhos nacionais de participação social ainda estão funcionando?**

As restrições vêm das entregas anteriores. Tudo roda em containers na máquina de quem avalia, sem serviço pago e sem nada exposto para fora do loopback (diário de 25/09). A fonte é uma só, o DOU mais a planilha da pesquisadora, e o esquema da origem é estável. O volume é pequeno: 82 órgãos, 59 conselhos no escopo do ADR 0010 e centenas de atos por mês.

## Alternativas consideradas

### Modelagem

- **A. One big table:** uma tabela desnormalizada por ato. Simples, mas a pergunta da E1 se mede pela **ausência**: o conselho que ficou meses sem publicar. Uma tabela por ato não tem linha para o mês sem ato, e o painel teria de gerar os zeros em tempo de leitura, sem teste. Também não há onde pendurar a vigência dos nomes sem repetir a SCD em cada linha.
- **B. Data Vault:** hubs, links e satélites. Paga-se quando há várias fontes e esquema instável. Aqui a fonte é uma e o esquema é nosso (ADR 0004): a camada extra viraria cerimônia.
- **C. Estrela (escolhida):** uma dimensão SCD tipo 2 (`dim_conselho`, uma linha por nome com vigência) e dois fatos: `fct_ato`, uma linha por matéria, e `fct_conselho_mes`, conselho × mês **com zeros**. A mart `mart_vitalidade` responde à pergunta, e `freshness_vitalidade` expõe o SLA.

### Ferramenta de transformação

- **dbt-core com dbt-duckdb (escolhida):** lê a silver por `delta_scan` e o OLTP por `ATTACH ... (TYPE postgres, READ_ONLY)` sem subir servidor nenhum, no mesmo DuckDB da E2. Os testes (`data_tests`, singulares e unitários) são a resposta direta ao critério de pegar erro silencioso, e o `dbt docs generate` (`make gold-docs`) dá o catálogo que a E4 vai publicar.
- **SQLMesh:** traz intervalos incrementais e ambientes virtuais de dados, que este volume não precisa; a squad não o conhece e a E3 tem duas semanas. Fica como alternativa real para quando o incremental importar.

### Orquestração

- **Opção nula, cron com `make`, levada a sério:** uma linha de crontab rodando `make ingest-mensal && make lake && make gold` no dia 15 cobre o caminho feliz. O que ela não dá, e teríamos de escrever à mão: o **retry** com espera (um laço com `sleep` e contador no shell), o **backfill** por mês com registro do que já rodou (um arquivo de estado caseiro), a distinção entre falha de dado e de infraestrutura (#83, #84), um lugar onde ver o que rodou e por que falhou, e a trava de um run por vez. Cada um é pequeno; juntos são um orquestrador caseiro sem interface.
- **Dagster (escolhida):** assets particionados por mês dão o backfill de graça (`make demo-backfill`), o `RetryPolicy` dá o retry demonstrável (`make demo-retry`), o `Failure(allow_retries=False)` separa a falha de dado (#84), a agenda roda do dia 15 ao 28 pulando mês já carregado (#83), e o log de eventos de cada run alimenta as provas (`scripts/eventos_do_run.sh`). Roda no mesmo molde de containers do projeto, em `127.0.0.1:3000`.
- **Airflow/Prefect:** mais pesados (scheduler + banco próprio no caso do Airflow) sem nada a mais que este caso use.

## Decisões

1. **Estrela com dois fatos.** `fct_ato` guarda o detalhe (uma linha por matéria, a versão mais recente, ligada ao nome da época por `asof join`: o último nome que começou até a data; antes do primeiro nome, fica com o mais antigo e `nome_aproximado = true`). `fct_conselho_mes` materializa o zero do mês sem ato. A planilha (2003–2020) entra no `fct_ato`, mas não estica o intervalo mensal: a vitalidade se mede só na janela coberta pelo DOU.
2. **Escopo da dimensão é o ADR 0010:** órgão com nome começando com "Conselho", menos a seed de exclusões. Atos de órgãos fora do escopo ficam fora do fato, contados em `fct_ato-fora-do-escopo.txt`.
3. **dbt em camadas** (staging em view, marts em tabela, `freshness_vitalidade` em view para o `current_date` valer na leitura), com testes de schema, relacionamento, volume, distribuição, singulares e unitários; `make gold` roda tudo.
4. **Dagster com um run por vez** (`dagster/dagster.yaml`, fila com `max_concurrent_runs: 1`), porque a silver (Delta) e a gold (DuckDB, um escritor) não aguentam runs paralelos.
5. **SLA declarado:** o mês M está na gold até o dia 20 do mês M+1. A agenda tenta do dia 15 ao 28; `sla_vitalidade` avisa sem travar o build.

## Medição e verificação

Tudo em `docs/adr/medicoes/0009-gold/`, gerado por script ou pelos alvos do Makefile; banco com DOU de julho a setembro de 2026 mais a planilha.

- **Granularidade (`granularidade.txt`):** `fct_ato` 458 linhas; `fct_conselho_mes` 177 (59 conselhos × 3 meses); a grão diária hipotética daria 5.428 linhas, 30 vezes o fato mensal, sem pergunta que a use. A grão por matéria guarda o detalhe; a mensal, com zeros, é a que responde à pergunta.
- **Variação lenta (`dim_conselho-renomeados.txt`):** CNDPI, CNDM e CNDH com dois nomes e um só `atual`; 62 linhas para 59 conselhos.
- **Testes que pegam erro silencioso (`teste-distribuicao-pega-o-mes.txt`):** com agosto tirado (`--vars excluir_mes`), `distribuicao_mes_sem_nenhum_ato` falha apontando `2026-08-01`; o `make gold` seguinte volta a passar. `teste-distribuicao-fora-da-tipologia.txt` mostra o teste da fração fora da tipologia disparando (limite rebaixado a 0 para a prova; hoje só a planilha é classificada).
- **Vitalidade (`vitalidade-por-situacao.txt`):** 26 ativos, 33 sem ato no período coberto, 59 no total. O limite de 3 meses é provisório, à espera da pesquisadora; com outubro na silver, a cobertura passa de 3 meses e os 33 viram "em silêncio" pela regra.
- **Orquestração:** grafo da ingestão à gold (`grafo-dagster.jpg`), agenda ligada às 6h de Brasília (`agenda-dagster.jpg`), retry com causa (`retry-2026-08-20261108T231400Z.txt`: primeira tentativa cai com o banco parado, `STEP_UP_FOR_RETRY`, recupera em 36 s), backfill de três meses idempotente (`backfill-*.txt`: segunda rodada com `gravadas=0`; os dois arquivos de 08/11 foram reconstruídos dos logs dos runs, com cabeçalho dizendo isso, e o de 09/11 saiu inteiro do script), e as falhas separadas por tipo (`falhas-*.txt`: mês não publicado e ZIP inválido sem retry; lake e dbt com retry e a causa real; teste do dbt com o nome na prova).
- **SLA (`sla-vitalidade-avisa.txt`):** com setembro tirado, `sla_vitalidade` dá `WARN 1` e o build termina com `ERROR=0`.
- **Plano de execução (`explain-antes.txt`, `resultado.md`, #74):** a extração do lake mede 22,8 ms e 1.429 buffers; o nó mais caro é o `Seq Scan` em `classificacao` (933 buffers, 65%). O índice candidato não teve ganho neste volume e **não entrou**; remedir com o backfill histórico.
- **Painel (`painel.png`):** título com a pergunta da E1, período coberto, SLA, situação por conselho com a marca da pesquisadora, atos por mês e tipologias; `make gold` passa com o painel aberto.
- **Catálogo:** `make gold-docs` gera `dbt/target/index.html` e `catalog.json`; publicar é da E4.

## Consequências

**Ganhamos:** a pergunta da E1 respondida por uma tabela testada, com o zero materializado e o SLA vigiado; provas reproduzíveis por script; a pilha inteira nos containers de sempre, sem servidor novo além do Dagster local.

**Perdemos / limites conhecidos:**
- A silver e a gold são recalculadas inteiras a cada run (`shortcut:` no grafo); vale enquanto o `dbt build` fica em segundos.
- "Carregado" para a agenda é o `atos_do_mes` materializado: um mês com falha de dado é repetido até o dia 28, e uma falha só na gold não reabre o mês.
- O teste de distribuição só pega buraco **no meio** da série; a ponta é papel do freshness.
- Um teste de dados do dbt que falha ainda passa pelo retry do asset `gold`, como se fosse falha de rede.
- O limite de 3 meses da vitalidade e o escopo do ADR 0010 seguem pendentes de confirmação da squad e da pesquisadora.

## Gatilho de revisão

- **Uma segunda fonte** (por exemplo, o Brasil Participativo) reabre a discussão do Data Vault e do incremental (SQLMesh).
- **`dbt build` acima de cinco minutos**, por exemplo com o backfill de 2003 a 2020, pede partição de verdade na silver e na gold e o fim do recálculo completo.
- **A pesquisadora definir o limite de meses** troca o `meses_ativo` e o texto do painel.
- **A squad aceitar o ADR 0010** (ou mudá-lo) muda o denominador de tudo que conta conselhos.
