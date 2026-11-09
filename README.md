# Conselhos Vivos

> Quais conselhos nacionais de participação social ainda estão funcionando?

**Documentação:** <https://luidooo.github.io/conselhos-vivos/> — decisões, medições, relatórios de carga e o checklist da E1, num só lugar.

Os conselhos nacionais — CONAMA, CNAS, ConCidades, CONDRAF, CNPIR e dezenas de outros — são órgãos paritários onde sociedade civil e governo decidem juntos sobre política pública. Eles são **autogeridos**: se ninguém convoca a reunião, o conselho simplesmente para de funcionar. Não é extinto, não é noticiado, não aparece em lugar nenhum. Ele só silencia.

Este projeto constrói a plataforma de dados que detecta esse silêncio — lendo o Diário Oficial da União, identificando quem publicou o quê, classificando o tipo de decisão e publicando um indicador de vitalidade por conselho.

## O problema

A professora Lizandra Serafim (UFPB) pesquisa a produção decisória desses conselhos desde 2003. O método é ler o DOU ato por ato, anotar autor e tema, e classificar cada decisão numa tipologia de cinco categorias.

Tudo à mão. Em vinte anos de trabalho, cobriu **cinco conselhos**. Existem entre oitenta e cem.

## A tipologia

Cada ato é classificado em uma destas categorias — é o que o pipeline precisa aprender a fazer:

| Sigla  | Significado |
|--------|-------------|
| `DEF`  | Define a política — diretrizes, regulação, orçamento. Ato vinculante, antes da execução. |
| `FISC` | Fiscaliza — aprova ou reprova contas, responsabiliza, aplica sanção. |
| `GEST` | Gestão administrativa da política já definida. |
| `AUTO` | Autorregulação — o conselho falando de si mesmo: regimento, eleições internas, grupos de trabalho. |
| `IP`   | Gere outras instâncias participativas — conferências, eleições, comissões setoriais. |

Um conselho que só produz `AUTO` está se auto-administrando, não incidindo em política pública. **A distribuição da tipologia ao longo do tempo já é, sozinha, uma medida de saúde.**

## Fontes de dados

| Fonte | O que traz | Acesso |
|---|---|---|
| [INLABS / Imprensa Nacional](https://inlabs.in.gov.br/) | Edições completas do DOU em XML, desde 01/01/2020 | Gratuito, exige cadastro |
| [Dados abertos da Imprensa Nacional](https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados) | O mesmo XML do INLABS, um ZIP por mês e por seção, com o histórico de anos anteriores | Público (CC0), sem login; o mês sai ~2 semanas depois de acabar |
| Planilhas da pesquisadora | 215 atos já classificados à mão, 2003–2020 — nosso *ground truth* | Pública; cópia versionada em `data/raw/` |
| [Brasil Participativo](https://brasilparticipativo.presidencia.gov.br/) | Composição, agenda e reuniões de cada conselho | Público (Decidim) |
| Cadastro de órgãos (SIORG / decretos) | O censo de conselhos existentes — o denominador | Público |

> **Por que o censo não pode sair do DOU:** o DOU só mostra quem publicou. Conselho que não publica há dois anos é precisamente o que queremos detectar. Se o denominador vier do DOU, o conselho morto some da conta e o indicador mente. **A ausência de publicação é o dado mais importante deste projeto.**

## Como rodar

Pré-requisitos: Docker com Compose v2 (`docker compose version`), `make` e `jq`.

```bash
make setup     # cria o .env (se faltar), sobe tudo, aplica as migrações de sql/ e carrega a planilha
```

Sem `make`, o equivalente é `cp .env.example .env && docker compose up -d --wait && bash scripts/migrate.sh && bash scripts/carga.sh`.

Isso sobe:

| Serviço | Onde | Para quê |
|---|---|---|
| `db` — PostgreSQL 16 | `localhost:5432` (host) · `db:5432` (entre containers) | o OLTP de curadoria |
| `pgadmin` — pgAdmin 4 | <http://localhost:5050> | explorar o banco pelo navegador — abre sem login, com o servidor `conselhos-vivos (db)` já cadastrado e conectado |

Os dados ficam no volume `pgdata` e sobrevivem a `docker compose down`.

> **`db` ou `localhost`?** Dentro do compose (pgAdmin, ingestores) o banco é `db:5432`. Fora dele, no seu terminal ou no DBeaver, é `localhost:5432`. Dentro de um container, `localhost` é o próprio container.

```bash
make test      # testes: ingestor em Python, infra, esquema do OLTP, leitura da planilha, identidade dos conselhos, carga e persistência do DOU
make vet-py    # compila src/ e tests/ com aviso virando erro, em container
make test-py-dou # só os testes do ingestor em Python que não usam banco (sem rede)
make test-db-py  # só os testes do ingestor em Python que gravam no banco, em transação desfeita
make extract   # lê as matérias dos ZIPs já baixados de DATA e imprime uma por linha, em JSON
make persist   # grava no banco as matérias dos ZIPs já baixados de DATA; pode rodar de novo, não duplica
make ingest-mensal MES=2026-08  # o mês inteiro dos dados abertos, sem login: baixa e grava as matérias de conselho
make migrate   # aplica as migrações de sql/ que ainda não rodaram
make carga     # carrega os conselhos e a planilha da pesquisadora (idempotente) e atualiza os relatórios
make siorg     # baixa o SIORG (precisa de rede) e atualiza o recorte em data/referencia/
make psql      # abre o psql dentro do container
make docs      # sobe o site de documentação em localhost:5173 (precisa de Node)
make down      # para, mantém os dados
make reset     # APAGA o banco, sobe do zero, migra e carrega a planilha
make pgadmin-reset  # recria o pgAdmin (se mudar POSTGRES_USER ou POSTGRES_DB)
make lake      # extrai do OLTP e atualiza a tabela Delta Lake em data/silver/atos/
make cdc       # aplica no Delta as mudanças de classificacao pendentes no slot lógico (rode make lake antes)
make cdc-demo  # reclassifica um ato e mostra a mudança chegando ao Delta
make cdc-drop  # remove o slot de replicação (slot parado retém WAL)
make           # lista todos os comandos
```

> **Porta 5432 ocupada?** Se você já tem um Postgres instalado na máquina, o `up` falha com `port is already allocated`. Troque `POSTGRES_PORT` no seu `.env` (ex.: `5433`) — só no `.env`, não no `.env.example`.

**O CI roda os testes.** Em todo PR e a cada push no `main`, o workflow `.github/workflows/test.yml` roda `make test` e `make vet-py` num runner sem `.env`, sem volume do banco e sem imagem em cache — a mesma máquina limpa da entrega. Ele também falha se a carga deixar os relatórios versionados diferentes dos que estão no repositório. Nada no CI usa credencial.
>
> **Só na sua máquina.** O banco e o pgAdmin escutam apenas em `127.0.0.1`: ninguém na mesma rede (Wi-Fi da UnB, por exemplo) alcança. Não troque isso — o pgAdmin roda **sem login**.
>
> **Senha com `$`?** No `.env`, coloque o valor entre aspas simples (`POSTGRES_PASSWORD='a$b'`), senão o Compose tenta interpolar. A senha do Postgres não pode ter `:` nem `\` (formato do `pgpass` do pgAdmin).
>
> **Subiu a branch da #2 antes desta correção?** O esquema era criado pelo `initdb`, e o `make migrate` quebra com `relation "orgao" already exists`. Rode `make reset` uma vez (apaga o banco local, que ainda não tem dado real).

**Carga da planilha:** o `make carga` lê `data/raw/Cópia_bancos_dados_Carla_Rocha.xlsx` no serviço `carga` do compose (só biblioteca padrão do Python, sem rede), grava os 215 atos e as classificações da pesquisadora, e reescreve [`docs/carga/relatorio-planilha.md`](docs/carga/relatorio-planilha.md): quantas linhas entraram, quantas foram descartadas e por quê. Rodar de novo não duplica nada nem muda o relatório. Os atos normalizados ficam em `data/interim/planilha/atos.csv`.

**Identidade dos conselhos:** antes dos atos, o `make carga` junta os 125 nomes da aba "Conselhos mapeados no DOU" em **82 órgãos** ([ADR 0004](docs/adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md)). Nomes que só diferem em caixa, acento ou sigla se juntam sozinhos; o resto é decisão registrada em [`data/referencia/conselhos-decisoes.csv`](data/referencia/conselhos-decisoes.csv) (grafia, renomeação com o ato legal, nome, indefinido ou ambíguo), que abre em qualquer planilha. Para corrigir uma decisão, edite o CSV e rode `make carga`. O resultado, com a conta que chega a 82, está em [`docs/carga/relatorio-conselhos.md`](docs/carga/relatorio-conselhos.md).

**Migrações:** cada arquivo `sql/NNN_*.sql` roda uma vez, em ordem e em transação, e fica registrado em `schema_migrations`. Depois de mergeado no `main`, um arquivo de migração **não se edita**: mudança nova vira o próximo número.

## Baixar o DOU

A fonte automática é a mensal: `make ingest-mensal`, [abaixo](#ingerir-um-mes-pelos-dados-abertos). O login do INLABS é recusado a scripts desde 12/10 (`502`, #42), e o cliente dele saiu do repositório junto com o Go ([ADR 0008](docs/adr/0008-unificar-o-pipeline-em-python.md)). O histórico está na tag `e2`.

**O bronze diário continua valendo.** Um ZIP baixado à mão pelo navegador, salvo como `data/bronze/inlabs/AAAA-MM-DD-DO1.zip` ou `AAAA-MM-DD-DO1E.zip`, é lido pelo `make extract DATA=...` e pelo `make persist DATA=...`. O diretório pode trazer também os marcadores que o cliente antigo deixava, e eles continuam sendo respeitados:

| Em `data/bronze/inlabs/` | Quer dizer | `make persist DATA=...` |
|---|---|---|
| `2026-10-02-DO1.zip` | a edição está em disco | grava |
| `2026-10-04-DO1.sem-edicao` | a edição foi buscada e o INLABS respondeu que ela não existe | não grava e não é erro |
| `2026-10-02-DO1.falhou` | a edição foi buscada e não chegou | **sai com erro** |
| nada | ninguém buscou | sai com erro |

**Um `.falhou` continua fazendo o `make persist` e o `make extract` saírem com erro**, mesmo que o ZIP da outra seção esteja em disco: esse ZIP é processado e o código de saída é `1`. Nenhum comando apaga o marcador. Depois de baixar a edição pelo navegador, apague o `.falhou` à mão.

```bash
ls data/bronze/inlabs/*.falhou   # o que falta baixar
```

## Ler as matérias

O `make extract` abre os ZIPs que estão em `data/bronze/inlabs/` para um dia (`DO1` e, se houver, `DO1E`) e imprime **uma matéria por linha, em JSON**, no stdout. Não fala com o banco nem com a rede, e não precisa de credencial. É Python (`python -m dou extract`, em `src/dou/materia.py`), a segunda fatia da migração do ingestor (#51): sobre a Seção 1 de agosto de 2026, a saída é idêntica à do comando em Go nas 8.590 matérias.

```bash
make extract DATA=2026-10-01 > materias.jsonl   # o log e o resumo vão para o stderr
make extract DATA=2026-10-01 | jq -r '.artCategory[-1]' | sort | uniq -c | sort -rn   # quem mais publicou
```

Cada linha traz os atributos do `<article>` (`id`, `idMateria`, `artType`, `pubDate`, `pubName`, `numberPage`, `editionNumber`, `artClass`), os campos do `<body>` (`identifica`, `ementa`, `titulo`, `subTitulo`) e:

- **`artCategory` já partido na hierarquia**, do ministério para baixo. O último nível é o órgão que publicou — o conselho, quando é um. A resolução é só `split('/')`; casar o nome com um dos 82 conselhos é trabalho da persistência (abaixo).
- **`texto`, o `<Texto>` em texto puro:** um parágrafo por linha, entidades HTML decodificadas, células de tabela separadas por ` | `. O HTML como publicado sai com `HTML=1` (`make extract DATA=... HTML=1`) e é a fonte da verdade: as marcas `<p class="assina">` e `<p class="identifica">` só existem nele, e o texto puro é derivado dele sem perda de palavras.

O comando lê **um ZIP por execução**; o `make extract` o roda uma vez por edição do dia, e a segunda roda mesmo se a primeira falhar.

Uma entrada que não é XML — a imagem de uma matéria, ou uma pasta, que não deveria aparecer — é ignorada e logada. Um XML que não lê como matéria (malformado, sem `id`, sem `pubDate`, sem `artCategory`) é logado com o nome do arquivo e o resto do ZIP segue; nesse caso o código de saída é `1`.

## Gravar as matérias no banco

O `make persist` grava no banco os ZIPs de um dia que já estão em `data/bronze/inlabs/`, sem acessar a rede. A extração acontece dentro dele, com o mesmo pacote que o `make extract` usa para imprimir. Para um mês inteiro, use o `make ingest-mensal`, [abaixo](#ingerir-um-mes-pelos-dados-abertos), que grava pelo mesmo `persist`.

```bash
make persist DATA=2026-10-01   # o resumo vai para o stderr
```

**Dado atrasado.** No DOU o atraso é real: a edição extra (`DO1E`) sai depois da edição da manhã, e uma edição pode ser republicada. Reprocessar um ZIP não duplica nada:

- **O que chega numa edição já gravada entra ao regravar.** Uma matéria nova entra com `versao = 1`; uma que voltou diferente entra como versão nova; as demais ficam como estavam.
- **O ato atrasado fica na data em que foi publicado**, e não na data em que chegou: `data_publicacao` vem do `pubDate` da matéria.
- **No Delta, o atrasado cai no ano certo.** O `make lake` relê o OLTP inteiro e grava por `ato_id` numa tabela particionada por `ano = EXTRACT(YEAR FROM data_publicacao)`: um ato publicado em 2024 que só chega em 2026 entra na partição `ano=2024`, e as outras não mudam. [`tests/lake/test_atrasado.sh`](tests/lake/test_atrasado.sh) prova isso de ponta a ponta (persist → lake → DuckDB) e roda no `make test`.
- **Na fonte mensal não há janela:** o ZIP de um mês fechado já traz o `DO1E` de todos os dias, e uma retificação sai como matéria nova, na data em que foi publicada. A janela de dias do `make ingest` (#31) só existia para o cliente do INLABS e saiu com ele ([ADR 0008](docs/adr/0008-unificar-o-pipeline-em-python.md)).

O comando lê **um ZIP por execução**, como o `extract`, e grava tudo numa transação: a edição entra inteira ou não entra. Uma entrada que não lê como matéria é logada e o resto do ZIP é gravado; nesse caso o código de saída é `3` **mesmo com a edição gravada**: é problema do dado, e repetir não resolve, por isso a orquestração não tenta de novo (#84). Um ZIP corrompido também sai com `3`. O código `1` fica para falha de infraestrutura, como um arquivo que não abre ou o banco fora do ar.

**Pode rodar de novo.** Cada matéria é comparada com **todas** as versões dela no banco, no que o DOU publicou (data, ementa e conteúdo). O órgão não entra: ele vem da identidade dos conselhos ([ADR 0004](docs/adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md)), e resolver um nome não é republicação. Comparar só com a última versão faria o mesmo `id` vindo com dois textos (no DO1 e no DO1E, ou em dois dias reprocessados) gerar duas versões a cada execução:

| A matéria | O que acontece | No resumo |
|---|---|---|
| nunca foi vista | entra com `versao = 1` | `gravadas` |
| já está lá, igual a alguma versão | nada é gravado | `inalteradas` |
| já está lá, diferente de todas (a edição foi republicada) | entra com a `versao` seguinte; as anteriores ficam | `versoes-novas` |
| é de órgão desconhecido | fica de fora, e o órgão vai para a fila | `orgao-desconhecido` |
| tem o `id` de outra entrada do mesmo ZIP | fica de fora; vale a primeira | `repetidas` |

Um `id` repetido no mesmo ZIP não derruba as demais matérias e é logado com as duas entradas. Só a primeira é gravada: gravar as duas faria da segunda uma versão nova da primeira, e cada execução seguinte criaria mais duas versões.

Quem grava é o `src/dou/oltp.py` (Python; a terceira fatia da migração do ingestor, #51), em `ato` com `origem = 'DOU'`, insert-only ([ADR 0001](docs/adr/0001-adotar-sistema-de-curadoria-insert-only-como-oltp.md)):

| Coluna de `ato` | De onde vem |
|---|---|
| `id_dou` | o `id` do `<article>`, e não o `idMateria`: é o que a extração já exige em todo XML |
| `versao` | `1` na primeira vez; a seguinte a cada republicação com conteúdo diferente |
| `orgao_id` | o último nível do `artCategory`, casado com um órgão conhecido |
| `data_publicacao` | `pubDate` |
| `ementa` | `<Ementa>`; nula quando vem vazia |
| `conteudo` | o `<Texto>` como publicado, em HTML. Matéria com `<Texto>` vazio é recusada |

**Como o órgão é encontrado.** O nome do último nível do `artCategory` vira a chave normalizada do [ADR 0004](docs/adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md) (sem caixa, acento, espaços repetidos e sigla no fim) e é procurado entre os nomes que os órgãos têm ou já tiveram (`orgao_nome`) e as grafias resolvidas (`orgao_alias` com `status = 'RESOLVIDO'`).

**Órgão desconhecido.** A maioria das matérias de uma edição não é de conselho. A matéria de um órgão que não é um dos conhecidos **não entra em `ato`**, e o nome do órgão entra uma vez em `orgao_alias`, com `fonte = 'DOU'`, `status = 'INDEFINIDO'`, sem órgão e com o `artCategory` inteiro no motivo: é a fila de decisão do ADR 0004. Quando alguém resolver o nome, a matéria é gravada reingerindo o ZIP, que continua em `data/bronze/`. Se a chave casar com **mais de um** órgão, nenhum é escolhido: o nome entra na fila como `AMBIGUO`. Um nome que **já está à espera de decisão**, por qualquer fonte, não ganha uma segunda linha: se a planilha o deixou como `AMBIGUO` ou `INDEFINIDO`, o status e o motivo dela continuam valendo, e a matéria fica de fora até alguém decidir.

A chave do nome é calculada num lugar só, `chave()` em `src/conselhos/identidade.py`, usada pela carga e pela ingestão. `tests/conselhos/chaves.tsv` guarda os 169 nomes e as chaves com que `orgao_alias.chave` foi gravada: mudar a função exige migrar a coluna, e o teste avisa.

A classificação não é tocada: continua da planilha e da curadoria ([ADR 0003](docs/adr/0003-carregar-a-planilha-como-rotulo-da-curadoria.md)).

## Ingerir um mês pelos dados abertos

O `make ingest-mensal` leva o DOU de um **mês inteiro** até o banco, a partir dos [dados abertos da Imprensa Nacional](https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados): público, sem login e sem credencial no `.env`. O ZIP mensal traz o mesmo XML `<article>` do INLABS, com o `DO1` e o `DO1E` de todos os dias do mês, e é gravado pelo mesmo `persist`.

```bash
make ingest-mensal MES=2026-08   # baixa a Seção 1 de agosto e grava as matérias de conselho em ato
make fetch-mensal MES=2026-08    # só baixa, para data/bronze/dados-abertos/S01082026.zip
make persist-mensal MES=2026-08  # só grava o ZIP já baixado, sem acessar a Imprensa Nacional
```

- **O ZIP fica com o nome que a Imprensa Nacional dá** (`S01MMAAAA.zip`): a Seção 1 de agosto de 2026 é `S01082026.zip`, com cerca de 50 MB e 8.600 matérias; a de setembro tem 286 MB e 8.900.
- **O `fetch-mensal` é Python** (`python -m dou fetch-mensal`, em `src/dou/`), a primeira fatia da migração do ingestor (#51): o download é byte a byte o mesmo que o comando em Go fazia.
- **Mês já em disco não é baixado de novo.** O arquivo de um mês fechado não muda, e o nome só existe depois que o ZIP chegou inteiro. Rodar o `make ingest-mensal` de novo não baixa nem duplica nada; o `persist` compara cada matéria com todas as versões, como no `make persist`.
- **Mês ainda não publicado é erro**, com código de saída `3`, e nada é gravado. A agenda do Dagster tenta de novo no dia seguinte, até o dia 28 (#83). O mês sai cerca de duas semanas depois de acabar: setembro de 2026 apareceu em 13/10. Para o dia de hoje, só o ZIP baixado à mão do INLABS.
- **Como o link é encontrado.** O endereço de cada ZIP leva um UUID que não dá para montar; o `fetch-mensal` lê a página da base de dados com `ano` e `mes` e pega o link do `S01MMAAAA.zip`. Só aceita link para o próprio `www.in.gov.br`. O pedido vai com `Accept: */*`: sem esse cabeçalho, o site responde `403`.

Para vários meses, um laço no shell:

```bash
for m in 2026-06 2026-07 2026-08; do make ingest-mensal MES=$m; done
```

## Fluxo de mudanças do OLTP ao Delta (CDC)

O Postgres sobe com `wal_level=logical` e um slot de replicação lógica (`conselhos_lake`) guarda as mudanças de `classificacao`; `make cdc` as aplica na tabela Delta ([ADR 0007](docs/adr/0007-propagar-mudancas-por-slot-de-replicacao-logica.md)). Sem Kafka. Quem já possui o banco rodando precisa recriar o container `db` para ativar o nível lógico (`make up` faz isso automaticamente; os dados persistem no volume).

**Cobertura do CDC:** o slot lógico monitora exclusivamente `INSERT` na tabela `classificacao` (as reclassificações de curadoria). Mudanças em outras tabelas — como atos novos ingeridos do DOU (`ato`), novas versões de matérias (`versao`) ou alterações em nomes e aliases de conselhos (`orgao_nome`, `orgao_alias`) — continuam sendo propagadas para a camada Delta pela recarga periódica via `make lake`.

Para ver uma mudança atravessando o fluxo:

```bash
make up                      # recria o db com wal_level=logical se ainda estava com replica
make migrate && make carga   # se o banco ainda estiver vazio
make cdc-demo
```

O `make cdc-demo` roda `make lake` (carga completa) e `make cdc` (cria o slot), mostra a tipologia de um ato no Delta, **reclassifica** o ato (um `INSERT` novo em `classificacao`, que é insert-only), consome o slot, mostra a mudança no Delta e, por fim, **restaura a tipologia original** com novo `INSERT`, provando o ciclo completo sem alterar a distribuição analítica real. `ATO_ID=123 make cdc-demo` escolhe o ato.

Para testar a tolerância a falhas e a semântica de entrega (queda simulada do consumidor pós-gravação no Delta Lake):

```bash
make cdc-chaos
```

O `make cdc-chaos` interrompe abruptamente o consumidor logo após aplicar a alteração no Delta Lake e antes de avançar o slot lógico no PostgreSQL. Ao reexecutar, o consumidor reprocessa os eventos e o `MERGE` idempotente garante que nenhuma linha duplique, mantendo a contagem total estritamente inalterada.

Dia a dia: `make lake` uma vez, depois `make cdc` sempre que quiser aplicar as reclassificações pendentes (pode rodar de novo, não duplica).

> **Slot parado retém WAL.** Se for abandonar o fluxo, rode `make cdc-drop`, senão o disco do banco cresce. Mudanças anteriores à criação do slot só entram com `make lake`.
>
> **Curadoria insert-only mantida.** A reclassificação da demonstração permanece registrada no histórico do banco (ADR 0001), sob revisor dedicado. Os testes isolam os revisores e não exigem `make reset` após demonstrar.

## Camada analítica e painel (E3)

A gold é um DuckDB em `data/gold/conselhos.duckdb`, gerado pelo dbt a partir da silver e do OLTP ([ADR 0009](docs/adr/0009-modelar-a-gold-em-estrela-com-dbt-e-orquestrar-com-dagster.md)). Uma estrela: `dim_conselho` (variação lenta dos nomes), `fct_ato` (uma linha por matéria) e `fct_conselho_mes` (conselho × mês, com zeros), mais a `mart_vitalidade`, que responde à pergunta da E1, e a `freshness_vitalidade`, com o SLA.

```bash
make lake        # OLTP → silver (Delta)
make mencoes     # menções aos conselhos em atos de outros órgãos, dos ZIPs já no bronze → silver
make gold        # silver + OLTP → gold, com todos os testes do dbt
make gold-docs   # catálogo e linhagem do dbt em dbt/target/
make painel      # o painel em http://127.0.0.1:8501
```

A orquestração é o Dagster, num job mensal com retry, backfill e agenda do dia 15 ao 28:

```bash
make orquestrador                           # a interface em http://127.0.0.1:3000
make demo-backfill DE=2026-07 ATE=2026-09   # baixa só o que falta; a 2ª rodada não grava nada
make demo-retry                             # para o Postgres por ~1 min e mostra o retry recuperando
make demo-falhas                            # falha de dado sem retry, falha de rede com retry, teste do dbt com nome
```

As provas ficam em `docs/adr/medicoes/0009-gold/`. O SLA: o mês M está na gold até o dia 20 do mês M+1.

## Estrutura

```
sql/            DDL versionado do banco
src/            ingestão (src/dou/), parsing e transformações, tudo em Python
docs/adr/       decisões de arquitetura (o porquê de cada escolha)
docs/diario/    registro semanal do andamento
docs/carga/     relatórios da carga (gerados pelo make carga, versionados)
data/           dados locais (não versionados), exceto a planilha em raw/ e referencia/
data/referencia/ decisões de identidade dos conselhos e recorte do SIORG (versionados)
data/silver/    camada analítica em Delta Lake (não versionada localmente)
tests/          testes do pipeline
site/           site de documentação (VitePress); as páginas são os .md do repositório
```

## Decisões de arquitetura

As decisões relevantes ficam registradas em [`docs/adr/`](docs/adr/), com contexto, alternativas consideradas e consequências aceitas. Se você quer entender *por que* o projeto é assim, comece por ali.

## Créditos

Bancos de dados de produção decisória: SERAFIM, Lizandra e colaboradores (UFPB / Cebrap, 2020–2026).

Tipologia de análise: GURZA LAVALLE, A.; VOIGT, J.; SERAFIM, L. *O que fazem os conselhos e quando o fazem?* Dados, v. 59, n. 3, 2016 — adaptada por GURZA LAVALLE, A.; GUICHENEY, H.; VELLO, B.; RODRIGUES, F. (CEM, 2018).

Referência arquitetural: [GovHub BR](https://gov-hub.io/).

---

Projeto da disciplina de Banco de Dados 2 — FCTE / UnB, 2026/2.
