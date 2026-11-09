# 0008 — Unificar o pipeline em Python e descontinuar o cliente do INLABS sem portar

- **Status:** proposto
- **Data:** 2026-11-08
- **Decisores:** a confirmar no PR — Luis (@Luidooo), Bruno (@BrunoBReis), Moura (@thegm445), Iago (@iagorrr), Luiza (@LuizaMaluf)
- **Plano:** [migração do ingestor Go para Python](../planos/2026-10-13-migracao-ingestor-go-para-python.md), fatias F1 a F5 (#51 a #57)

> **A decisão sobre o INLABS ainda não foi tomada pela squad.** A #56 pede essa decisão, e a opção escolhida aqui é a recomendada pelo plano. O PR que traz este ADR é o lugar de aprovar ou recusar. O ADR passa a "aceito" só depois disso.

## Contexto

O pipeline nasceu com duas linguagens: Go no ingestor e Python em planilha, conselhos e lake. A E3 traz dbt e orquestração, também em Python. A chave do órgão ([ADR 0004](0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada.md)) existia nas duas linguagens, com um teste de paridade entre elas.

As fatias F1 a F3 (#53, #54, #55) já levaram para `src/dou/` tudo o que roda de verdade: `fetch-mensal`, `extract` e `persist`. O que restava em Go era:

- **O cliente do INLABS:** `internal/inlabs`, `cmd/fetch` e `internal/config`. O login dele é recusado a scripts desde 12/10 (`502` em `logar.php`, inclusive com o script oficial; #42).
- **Código já sem uso em produção:** `internal/dadosabertos` e `cmd/fetch-mensal`, que nenhum serviço do compose executava mais, só a suíte de testes em Go. O `internal/store` não estava nessa conta: o `cmd/fetch` o importava, e era a gravação do cliente do INLABS.

## Alternativas

### Linguagem do pipeline

| | A. Manter as duas (opção nula) | **B. Tudo em Python (escolhida)** | C. Tudo em Go |
|---|---|---|---|
| Custo de migrar | nenhum | F1 a F3 já feitas | reescrever planilha, conselhos e lake |
| Toolchains no CI | dois | um | um |
| Chave do órgão | em dois lugares | em um | em um |
| Orquestrador da E3 | chama binário Go por shell | chama Python | chama Go, mas dbt e Delta seguem em Python |

### Cliente do INLABS

| | **a. Descontinuar sem portar (proposta)** | b. Portar com `urllib` + `cookiejar` | c. Manter só ele em Go |
|---|---|---|---|
| Código novo | nenhum | o cliente inteiro, sem poder exercitá-lo contra o INLABS | nenhum |
| Toolchains | um | um, mais `tzdata` na imagem slim | dois, por um comando que não funciona |
| ZIP baixado à mão | continua entrando | continua entrando | continua entrando |

## Critério

Onde fica o código que a E3 orquestra e que a pesquisadora vai manter; o custo de manter a chave do órgão em dois lugares; e o que roda de verdade hoje. A fonte automática real é a mensal ([ADR 0005](0005-ingerir-dou-no-oltp-e-propagar-ao-delta-via-cdc.md)), e ela já está em Python.

## Medições

Os números vêm das entradas da migração em [`AI-USAGE.md`](../../AI-USAGE.md) (F1 a F3), todos sobre a Seção 1 de agosto de 2026 (`S01082026.zip`):

| Fatia | Prova | Resultado |
|---|---|---|
| F1 `fetch-mensal` | `cmp` do ZIP baixado por Go e por Python | idêntico, 52.565.336 bytes |
| F2 `extract` | `diff` da saída normalizada com `jq -c -S` | vazio nas 8.590 matérias; 120 imagens e 0 falhas nos dois |
| F2 tempo do parser | a mesma execução | Go 2,1 s; Python 9,5 s |
| F3 prova cruzada | `persist` em Python sobre o banco gravado pelo Go | `gravadas=0 versoes-novas=0 inalteradas=96 orgao-desconhecido=8494`; foto de `ato` e `orgao_alias` idêntica antes e depois |
| F3 prova A/B | banco zerado, `persist` em Python do zero | mesma foto do Go: 96 atos e 748 aliases |
| F3 risco Unicode (#40) | chave de toda linha de `orgao_alias` recalculada em Python | bateu |

**O que não existe:** as fotos em si não foram versionadas. O diretório `docs/adr/medicoes/0008-linguagem-unica/` previsto no plano nunca foi criado, então a prova da F3 é só o registro em texto. Também não há registro do tempo do `persist` em Go contra Python.

## Decisão

1. **O pipeline fica em Python.** O ingestor é o `src/dou/`, e o código em Go sai do repositório.
2. **O cliente do INLABS é descontinuado sem porte** (opção a, proposta). Portá-lo produziria código que ninguém consegue exercitar.
3. **O contrato do bronze diário fica.** `data/bronze/inlabs/AAAA-MM-DD-DO1[E].zip` baixado à mão continua sendo lido por `make extract DATA=` e `make persist DATA=`. Os marcadores `.sem-edicao` e `.falhou` continuam respeitados, e um `.falhou` continua fazendo esses comandos saírem com erro. O `src/dou/bronze.py` mantém o código e os testes dos marcadores.
4. **`make vet-py` substitui `make vet-go` no CI:** `python -W error -m compileall -q src tests`, só com a biblioteca padrão.

## Consequências

**O que ganhamos:**
- Um toolchain, uma suíte de testes e uma chave do órgão.
- Menos configuração: saem dois serviços e dois volumes do compose, e as credenciais do INLABS saem do `.env.example`.

**O que perdemos:**
- **A busca automática por dia.** Saem o `make fetch`, o `make ingest` e o `make ingest-dia`. O dia corrente depende de baixar o ZIP no navegador; a fonte automática só traz meses fechados, cerca de duas semanas depois do fim do mês.
- **A janela de reprocessamento da E2 (#31).** Saem o `make janela` e o `tests/ingest/test_janela.sh`, porque a janela só existia para o `make ingest`. O código entregue na E2 continua na tag `e2`. A idempotência do `persist` e o `tests/lake/test_atrasado.sh` continuam valendo.
- **A limpeza automática dos marcadores.** Um `.falhou` antigo não some quando o ZIP é baixado à mão, porque era o cliente que o apagava. É preciso apagá-lo à mão.
- **Velocidade do parser:** de 2,1 s para 9,5 s por mês, aceitável para um job mensal.
- **`go vet` e `gofmt`.** O `compileall` só pega erro de sintaxe e aviso de compilação, bem menos do que o `go vet` pegava, e nada checa o formato como o `gofmt` checava. O `test-go` rodava `go test -count=1 ./...`, sem `-race`, então não há detector de corrida a perder; o teste de corrida do bronze usa threads de verdade.

**O que se torna irreversível:** nada. O Go fica no histórico do git e na tag `e2`.

## Gatilho de revisão

- **O INLABS voltar a aceitar login por script:** reavaliar portar `internal/inlabs` com `urllib` e `cookiejar`, e trazer a janela de volta. A imagem slim precisaria de `tzdata`.
- **O parser em Python ficar lento demais para o job mensal:** o limite ainda não foi definido e cabe à squad. A referência é 9,5 s em agosto de 2026.
