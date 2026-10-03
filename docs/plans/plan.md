# Fetcher INLABS do DOU — o que falta fazer

Baixar as edições da Seção 1 do DOU (DO1) do INLABS para um intervalo
de datas e gravar os ZIPs em disco. Esta fase baixa e grava; não abre os ZIPs,
não escreve no Postgres e não mantém registro de estado por data.

Datas resolvidas em **America/Sao_Paulo**. A unidade de trabalho é a data.
DO1E, a edição extra do mesmo dia, ficou de fora desta fase.

## Pronto

- [x] `internal/config` — credenciais do INLABS do ambiente, `.env` opcional
- [x] `internal/inlabs` — login por POST em `logar.php`, header `origem`,
      cookie de sessão no jar como única prova de login
- [x] `cmd/fetch` — carrega config, cria diretório de saída, faz login

## Passo 1 — `Date`, sem rede

`internal/inlabs/date.go`

- [x] `type Date` guardando ano/mês/dia, sem hora dentro
- [x] `ParseDate("2026-10-02")`, `String()`, `Before()`, `After()`,
      `Compare()` e `NewDate()`
- [x] `Today(now time.Time, loc *time.Location) Date` — recebe o instante e
      o fuso em vez de chamar `time.Now()` dentro, senão o fuso não é testável
- [x] `Range(first, last Date) ([]Date, error)` — erro se `first > last`; o
      passo a passo acontece em UTC, porque um dia que começa numa transição
      de horário de verão não tem meia-noite
- [x] a const `TimeZone` com `LoadLocation()`
- [ ] `main`: `time.LoadLocation("America/Sao_Paulo")` e
      `import _ "time/tzdata"` — imagem distroless não tem zoneinfo, e sem o
      import isso passa no teste local e falha em produção

Testes:

- [x] parse válido e inválido (8 casos de recusa)
- [x] intervalo invertido dá erro
- [x] range de 1 dia, de N dias, atravessando mês, ano e 29 de fevereiro,
      mais um backfill de 4 meses sem repetir nem perder dia
- [x] **`2026-10-02T01:30Z` → `Today` devolve 01/10**, porque em São Paulo
      ainda é 22:30 do dia anterior. Sem isto, depois das 21h o comando pede
      a edição de amanhã, leva 404 e marca dia útil como sem edição

## Passo 2 — `Fetch` de uma data

`internal/inlabs/inlabsclient.go`

- [ ] `Fetch(ctx, d Date) (io.ReadCloser, error)`, montando
      `index.php?p=<data>&dl=<data>-DO1.zip` com o header `origem`
- [ ] o nome do arquivo (`2026-10-02-DO1.zip`) é montado aqui, num lugar só:
      ele é o mesmo string no parâmetro `dl` da URL e no disco
- [ ] devolve o corpo como stream; quem grava é o passo 3
- [ ] `CheckRedirect` devolvendo `http.ErrUseLastResponse` no `New()` — hoje o
      cliente segue o 302, e seguido ele vira 200 com HTML
- [ ] classificação por sentinela: `ErrNoEdition` (404), `ErrSessionExpired`
      (302 para `acessar.php` **ou** 200 com `Content-Type: text/html`),
      `ErrTransient` (5xx, 429)
- [ ] nunca setar `Accept-Encoding` à mão: desliga a descompressão automática
      e grava bytes comprimidos dentro do ZIP

Testes (reusando `newTestClient`):

- [ ] 200 com ZIP devolve o corpo íntegro
- [ ] 404 → `ErrNoEdition`, sem retentativa
- [ ] 302 para `acessar.php` → `ErrSessionExpired`, sem ler o corpo
- [ ] 200 com HTML → `ErrSessionExpired`
- [ ] 500 → `ErrTransient`
- [ ] URL e nome de arquivo montados corretamente
- [ ] `origem` presente em toda requisição

## Passo 3 — `Store.Save`, escrita atômica

`internal/store/store.go`

- [ ] `Store{dir string}` e `Save(name string, r io.Reader) (Receipt, error)`
      com tamanho e sha256 no recibo — struct desde já, para virar interface
      depois sem mexer em chamador
- [ ] ordem: temporário **no mesmo diretório** → `io.Copy` → `Sync` do
      arquivo → **valida o ZIP no temporário** → `Rename` → `Sync` do
      diretório
  - temporário noutro filesystem faz o `Rename` falhar com `EXDEV`
  - validar antes do rename é o que faz "existe arquivo com o nome final"
    significar "conteúdo íntegro"; é a defesa contra o 200-com-HTML
  - `archive/zip` quer `io.ReaderAt`, então validar o arquivo temporário, não
    o stream, sai de graça
- [ ] nome do temporário único por execução, para duas execuções nunca
      escreverem o mesmo arquivo intercalado

Testes:

- [ ] ZIP válido chega ao nome final, com tamanho e sha256 certos
- [ ] corpo HTML **não** produz arquivo final e não deixa temporário
- [ ] erro no meio do `io.Copy` não deixa lixo no diretório

## Passo 4 — CLI e o laço

`cmd/fetch/main.go`

- [ ] flags `-from` e `-to` em `YYYY-MM-DD`, por um `flag.Value` próprio, para
      o erro sair no `flag.Parse` como erro de uso
- [ ] sem as duas flags: só hoje
- [ ] `to` depois de hoje é erro de uso — não há nada lá, e aceitar significa
      registrar o 404 de uma data que não existe
- [ ] laço por data: `Fetch` → `Save`
- [ ] três classes de erro:
  - **fatal** (credencial recusada, diretório não gravável, disco cheio) →
    aborta a execução
  - **da data** (404, transitório) → conta e segue; uma intermitência não
    pode matar 119 downloads bons
  - **sessão expirada** → re-login e repete **essa** requisição; segunda vez
    seguida vira fatal
- [ ] resumo no fim: `baixadas=87 sem-edicao=30 falhou=3`
- [ ] exit code honesto: `0` só se nada falhou, `1` se alguma data falhou,
      `2` erro de uso. Sem registro em disco, o exit code e o resumo
      são a única forma de saber que a execução foi parcial
- [ ] dizer no `--help` que **não há retomada**: sem registro de estado, cada
      execução baixa tudo de novo

## Adiado, de propósito

- DO1E, a edição extra. Quando entrar, a unidade de trabalho passa de data
  para (data, seção), o que muda a chave do registro de estado — e 404 em DO1E
  é o caso normal, então ele não pode ser logado como o 404 de DO1
- registro de estado por data (`baixada` / `sem-edicao` / `pendente` /
  `falhou` / `fora-da-janela`) e, com ele, idempotência e `--forcar`
- concorrência limitada entre datas
- retentativa com backoff e respeito ao `Retry-After`
- Dockerfile, serviço do compose e alvo do `make`
- `make test` rodando Go em container e CI
- ADR 0005

Duas apostas baratas para não repintar quando o registro chegar:

- [ ] classificar o desfecho de cada data num tipo
      (`baixada`/`sem-edicao`/`falhou`) já no passo 4 e usar isso no resumo.
      Persistir depois passa a ser escrever os mesmos valores num arquivo
- [ ] **não** fingir idempotência com `os.Stat`: "o arquivo existe" não
      distingue ZIP íntegro de HTML salvo com nome `.zip`, de truncado, nem
      de zero byte

## Decisões em aberto

- Formato do registro de estado, quando chegar: JSONL append-only (resiste a
  processo morto no meio, melhor sob concorrência) ou um JSON reescrito a cada
  execução (mais fácil de ler). Preferência atual: JSONL
- Janela servida pelo INLABS: data anterior à janela devolve 404 igual a "não
  houve edição". Tratar os dois como a mesma coisa grava `sem-edicao` para
  datas que tiveram edição. Resolver com estado próprio (`fora-da-janela`) ou
  recusando no input — fica para a fase do registro
