---
title: Plano de migração do ingestor Go para Python
---

> **Status: proposta, não decidida.** Planejado em 13/10/2026 com auxílio de Claude Code (agente de planejamento), a pedido da Luiza, para discussão da squad depois da E2. Nada aqui foi implementado. A decisão vira o ADR 0008 quando a squad aprovar.


Base lida: `README.md`, `Makefile`, `docker-compose.yml`, `.github/workflows/test.yml`, ADRs 0001/0003/0004/0006/0007, `AI-USAGE.md` (entradas de 10 a 13/10), todo `src/ingestor/` (4.730 linhas Go: 2.190 de código, 2.540 de teste; 112 funções `Test*` + 19 subtestes), `src/conselhos/identidade.py`, `src/lake/sync.py` e `cdc.py`, `scripts/carga.sh`, `tests/**`. HEAD local está desanexado em `5b08554` (CDC); o plano é contra `origin/main`.

Números de referência que o plano usa como gabarito (de `AI-USAGE.md`, 12/10, `make ingest-mensal MES=2026-08` em banco limpo): `S01082026.zip` tem 52,6 MB, 8.590 matérias + 120 imagens, 0 falhas, nenhum `id` repetido; o persist gravou **96 atos**, enfileirou **8.494** matérias de órgão desconhecido, `orgao_alias` ficou com **751 linhas**; segunda execução `gravadas=0 inalteradas=96`.

---

## 1. Inventário: o que cada pacote/comando Go faz e o equivalente Python

| Go (linhas código / teste) | O que faz | Equivalente Python sugerido | Dependências |
|---|---|---|---|
| `internal/store/store.go` (195 / 279, 18 testes) | `Store.Save`: temp no mesmo dir (`name.part-*`), copia, `fsync`, valida com `zip.NewReader`, `rename`, apaga marcadores `.sem-edicao`/`.falhou`, `fsync` do diretório. `Has`, `MarkNoEdition`, `MarkFailed` (ZIP em disco vence; marcador novo apaga o outro antes de escrever). `New` recusa dir inexistente. | `src/dou/bronze.py`: classe `Bronze(dir)` com `salvar(nome, fileobj)`, `tem(nome)`, `marcar_sem_edicao`, `marcar_falhou`. | stdlib: `tempfile.NamedTemporaryFile(dir=, prefix=nome+".part-", delete=False)`, `shutil.copyfileobj`, `os.fsync`, `zipfile.ZipFile` (abre o diretório central, como `zip.NewReader`; não usar `is_zipfile`, que só olha o fim do arquivo), `os.replace`, `os.open(dir)`+`os.fsync` |
| `internal/dadosabertos/dadosabertos.go` (226 / 198, 8 testes) | `ParseMonth` (só `YYYY-MM`), `ZipName` (`S01MMAAAA.zip`), `FetchMonth`: `Has` → sem requisição; lê a listagem `/acesso-a-informacao/dados-abertos/base-de-dados?ano=&mes=Agosto` (nomes em `monthNames`, com "Março"), `linkTo` acha `href` cujo path contém `/S01082026.zip/`, `html.UnescapeString`, resolve contra a base, **recusa host diferente**; GET com `User-Agent: conselhos-vivos-ingest/0.1` e `Accept: */*`; `ErrNotPublished`; timeout de 10 min no mês; limite de 5 MB na página. | `src/dou/dadosabertos.py`: `Mes`, `nome_do_zip`, `baixar_mes(mes, bronze, base_url=...)`, `link_para(pagina, nome, base)`. | stdlib: `urllib.request` (honra proxies do ambiente como `ProxyFromEnvironment`), `urllib.parse.urljoin/urlsplit`, `html.unescape`, `re` (`href="([^"]+)"`), `datetime.strptime("%Y-%m")`. Timeout: `urlopen(req, timeout=30)` cobre conexão/leitura por fase; o teto de 10 min vira contagem de relógio no laço de cópia, ou se aceita só o timeout por fase (registrar no PR). |
| `cmd/fetch-mensal/main.go` (70) + `internal/config.FetchMensal` | CLI `-month`; `DADOS_ABERTOS_OUTPUT_DIR` (padrão `.`); saída 2 (uso), 1 (erro/mês não publicado), log `iniciando`/`mes ... desfecho=baixada|ja-baixada`. | `python -m dou fetch-mensal --month AAAA-MM` em `src/dou/__main__.py` (dispatch como `python -m conselhos {sql|relatorio|siorg}`). | `argparse` (sai com 2 em erro de uso, igual ao Go), `logging` para stderr, `os.environ`. |
| `internal/article/article.go` + `text.go` (252 / 220, 10 testes) | `Read(zip)`: itera entradas, `.xml` em qualquer profundidade (case-insensitive), pasta/imagem → `ErrNotXML`; `parse`: exatamente um `<article>`, exige `id`, `pubDate` `DD/MM/YYYY`, `artCategory` não vazio; `TrimSpace` em todos os campos exceto `Texto` (HTML cru); `splitCategory` descarta níveis vazios; `Organ()` = último nível; `PlainText`: tokenizer HTML, quebra de linha em `p br div tr li table h1-h6`, ` | ` entre `td/th`, espaços colapsados, entidades decodificadas. Campos JSON: `entry,id,idMateria,pubName,artType,pubDate,numberPage,editionNumber,artClass,artCategory,identifica,ementa,titulo,subTitulo,html(omitempty),texto`. | `src/dou/materia.py`: `@dataclass Materia`, `ler(zipfile.ZipFile)` gerador de `(Materia|None, erro|None)`, `extrair_texto(html)`. | stdlib: `zipfile`, `xml.etree.ElementTree` (aceita BOM e CRLF da amostra real; CDATA vira `.text`), `html.parser.HTMLParser(convert_charrefs=True)`, `datetime.date`, `json.dumps(ensure_ascii=False)` (equivale a `SetEscapeHTML(false)`). |
| `cmd/extract/main.go` (106 / 106, 3 testes) | `[-html] EDITION.zip` → uma linha JSON por matéria no stdout; resumo `lidas/ignoradas/falhou` no stderr; saída 1 se `falhou>0` ou ZIP não abre; 2 se nº de args ≠ 1. | `python -m dou extract [--html] ZIP`. | stdlib. |
| `internal/oltp/key.go` (45 / 58, 2 testes) | `squeeze` + `Key` = `espacos()` + `chave()` de `src/conselhos/identidade.py` (regexes idênticos, NFKD, remove `unicodedata.combining`, casefold). Paridade por `testdata/chaves.tsv` (169 pares). | **Não portar: importar `conselhos.identidade.chave` e `espacos`.** A duplicação some; `chaves.tsv` vira arquivo-ouro só do Python (mover para `tests/conselhos/chaves.tsv`). | — |
| `internal/oltp/oltp.go` (197 / 418, 14 testes) | `Open`: lê `orgao_nome ∪ orgao_alias(RESOLVIDO)` → `chave→orgao_id`, chave com 2 ids vira `ambiguous` e sai do mapa; lê `orgao_alias WHERE status <> 'RESOLVIDO'` → `waiting`. `Save`: `ErrNoContent` se `<Texto>` em branco; órgão desconhecido → `queue` (uma linha `INDEFINIDO`/`AMBIGUO`, `fonte='DOU'`, motivo com `artCategory`, `ON CONFLICT (fonte, nome) DO NOTHING`, não reenfileira chave já `waiting`); senão um único statement `WITH versions AS (...) INSERT ... WHERE NOT EXISTS (same) RETURNING versao` comparando **todas** as versões por `data_publicacao`, `ementa IS NOT DISTINCT FROM NULLIF($4,'')`, `conteudo`; sem linha → `Unchanged`; `versao>1` → `NewVersion`. | `src/dou/oltp.py`: `class Gravador` com `abrir(conn)`, `salvar(materia)` → `Desfecho` (Enum: GRAVADA, VERSAO_NOVA, INALTERADA, ORGAO_DESCONHECIDO), `SemConteudo(Exception)`. **O SQL é copiado como está**, trocando `$n` por `%s`. | `psycopg[binary]==3.2.5` (já em `src/lake/requirements.txt`). `date` Python → `DATE`; `a.PubDate.In(time.UTC)` é só a conversão civil→timestamp do Go, não há equivalente a fazer. |
| `cmd/persist/main.go` (185 / 221, 6 testes) | `EDITION.zip` → conexão pelas `PG*`, **uma transação por ZIP**, `seen[id]` → `repetida` (vale a primeira), resumo `gravadas/versoes-novas/inalteradas/orgao-desconhecido/repetidas/ignoradas/falhou`; commit mesmo com falhas de entrada e saída 1. | `python -m dou persist ZIP`; função `persistir(conn_ou_tx, logger, caminho) -> Resumo` separada do `main` para o teste. | `psycopg` com `autocommit=False` (não reusar `lake.sync.obter_conexao`, que usa `autocommit=True`; criar `dou/db.py::conectar()` lendo `PG*`/`POSTGRES_*` do mesmo jeito). |
| `internal/dbtest/dbtest.go` (39) | Transação nunca confirmada; `t.Skip` sem `PGHOST`. | `tests/dou_db/dbtest.py`: `class CasoComBanco(unittest.TestCase)` com `setUp` (`psycopg.connect`), `tearDown` (`rollback`+`close`), `@unittest.skipUnless(os.getenv("PGHOST"), ...)`. | psycopg. |
| `internal/config/config.go` (60 / 117, 7 testes) | `.env` opcional via `-env` (godotenv), ambiente vence; `INLABS_EMAIL/SENHA` obrigatórios; `*_OUTPUT_DIR`. | Some com o INLABS. Para o mensal basta `os.environ.get("DADOS_ABERTOS_OUTPUT_DIR", ".")`. | — |
| `internal/inlabs/` (540 / 995, 37 testes) + `cmd/fetch` (122 / 81, 6 testes) | Login `POST /logar.php` com header `origem`, cookie `inlabs_session_cookie` como única prova, sem seguir 302, `retryablehttp` com backoff+`Retry-After`, 404 → `.sem-edicao`, 302/200-html → sessão expirada (renova uma vez), `FetchDay` DO1+DO1E com timeout por seção, `Today` em `America/Sao_Paulo` (tzdata embutido), piso 2020-01-01, nenhuma credencial em log. | **Não migrar agora; descartar com ADR** (ver fatia 4). O login é recusado com 502 para qualquer script (#42). O contrato do bronze (`data/bronze/inlabs/AAAA-MM-DD-DO1[E].zip` + marcadores) é preservado por `bronze.py` e pelo `TEM_EDICAO` do Makefile. | Se um dia voltar: `urllib` + `http.cookiejar`, `zoneinfo` (**`python:3.12-slim` não traz `/usr/share/zoneinfo`: precisaria de `pip install tzdata`**). |
| `go.mod`: `civil`, `caarlos0/env`, `retryablehttp`, `pgx/v5`, `godotenv`, `x/net/html`, `x/text`, `testify` | — | Tudo coberto pela stdlib + `psycopg`. Testes com `unittest` (padrão do repo, `tests/planilha` e `tests/conselhos`), sem pytest. | — |

---

## 2. Ordem de migração (fatias verticais, cada uma mergeável com `make test` verde)

Princípio: durante a transição Go e Python coexistem na árvore; cada fatia **troca um serviço compose e um alvo do Makefile** de Go para Python, mantém o alvo Go como `*-go` até a última fatia, e traz um script temporário de equivalência. Nada é apagado antes de provado.

```
F0  infra Python (pacote src/dou, serviço compose, alvo de teste, CI)         sem mudança de comportamento
F1  fetch-mensal  = bronze.py + dadosabertos.py + CLI                         troca o serviço fetch-mensal
F2  extract       = materia.py (+ extrair_texto) + CLI                        troca o serviço extract
F3  persist       = oltp.py (reusa conselhos.identidade) + db.py + CLI        troca persist, persist-mensal, test-db-go
F4  INLABS: ADR de descarte; remoção do Go (cmd/fetch, inlabs, config, go.mod, serviços, vet-go, CI)
F5  ADR de linguagem única + limpeza final de README/docs
```

Por que esta ordem: F1→F2→F3 é o caminho que roda de verdade (`make ingest-mensal`), cada uma com uma prova de equivalência objetiva sobre `S01082026.zip`, que já está em `data/bronze/dados-abertos/`. F3 depende de F2 (parser) e F1 (nada, mas convém ter o ZIP baixado pelo Python). A decisão sobre o INLABS (F4) fica por último porque é a única que apaga comportamento, e precisa de ADR.

---

## 3. Detalhe por fatia

### F0 — Infra do pacote Python (sem comportamento novo)

**Criar**
- `src/dou/__init__.py` (docstring: ingestão do DOU, ADRs 0001/0004), `src/dou/__main__.py` (dispatch de subcomandos, por ora vazio/`--help`), `src/dou/requirements.txt` (`psycopg[binary]==3.2.5`, mesma versão do lake).
- `tests/dou/__init__.py` (testes sem banco e sem rede externa, rodam no serviço `carga`, que já monta `./src` e `./tests` e tem `network_mode: none`; loopback existe mesmo com `none`, o que basta para `http.server` em thread — **confirmar na F1**).
- `tests/dou_db/__init__.py` (testes com banco; rodam num serviço novo).
- `docker-compose.yml`: serviços `dou` (modelo do `lake`: `python:3.12.14-slim`, `pip install -r /app/src/dou/requirements.txt` com volume `pipcache`, `PYTHONPATH=/app/src`, `./src:/app/src:ro`, `./data/bronze:/data/bronze`, `user: ${DOCKER_UID}:${DOCKER_GID}` para quem escreve no bronze, `PG*` e `depends_on: db` para o persist) e `dou-db-test` (mesmo, mais `./tests:/app/tests:ro`, `entrypoint` em `python -m unittest discover -s tests/dou_db`).
- `Makefile`: `test-py-dou` (`carga -m unittest discover -s tests/dou`) e `test-db-py` (serviço `dou-db-test`); ambos entram em `test`.
- `.github/workflows/test.yml`: nada ainda (`make test` já chama).

**Risco**: o `pip install` a cada `run` (como no `lake`) custa ~segundos com `pipcache`; aceito, é o padrão já adotado. **Esforço: 3 h.**

### F1 — `fetch-mensal` em Python

**Criar**: `src/dou/bronze.py`, `src/dou/dadosabertos.py`, subcomando `fetch-mensal` em `src/dou/__main__.py`, `tests/dou/test_bronze.py`, `tests/dou/test_dadosabertos.py`.
**Trocar**: serviço compose `fetch-mensal` → imagem Python (entrypoint `python -m dou fetch-mensal "$@"`, `DADOS_ABERTOS_OUTPUT_DIR=/data/bronze/dados-abertos`); alvo `make fetch-mensal` passa `--month $(MES)`. Manter o serviço Go como `fetch-mensal-go` só até o fim da F1 (apagar no mesmo PR se a prova passar).

**Portar os testes (18 `store` + 8 `dadosabertos` → ~26 casos `unittest`)**
- `store_test.go`: `TestSaveLandsAValidZip`, `RefusesAnHTMLBody`, `LeavesNothingWhenTheStreamBreaks` (reader que levanta no meio), `ReplacesAnExistingFile`, `IsSafeWhenTwoRunsRaceOnTheSameName` (duas `threading.Thread`), `NewRefusesADirectoryThatIsNotThere`, `NewRefusesAPathThatIsAFile`, os 9 de marcadores (`MarkNoEdition` idempotente, ZIP vence, `Save` apaga marcador, último marcador fica, `Has` só vê o ZIP). Diretório via `tempfile.TemporaryDirectory`; ZIP de teste via `zipfile.ZipFile(io.BytesIO(), "w")`.
- `dadosabertos_test.go`: `monthServer` vira `http.server.ThreadingHTTPServer` em `127.0.0.1:0` numa thread, handler que devolve 403 sem `Accept: */*`, serve a `listing` fixa (copiar a página do teste Go, com `&amp;`) e conta requisições. Casos: nome publicado, só `YYYY-MM`, salva a Seção 1 (asserta o path do ZIP), mês em disco → 0 requisições, mês não publicado → 1 requisição e dir vazio, download 500 → dir vazio, página no lugar do ZIP → "não é zip", link para outro host → erro cita o host e 1 requisição.

**Riscos específicos**
- `urllib` segue redirects por padrão; o Go também (`dadosabertos` não desliga `CheckRedirect`). Mesmo comportamento; registrar.
- `urllib` manda `Accept-Encoding: identity`; não setar `gzip` à mão (ZIP já é comprimido; o aviso do `context.md` vale).
- Permissão do arquivo: Go cria o temp com `0600` e o `rename` mantém (o ZIP em disco hoje tem `-rw-------`); `NamedTemporaryFile` também é `0600`. Igual.
- Timeout total de 10 min: `urlopen(timeout=30)` é por operação de socket; aceitar como "fase", como o Go faz para dial/TLS/headers, e documentar que não há teto global.

**Prova de equivalência**: `mv data/bronze/dados-abertos/S01082026.zip /tmp/go.zip` (fora do repo) → `make fetch-mensal MES=2026-08` (Python) → `cmp /tmp/go.zip data/bronze/dados-abertos/S01082026.zip` (o arquivo de um mês fechado não muda; 12/10 já provou que o download bate byte a byte com a amostra). Segunda execução: nenhuma requisição (log `ja-baixada`). `MES=2026-09` → saída 1 e nada em disco. `MES=2026-9` → saída 2.
**Esforço: 8 h.**

### F2 — `extract` em Python

**Criar**: `src/dou/materia.py` (`Materia`, `ler`, `extrair_texto`, `NaoEXML`, `Malformada`, `ErroDeEntrada(entrada, causa)`), subcomando `extract`, `tests/dou/test_materia.py`, `tests/dou/test_extract.py`. **Mover** `src/ingestor/internal/article/testdata/*.xml` + `README.md` para `tests/dou/amostras/` (na F2 copiar; apagar os originais na F4). Os testes Go leem `testdata/` relativo ao pacote; `cmd/persist` e `oltp` também apontam para lá — por isso copiar, não mover, até a F4.
**Trocar**: serviço `extract` → Python (`./data/bronze:/data/bronze:ro`); `make extract` passa `--html` em vez de `-html` (ou aceitar os dois no argparse: `add_argument("-html", "--html")` funciona).

**Portar os testes (10 `article` + 3 `extract`)**: `ParseRealArticle` (campo a campo, incluindo `artClass`, BOM/CRLF, `Text` começa/termina como no Go), `ParseConselho` (o texto esperado com `Art. | Prazo` e `1º | 30 dias` é o gabarito do `extrair_texto`), `ReadSurvivesBadEntries`, `FindsXMLAtAnyDepth`, `ReportsADirectory` (entrada `pasta/` → `NaoEXML`), `ReadStopsWhenTheCallerDoes` (gerador: `next()` e descartar; conferir que não abriu a 2ª entrada), `ParseRefusesIncompleteArticles` (sem id, sem pubDate, sem artCategory, dois `<article>`), `SplitCategoryDropsEmptyLevels`, `OrganOfNoCategory`, `EntryErrorUnwraps` (`__cause__`). `extract`: uma linha por matéria (`json.loads` de cada linha), `html` só com `--html`, ZIP que não abre → erro cita o caminho.

**Riscos específicos**
- `extrair_texto`: `HTMLParser` é puro Python; em ~50 MB de HTML por mês estimo dezenas de segundos — medir e registrar (o projeto registra medições no AI-USAGE). O Go tokenizer decodifica entidades no texto (`tokens.Text()`); `convert_charrefs=True` faz o mesmo. `strings.Fields` e `str.split()` ambos tratam espaço Unicode (inclui NBSP) — igual.
- `encoding/xml` com `body>Texto` pega o primeiro `<Texto>`; usar `find("body/Texto")` (não `iter`). Elemento com filhos (não CDATA): os dois pegam só o texto inicial; a prova sobre 8.590 matérias cobre.
- JSON: Go escapa U+2028/2029 mesmo com `SetEscapeHTML(false)`; Python não. Comparar com `jq -c -S .` dos dois lados, não por `diff` cru. `pubDate` em Go sai `"2026-10-02"` (`civil.Date.MarshalText`): emitir `isoformat()`.
- `strings.TrimSpace` × `str.strip()`: ambos Unicode. OK.

**Prova de equivalência**: `docker compose run --rm -T extract /data/bronze/dados-abertos/S01082026.zip | jq -c -S . > /tmp/go.jsonl` e o mesmo com o serviço Python (`--html` ligado para comparar o HTML cru também) → `diff` vazio, 8.590 linhas, resumo `lidas=8590 ignoradas=120 falhou=0`, mesmo código de saída. Guardar tempo de execução dos dois.
**Esforço: 8 h.**

### F3 — `persist` em Python (a fatia que importa)

**Criar**: `src/dou/db.py` (`conectar()` com `PG*`/`POSTGRES_*`, `autocommit=False`), `src/dou/oltp.py`, subcomando `persist`, `tests/dou_db/dbtest.py`, `tests/dou_db/test_oltp.py`, `tests/dou_db/test_persist.py`. **Mover** `src/ingestor/internal/oltp/testdata/chaves.tsv` → `tests/conselhos/chaves.tsv` e ajustar `CHAVES` em `tests/conselhos/test_conselhos.py:26` (o teste `test_a_chave_e_a_mesma_do_go` passa a chamar-se `test_a_chave_nao_mudou`: vira arquivo-ouro de regressão, porque `orgao_alias.chave` já está gravada com esses valores). Na F3 ainda não apagar `key.go` (o `TestKeyAgreesWithThePythonKey` lê `testdata/chaves.tsv`: deixar uma cópia até a F4, ou apagar o teste Go nesta fatia — prefiro apagar `internal/oltp` inteiro na F3, já que o serviço `persist` deixa de usá-lo; ver abaixo).
**Trocar**: serviço `persist` → Python (`PG*`, `depends_on: db`, bronze `:ro`); `make persist`, `make persist-mensal` (sem mudança de sintaxe: o argumento é o caminho do ZIP); `make test-db-go` → `test-db-py` (serviço `dou-db-test`); `test:` chama o novo. Apagar na mesma fatia `src/ingestor/internal/oltp/`, `cmd/persist/`, `internal/dbtest/`, `internal/article/`, `cmd/extract/` e o serviço `ingestor-db-test` (nenhum outro pacote Go depende deles: `inlabs` e `dadosabertos` só usam `store`). Com isso `make test-db-go` some e `make test-go` passa a cobrir só `inlabs`, `store`, `dadosabertos`, `config`, `cmd/fetch`.

**Portar os testes (14 `oltp` + 6 `persist` + 2 `key`)**
- Helpers: `materia_construida(id, *categoria)` (equivale a `handmade`), `amostra_construida()` (lê `conselho-construido.xml` via `ler`), `novo_orgao(conn, nome)` (`INSERT INTO orgao DEFAULT VALUES RETURNING id` + `orgao_nome`), `contar(conn, sql, *args)`, `estado(conn)` (a query do `state()` de `main_test.go:72`, `row_to_json`).
- `oltp`: grava matéria do CONAMA (checa `origem`, `versao=1`, data, ementa, `conteudo == html` com `<p class="assina">`), ementa vazia e em branco → NULL, acha o órgão por `orgao_nome` antigo e por `orgao_alias RESOLVIDO`, enfileira desconhecido (`INDEFINIDO`, `fonte='DOU'`, motivo com `artCategory`), não enfileira nome já pendente (de qualquer fonte, por chave), não escolhe entre dois órgãos (`AMBIGUO`), gravar de novo não escreve, não alterna entre duas versões conhecidas, mudança só de órgão não gera versão, republicada vira versão 2 com a 1 intacta, sem `<Texto>` → `SemConteudo`, chave bate com aliases carregados (`SELECT nome, chave FROM orgao_alias` e `chave(nome) == chave` para toda linha — **este teste é também a verificação do risco Unicode da seção 6**).
- `persist`: `SavesTheEdition` (resumo `gravadas=1 orgao-desconhecido=1 ignoradas=1 falhou=1`, +1 ou +2 linhas conforme a Coordenação-Geral da PF já esteja na fila), `TwiceLeavesTheDatabaseIdentical` (lista `estado()` igual), `RepublishedEditionAsNewVersions` (`1:false,2:true`), `OnlyTheFirstOfARepeatedID`, `TakesAMateriaThatArrivedLate` (`data_publicacao = 2026-10-02`), `StopsOnAZipThatDoesNotOpen` (antes de tocar o banco). ZIP de teste montado em `tempfile` com entradas em ordem alfabética (`writeEdition` ordena por nome: o Python deve fazer o mesmo, senão o caso do `id` repetido inverte qual é "a primeira").
- `key_test.go` → já existe em `tests/conselhos/test_conselhos.py` (`Chave.*`): nada a portar.

**Riscos específicos**
- `NULLIF(%s, '')` com `str` em psycopg3: o parâmetro vai sem OID (unknown) e o servidor infere `text`; se o planner reclamar de tipo, usar `NULLIF(%s::text, '')`. A comparação `data_publicacao = %s` com `datetime.date` é `DATE` nativo.
- Transação: `conn.transaction()` ou `BEGIN` explícito; commit no fim do ZIP, **saída 1 mesmo com commit** quando `falhou>0` (comportamento documentado no README).
- A race de `uq_ato_dou_versao` (duas execuções no mesmo ZIP): o Go deixa o erro subir e aborta; manter igual.
- Logs: não há credencial no fluxo (as `PG*` nunca são logadas); manter a linha-resumo no formato `chave=valor` do slog (`gravadas=96 versoes-novas=0 ...`), porque o README e o AI-USAGE citam esse formato.

**Prova de equivalência (a mais importante)**
1. `make reset` (banco zerado + carga) → `make persist-mensal MES=2026-08` **com o serviço Go** → foto A:
   `SELECT id_dou, versao, orgao_id, data_publicacao, ementa, md5(conteudo) FROM ato WHERE origem='DOU' ORDER BY 1,2` e `SELECT nome, chave, fonte, status, orgao_id, motivo FROM orgao_alias ORDER BY fonte, nome` (sem `id`/`criado_em`, que mudam entre bancos). Esperado: 96 linhas em `ato`, 751 em `orgao_alias`.
2. `make reset` → o mesmo com o serviço Python → foto B. `diff A B` vazio; resumo `gravadas=96 orgao-desconhecido=8494 ignoradas=120 falhou=0 repetidas=0`.
3. **Prova cruzada** (a mais forte): sobre o banco da etapa 1 (gravado pelo Go), rodar o persist Python: tem de dar `gravadas=0 versoes-novas=0 inalteradas=96` e `estado()` idêntico antes/depois. Isso prova que ementa/conteudo/data chegam byte a byte iguais ao que o Go gravou; qualquer diferença de parsing viraria `versoes-novas>0`.
4. Guardar as fotos e os tempos em `docs/adr/medicoes/0008-linguagem-unica/` e citar no AI-USAGE.
**Esforço: 10 h.**

### F4 — INLABS: descartar com ADR e tirar o Go do repositório

**Decisão recomendada: não portar o cliente INLABS agora.** Motivos verificados: o login automático é recusado (502 em `logar.php`, inclusive com o script oficial — `AI-USAGE.md` 12/10, README "Dado atrasado"); é o maior bloco do módulo (1.535 linhas = 33% do Go, 43 testes) e portá-lo sem poder exercitar contra o INLABS produziria código morto; a fonte automática real já é a mensal. O que se preserva: o contrato do bronze diário (`data/bronze/inlabs/AAAA-MM-DD-DO1[E].zip` + `.sem-edicao`/`.falhou`), que `make extract DATA=` e `make persist DATA=` continuam lendo via `TEM_EDICAO` — um ZIP baixado à mão pelo navegador continua entrando no pipeline. Manter os marcadores em `bronze.py` (já portados na F1) custa pouco e deixa o caminho pronto se o INLABS voltar a aceitar scripts.

Alternativa B (se a squad quiser manter a opção viva sem código): mover `src/ingestor/` inteiro para um diretório `archive/` não testado — **não recomendo**: viola "código no repo roda no `make test`".
Alternativa C (manter Go só para o INLABS): mantém dois toolchains, duas suítes e o `vet-go` no CI por um comando que não funciona — é o custo que o ADR 0008 quer eliminar.

**Remover**: `src/ingestor/` inteiro (restam `cmd/fetch`, `cmd/fetch-mensal`, `internal/inlabs`, `internal/store`, `internal/dadosabertos`, `internal/config`, `go.mod`, `go.sum`); serviços `ingestor`, `ingestor-test` (e `fetch-mensal` Go, se ainda existir), volumes `gocache`/`gomodcache`; alvos `fetch`, `ingest`, `ingest-dia`, `test-go`, `vet-go`; a linha `make vet-go` do CI; variáveis `INLABS_*` do `.env.example` (ou deixar comentadas com a referência ao ADR). **Manter** `make janela` e `tests/ingest/test_janela.sh`? O `janela` só existe para o `ingest`; sem `ingest` vira órfão. Proposta: remover ambos e registrar no ADR que a janela volta com o cliente diário; se a squad preferir manter a conta de datas para o `ingest-dia` manual, custa zero (já é Python no container `carga`).
**Substituir `vet-go`** por `vet-py`: `python -W error -m compileall -q src tests` (stdlib) — e, se a squad aceitar uma ferramenta de dev, `ruff check` (o `.gitignore` já lista `.ruff_cache/`). CI: trocar a linha.
**README**: seções "Baixar o DOU", "Gravar as matérias no banco" (trocar `src/ingestor/internal/oltp` por `src/dou/oltp.py`, remover "A chave é calculada em Go e em Python"), tabela de comandos, "Ingerir um mês".
**Esforço: 5 h** (sem contar a discussão do ADR na squad).

### F5 — ADR de linguagem única e limpeza

ADR 0008 (abaixo), índice em `docs/adr/README.md`, entrada no `AI-USAGE.md`, diário. Apagar `scripts/equivalencia.sh` temporário, se criado. **Esforço: 2 h.**

---

## 4. Estimativa de esforço (horas de uma pessoa)

| Fatia | Código | Testes | Prova/medição | Docs/PR | Total |
|---|---|---|---|---|---|
| F0 infra | 1,5 | 0,5 | – | 1 | **3** |
| F1 fetch-mensal | 3 | 3 | 1 | 1 | **8** |
| F2 extract | 3,5 | 2,5 | 1 | 1 | **8** |
| F3 persist | 3 | 4 | 2 | 1 | **10** |
| F4 INLABS + remoção do Go | 1 | 0,5 | 1 | 2,5 | **5** |
| F5 ADR 0008 + limpeza | – | – | – | 2 | **2** |
| Revisão de PR, retrabalho (~20%) | | | | | **7** |
| **Total** | | | | | **≈ 43 h** |

Cabe entre 14/10 e 03/11 para uma pessoa a meio tempo; F1–F3 são independentes de dbt/orquestração e podem andar em paralelo com a E3.

---

## 5. ADR: o que precisa virar decisão registrada

Dois pontos de decisão; recomendo **um ADR com os dois**, porque o segundo é consequência do primeiro: `docs/adr/0008-unificar-o-pipeline-em-python.md` (0005 está reservado para a #32; 0006 e 0007 existem). Rascunho de 10 linhas:

1. **Contexto.** O pipeline tem dois toolchains: Go 1.26 no ingestor (`src/ingestor`, 2,2 mil linhas, 112 testes, quatro serviços compose e três alvos de teste próprios) e Python 3.12 em planilha, conselhos e lake. A E3 traz dbt e orquestração, ambos em Python. A chave do órgão (ADR 0004) está em duas linguagens, com teste de paridade por arquivo. O cliente INLABS, metade do Go, não funciona desde 12/10 (login recusado a scripts); a ingestão real é a mensal dos dados abertos.
2. **Alternativas.** (A) manter as duas linguagens — opção nula: zero custo de migração, mas cada mudança na identidade dos conselhos exige dois PRs e dois toolchains no CI, e o orquestrador chamaria binários Go por shell; (B) tudo Python — reescrita de ~1 mil linhas úteis + testes, zero dependência nova (psycopg já está no lake), chave em um lugar só; (C) tudo Go — reescrever planilha, conselhos e lake (deltalake/pyarrow não têm equivalente Go maduro) contra o ADR 0003 e o 0006.
3. **Critério.** Onde fica o código que a E3 vai orquestrar e que a pesquisadora vai manter; custo de manter a chave do órgão em dois lugares; o que já roda de verdade.
4. **Decisão.** (B): o ingestor migra para `src/dou/` em fatias (fetch-mensal → extract → persist), cada uma provada sobre `S01082026.zip` contra o Go antes de o Go sair; o cliente INLABS é **descontinuado sem porte**, mantendo o contrato do bronze diário para ZIPs baixados à mão; o Go sai do repositório ao fim.
5. **Consequências.** Ganha-se um toolchain, uma suíte, uma chave; perde-se o `-race` e o `go vet` (substituídos por testes com threads e `compileall`/ruff), o cliente INLABS com retry/sessão (recuperável do histórico) e, possivelmente, desempenho no `extrair_texto` (medido na F2 e registrado).
6. **Gatilho de revisão.** O INLABS voltar a aceitar login por script (reavaliar portar `internal/inlabs` com `urllib`+`cookiejar`); o parser Python passar de N minutos por mês (medir; limite a decidir).

---

## 6. Riscos e armadilhas gerais

- **Perda de cobertura.** Go: 112 testes + 19 subtestes. Com o descarte do INLABS saem 50 (37 `inlabs` + 6 `cmd/fetch` + 7 `config`). Os 62 restantes têm porte 1:1 na tabela acima (18 store, 8 dadosabertos, 10 article, 3 extract, 14 oltp, 6 persist, 2 key já cobertos em Python). Conferir no PR de cada fatia a lista nome a nome; o `TestSaveIsSafeWhenTwoRunsRaceOnTheSameName` precisa de threads reais, não de mock.
- **Unicode na chave (#40).** O Go só passou a bater com o Python depois de trocar categoria `Mn` por classe de combinação; os 2 caracteres divergentes não ocorrem em nome real. Com a migração a divergência entre linguagens desaparece, mas **as 751 chaves em `orgao_alias.chave` foram gravadas em parte pelo Go (626 do DOU) com tabelas Unicode do `x/text`, e o Python 3.12 usa Unicode 15.0**: o teste `TestKeyAgreesWithTheLoadedAliases` portado (recalcular `chave(nome)` para toda linha de `orgao_alias`) é a verificação; rodar também uma vez à mão contra o banco cheio de agosto antes de mergear a F3. Divergência aqui faria o persist enfileirar de novo um nome já pendente (chave diferente → `waiting` não casa).
- **Tipos.** `pubDate` `DD/MM/YYYY` → `date` (não `datetime`); `versao` é `int`; `orgao_id` `int`; `ementa` `None` quando vazia **só no SQL** (`NULLIF`), como no Go, para a comparação `IS NOT DISTINCT FROM` continuar valendo; `conteudo` é o `<Texto>` cru sem `strip`.
- **Timezone.** Só o caminho diário depende de "hoje em Brasília" (`inlabs.Today`); o Makefile já resolve com `TZ=America/Sao_Paulo date +%F` no host, e o Python não entra nisso. Se o cliente diário voltar: `zoneinfo` exige `tzdata` na imagem slim.
- **Desempenho do parser.** 8.590 XMLs/mês em `zipfile` + `ElementTree` é segundos; o gargalo provável é `HTMLParser` no `extrair_texto` (só o `extract` precisa dele; o `persist` grava o HTML cru — **não chamar `extrair_texto` no persist**, como o Go também não precisa, embora `parse` o compute sempre: tornar o texto puro preguiçoso, `@cached_property`, é uma melhoria legítima que não muda a saída). Ler entrada a entrada, nunca `read()` do ZIP inteiro (50 MB).
- **Idempotência.** O statement único (`WITH versions ... INSERT ... WHERE NOT EXISTS`) é o que garante "compara com todas as versões" e evita a corrida; copiar literalmente, não "reescrever em ORM". A prova cruzada da F3 (Go gravou, Python relê → `inalteradas=96`) é o teste de aceitação.
- **Ordem das entradas do ZIP.** O caso "id repetido, vale a primeira" depende da ordem do diretório central (`ZipFile.infolist()` preserva, como `zip.Reader.File`). Os testes constroem o ZIP com nomes ordenados.
- **Marcadores e `TEM_EDICAO`.** O Makefile lê `.sem-edicao`/`.falhou` por `wildcard`; sem o `fetch` diário ninguém mais os escreve, mas os cinco `.falhou` que estão hoje em `data/bronze/inlabs/` continuam fazendo `make persist DATA=2026-10-04` sair com erro — comportamento correto, documentar.
- **CI.** `make test` chama `test-go` e o workflow chama `vet-go`; cada fatia que remove um alvo tem de ajustar os dois no mesmo PR, senão o CI quebra no `main`.
- **Docs.** README, `docs/diario`, página "Jornada do dado" do site citam `src/ingestor/...`; o site VitePress serve os `.md` do repo, então link quebrado derruba o build do `make docs`.
- **Git.** O trabalho local está em HEAD desanexado sobre commits de CDC não mergeados (`5b08554`); abrir as branches das fatias a partir de `origin/main` e rebasear quando o CDC entrar.

---
