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

Depois, preencha as credenciais do INLABS no `.env`. Sem `make`, o equivalente é `cp .env.example .env && docker compose up -d --wait && bash scripts/migrate.sh && bash scripts/carga.sh`.

Isso sobe:

| Serviço | Onde | Para quê |
|---|---|---|
| `db` — PostgreSQL 16 | `localhost:5432` (host) · `db:5432` (entre containers) | o OLTP de curadoria |
| `pgadmin` — pgAdmin 4 | <http://localhost:5050> | explorar o banco pelo navegador — abre sem login, com o servidor `conselhos-vivos (db)` já cadastrado e conectado |

Os dados ficam no volume `pgdata` e sobrevivem a `docker compose down`.

> **`db` ou `localhost`?** Dentro do compose (pgAdmin, ingestores) o banco é `db:5432`. Fora dele, no seu terminal ou no DBeaver, é `localhost:5432`. Dentro de um container, `localhost` é o próprio container.

```bash
make test      # testes: Go do ingestor, infra, esquema do OLTP, leitura da planilha, identidade dos conselhos, carga e persistência do DOU
make test-go   # só os testes do ingestor em Go, em container (sem rede, sem credencial)
make test-db-go  # só os testes do ingestor que gravam no banco, em transação desfeita (banco no ar e migrado)
make test-py-dou # só os testes do ingestor em Python que não usam banco (sem rede)
make test-db-py  # só os testes do ingestor em Python que gravam no banco, em transação desfeita
make fetch     # baixa as edições do DOU de hoje em Brasília; DATA=AAAA-MM-DD para outro dia
make extract   # lê as matérias dos ZIPs já baixados de DATA e imprime uma por linha, em JSON
make persist   # grava no banco as matérias dos ZIPs já baixados de DATA; pode rodar de novo, não duplica
make ingest    # fetch e persist dos 7 dias que terminam em DATA (JANELA=N muda a janela): baixa e grava as matérias de conselho
make ingest-dia  # o mesmo para um dia só, sem janela
make janela    # lista os dias que o make ingest reprocessa
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

**O CI roda os testes.** Em todo PR e a cada push no `main`, o workflow `.github/workflows/test.yml` roda `make test` e `make vet-go` num runner sem `.env`, sem volume do banco e sem imagem em cache — a mesma máquina limpa da entrega. Ele também falha se a carga deixar os relatórios versionados diferentes dos que estão no repositório. Nada no CI usa credencial do INLABS.
>
> **Só na sua máquina.** O banco e o pgAdmin escutam apenas em `127.0.0.1`: ninguém na mesma rede (Wi-Fi da UnB, por exemplo) alcança. Não troque isso — o pgAdmin roda **sem login**.
>
> **Senha com `$`?** No `.env`, coloque o valor entre aspas simples (`INLABS_SENHA='a$b'`), senão o Compose tenta interpolar. A senha do Postgres não pode ter `:` nem `\` (formato do `pgpass` do pgAdmin).
>
> **Subiu a branch da #2 antes desta correção?** O esquema era criado pelo `initdb`, e o `make migrate` quebra com `relation "orgao" already exists`. Rode `make reset` uma vez (apaga o banco local, que ainda não tem dado real).

**Carga da planilha:** o `make carga` lê `data/raw/Cópia_bancos_dados_Carla_Rocha.xlsx` no serviço `carga` do compose (só biblioteca padrão do Python, sem rede), grava os 215 atos e as classificações da pesquisadora, e reescreve [`docs/carga/relatorio-planilha.md`](docs/carga/relatorio-planilha.md): quantas linhas entraram, quantas foram descartadas e por quê. Rodar de novo não duplica nada nem muda o relatório. Os atos normalizados ficam em `data/interim/planilha/atos.csv`.

**Identidade dos conselhos:** antes dos atos, o `make carga` junta os 125 nomes da aba "Conselhos mapeados no DOU" em **82 órgãos** ([ADR 0004](docs/adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md)). Nomes que só diferem em caixa, acento ou sigla se juntam sozinhos; o resto é decisão registrada em [`data/referencia/conselhos-decisoes.csv`](data/referencia/conselhos-decisoes.csv) (grafia, renomeação com o ato legal, nome, indefinido ou ambíguo), que abre em qualquer planilha. Para corrigir uma decisão, edite o CSV e rode `make carga`. O resultado, com a conta que chega a 82, está em [`docs/carga/relatorio-conselhos.md`](docs/carga/relatorio-conselhos.md).

**Migrações:** cada arquivo `sql/NNN_*.sql` roda uma vez, em ordem e em transação, e fica registrado em `schema_migrations`. Depois de mergeado no `main`, um arquivo de migração **não se edita**: mudança nova vira o próximo número.

## Baixar o DOU

O `make fetch` baixa do INLABS as edições da Seção 1 — `DO1` e a edição extra `DO1E` — de um dia, e grava os ZIPs em `data/bronze/inlabs/` (o `make fetch` cria o diretório; o comando Go, chamado direto, exige que ele exista). Precisa das credenciais do INLABS no `.env` (cadastro gratuito em <https://inlabs.in.gov.br/>).

```bash
make fetch                    # hoje, no horário de Brasília
make fetch DATA=2026-10-01    # um dia específico
```

Um arquivo só aparece com o nome final quando o conteúdo é um ZIP que abre: sessão expirada devolve a página de login.

**Não há retomada.** Cada execução baixa o dia de novo, sobrescrevendo o que estiver em disco. Para vários dias:

```bash
for d in 2026-10-01 2026-10-02 2026-10-03; do make fetch DATA=$d; done
```

**O diretório é o registro do dia.** No lugar do ZIP que não veio, o `fetch` deixa um arquivo vazio com o mesmo nome e outra extensão. Assim `data/bronze/inlabs/` diz o que foi pedido ao INLABS e o que ele respondeu, por data e por seção:

| Em `data/bronze/inlabs/` | Quer dizer |
|---|---|
| `2026-10-02-DO1.zip` | houve edição, e ela foi baixada |
| `2026-10-04-DO1.sem-edicao` | a edição foi buscada e o INLABS respondeu que ela não existe (domingo, feriado, dia sem edição extra)¹ |
| `2026-10-02-DO1.falhou` | a edição foi buscada e não chegou: é a que falta buscar de novo |
| nada | ninguém buscou |

```bash
ls data/bronze/inlabs/*.falhou   # o que falta buscar de novo
```

Para cada edição há no máximo um dos três arquivos, e ele diz o que a última busca encontrou:

- **Um ZIP que chega apaga o marcador.** A edição extra sai à tarde, depois de uma busca de manhã; e a edição que falhou ontem e chega hoje deixa de ser falha.
- **Um ZIP em disco vence.** Nem um "não existe" nem uma falha posteriores desmentem uma edição já baixada.
- **A falha é buscada de novo quando o dia roda de novo**: `make fetch DATA=...` rebaixa o dia inteiro, e não só o que falhou. Nada refaz sozinho um dia que falhou.
- **Execução interrompida não deixa registro.** Uma busca cancelada ou que estourou o prazo da execução não foi recusada, só não foi esperada.

¹ "Respondeu que não existe" é o `404`, e essa leitura **ainda não foi conferida contra o INLABS**: não se sabe o que ele devolve em manutenção nem para uma data sem edição com sessão válida. Até lá, um `.sem-edicao` num dia útil merece desconfiança.

O registro fica no bronze, e não numa tabela do banco, para o `fetch` continuar sem falar com o banco: ele roda sem o Postgres no ar. O custo é que o registro não é consultável por SQL.

O código de saída diz o que aconteceu: `0` nada falhou, `1` a execução foi abortada ou alguma seção falhou, `2` erro de uso (`-date` ausente ou malformado). Uma data que o INLABS não pode ter — futura, ou anterior a 2020-01-01, que é desde quando ele serve — aborta a execução com `1` e nenhuma requisição: é regra do INLABS, e não do argumento.

## Ler as matérias

O `make extract` abre os ZIPs que o `make fetch` deixou em `data/bronze/inlabs/` para um dia (`DO1` e, se houver, `DO1E`) e imprime **uma matéria por linha, em JSON**, no stdout. Não fala com o banco nem com a rede, e não precisa de credencial.

```bash
make extract DATA=2026-10-01 > materias.jsonl   # o log e o resumo vão para o stderr
make extract DATA=2026-10-01 | jq -r '.artCategory[-1]' | sort | uniq -c | sort -rn   # quem mais publicou
```

Cada linha traz os atributos do `<article>` (`id`, `idMateria`, `artType`, `pubDate`, `pubName`, `numberPage`, `editionNumber`, `artClass`), os campos do `<body>` (`identifica`, `ementa`, `titulo`, `subTitulo`) e:

- **`artCategory` já partido na hierarquia**, do ministério para baixo. O último nível é o órgão que publicou — o conselho, quando é um. A resolução é só `split('/')`; casar o nome com um dos 82 conselhos é trabalho da persistência (abaixo).
- **`texto`, o `<Texto>` em texto puro:** um parágrafo por linha, entidades HTML decodificadas, células de tabela separadas por ` | `. O HTML como publicado sai com `HTML=1` (`make extract DATA=... HTML=1`) e é a fonte da verdade: as marcas `<p class="assina">` e `<p class="identifica">` só existem nele, e o texto puro é derivado dele sem perda de palavras.

O comando Go lê **um ZIP por execução**; o `make extract` o roda uma vez por edição do dia, e a segunda roda mesmo se a primeira falhar.

Uma entrada que não é XML — a imagem de uma matéria, ou uma pasta, que não deveria aparecer — é ignorada e logada. Um XML que não lê como matéria (malformado, sem `id`, sem `pubDate`, sem `artCategory`) é logado com o nome do arquivo e o resto do ZIP segue; nesse caso o código de saída é `1`.

## Gravar as matérias no banco

O `make ingest` leva o DOU do INLABS até o banco, de ponta a ponta:

```bash
make ingest DATA=2026-10-11            # os 7 dias que terminam em DATA: de 05/10 a 11/10
make ingest DATA=2026-10-11 JANELA=1   # só o dia
make ingest-dia DATA=2026-10-11        # o mesmo que JANELA=1
```

Para cada dia, do mais antigo para o mais novo, ele encadeia o `make fetch` e o `make persist` (é o `make ingest-dia`). Se o `fetch` falha numa seção, o que foi baixado é gravado mesmo assim, e o dia conta como falho. A extração acontece dentro do `persist`, com o mesmo pacote que o `make extract` usa para imprimir. Um dia que o `fetch` marcou como sem edição não é erro, e nada é gravado; um dia cuja busca falhou é, em qualquer das duas seções. Um dia que falha não impede os seguintes, e o `make` sai com erro se qualquer um falhou.

**Dado atrasado.** No DOU o atraso é real: a edição extra (`DO1E`) sai depois da busca da manhã, e o INLABS pode republicar uma edição. Por isso cada `make ingest` busca e grava de novo os últimos `JANELA` dias, e não só o dia pedido:

- **O que chega dentro da janela entra sozinho.** Uma matéria nova numa edição já gravada entra com `versao = 1`; uma que voltou diferente entra como versão nova; as demais ficam como estavam. Reprocessar não duplica.
- **O ato atrasado fica na data em que foi publicado**, e não na data em que chegou: `data_publicacao` vem do `pubDate` da matéria.
- **Um dia cuja busca falhou é buscado de novo** na próxima execução, enquanto estiver na janela.
- **O que chega depois da janela não entra sozinho, e nada avisa.** Para trazê-lo, rode o dia à mão (`make ingest-dia DATA=...`) ou uma janela maior (`JANELA=30`). O bronze guarda só a última versão baixada de cada edição.
- **A janela é de dias do INLABS**, e o login automático do INLABS hoje é recusado (#42): ela só regrava os dias cujos ZIPs já estão em `data/bronze/inlabs/`. Na fonte mensal (`make ingest-mensal`) não há janela: o ZIP de um mês fechado já traz o `DO1E` de todos os dias, e uma retificação sai como matéria nova, na data em que foi publicada.

A janela padrão é de **7 dias**, um valor provisório: cobre o fim de semana e um feriado emendado, e custa 14 edições pedidas ao INLABS por execução (DO1 e DO1E de cada dia). Ninguém mediu ainda com que atraso o INLABS republica uma edição; a squad decide o valor na #31. `make janela DATA=... JANELA=...` lista os dias sem baixar nada.

O `make persist` sozinho grava os ZIPs que já estão em `data/bronze/inlabs/`, sem acessar o INLABS:

```bash
make persist DATA=2026-10-01   # o resumo vai para o stderr
```

O comando Go lê **um ZIP por execução**, como o `extract`, e grava tudo numa transação: a edição entra inteira ou não entra. Uma entrada que não lê como matéria é logada e o resto do ZIP é gravado; nesse caso o código de saída é `1` **mesmo com a edição gravada**, como no `extract`.

**Pode rodar de novo.** Cada matéria é comparada com **todas** as versões dela no banco, no que o DOU publicou (data, ementa e conteúdo). O órgão não entra: ele vem da identidade dos conselhos ([ADR 0004](docs/adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md)), e resolver um nome não é republicação. Comparar só com a última versão faria o mesmo `id` vindo com dois textos (no DO1 e no DO1E, ou em dois dias da janela de reprocessamento) gerar duas versões a cada execução:

| A matéria | O que acontece | No resumo |
|---|---|---|
| nunca foi vista | entra com `versao = 1` | `gravadas` |
| já está lá, igual a alguma versão | nada é gravado | `inalteradas` |
| já está lá, diferente de todas (a edição foi republicada) | entra com a `versao` seguinte; as anteriores ficam | `versoes-novas` |
| é de órgão desconhecido | fica de fora, e o órgão vai para a fila | `orgao-desconhecido` |
| tem o `id` de outra entrada do mesmo ZIP | fica de fora; vale a primeira | `repetidas` |

Um `id` repetido no mesmo ZIP não derruba as demais matérias e é logado com as duas entradas. Só a primeira é gravada: gravar as duas faria da segunda uma versão nova da primeira, e cada execução seguinte criaria mais duas versões.

Quem grava é o pacote `src/ingestor/internal/oltp`, em `ato` com `origem = 'DOU'`, insert-only ([ADR 0001](docs/adr/0001-adotar-sistema-de-curadoria-insert-only-como-oltp.md)):

| Coluna de `ato` | De onde vem |
|---|---|
| `id_dou` | o `id` do `<article>`, e não o `idMateria`: é o que a extração já exige em todo XML |
| `versao` | `1` na primeira vez; a seguinte a cada republicação com conteúdo diferente |
| `orgao_id` | o último nível do `artCategory`, casado com um órgão conhecido |
| `data_publicacao` | `pubDate` |
| `ementa` | `<Ementa>`; nula quando vem vazia |
| `conteudo` | o `<Texto>` como publicado, em HTML. Matéria com `<Texto>` vazio é recusada |

**Como o órgão é encontrado.** O nome do último nível do `artCategory` vira a chave normalizada do [ADR 0004](docs/adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md) (sem caixa, acento, espaços repetidos e sigla no fim) e é procurado entre os nomes que os órgãos têm ou já tiveram (`orgao_nome`) e as grafias resolvidas (`orgao_alias` com `status = 'RESOLVIDO'`). A chave é calculada em Go (`oltp.Key`) e em Python (`chave()` em `src/conselhos`); um teste confere que as duas dão o mesmo resultado nos 125 nomes que a carga gravou.

**Órgão desconhecido.** A maioria das ~300 matérias de um dia não é de conselho. A matéria de um órgão que não é um dos conhecidos **não entra em `ato`**, e o nome do órgão entra uma vez em `orgao_alias`, com `fonte = 'DOU'`, `status = 'INDEFINIDO'`, sem órgão e com o `artCategory` inteiro no motivo: é a fila de decisão do ADR 0004. Quando alguém resolver o nome, a matéria é gravada reingerindo o ZIP, que continua em `data/bronze/`. Se a chave casar com **mais de um** órgão, nenhum é escolhido: o nome entra na fila como `AMBIGUO`. Um nome que **já está à espera de decisão**, por qualquer fonte, não ganha uma segunda linha: se a planilha o deixou como `AMBIGUO` ou `INDEFINIDO`, o status e o motivo dela continuam valendo, e a matéria fica de fora até alguém decidir.

A chave do nome é calculada em dois lugares, em Python na carga e em Go na ingestão. As duas são conferidas contra o mesmo arquivo, `src/ingestor/internal/oltp/testdata/chaves.tsv`, com todos os nomes de `orgao_nome` e da planilha: nenhuma muda sem o teste da outra falhar.

A classificação não é tocada: continua da planilha e da curadoria ([ADR 0003](docs/adr/0003-carregar-a-planilha-como-rotulo-da-curadoria.md)).

## Ingerir um mês pelos dados abertos

O `make ingest-mensal` faz o mesmo que o `make ingest`, mas para um **mês inteiro**, e a partir dos [dados abertos da Imprensa Nacional](https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados): público, sem login e sem credencial no `.env`. O ZIP mensal traz o mesmo XML `<article>` do INLABS, com o `DO1` e o `DO1E` de todos os dias do mês, e é gravado pelo mesmo `persist`.

```bash
make ingest-mensal MES=2026-08   # baixa a Seção 1 de agosto e grava as matérias de conselho em ato
make fetch-mensal MES=2026-08    # só baixa, para data/bronze/dados-abertos/S01082026.zip
make persist-mensal MES=2026-08  # só grava o ZIP já baixado, sem acessar a Imprensa Nacional
```

- **O ZIP fica com o nome que a Imprensa Nacional dá** (`S01MMAAAA.zip`): a Seção 1 de agosto de 2026 é `S01082026.zip`, com cerca de 50 MB e 8.600 matérias.
- **Mês já em disco não é baixado de novo.** O arquivo de um mês fechado não muda, e o nome só existe depois que o ZIP chegou inteiro. Rodar o `make ingest-mensal` de novo não baixa nem duplica nada; o `persist` compara cada matéria com todas as versões, como no `make ingest`.
- **Mês ainda não publicado é erro**, e nada é gravado. O mês sai cerca de duas semanas depois de acabar: em meados de outubro, o mais recente é agosto. Para o dia de hoje, a fonte continua sendo o `make ingest`, do INLABS.
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

Dia a dia: `make lake` uma vez, depois `make cdc` sempre que quiser aplicar as reclassificações pendentes (pode rodar de novo, não duplica).

> **Slot parado retém WAL.** Se for abandonar o fluxo, rode `make cdc-drop`, senão o disco do banco cresce. Mudanças anteriores à criação do slot só entram com `make lake`.
>
> **Curadoria insert-only mantida.** A reclassificação da demonstração permanece registrada no histórico do banco (ADR 0001), sob revisor dedicado. Os testes isolam os revisores e não exigem `make reset` após demonstrar.

## Estrutura

```
sql/            DDL versionado do banco
src/            ingestão, parsing e transformações; src/ingestor/ (Go) está sendo migrado para src/dou/ (Python), fatia a fatia (#51)
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
