# 0001 — O OLTP do projeto é o sistema de curadoria, com classificação insert-only

- **Status:** proposto
- **Data:** 2026-09-26
- **Decisores:** a confirmar no PR — Luis (@Luidooo), Bruno (@BrunoBReis), Moura (@thegm445), Iago (@iagorrr), Luiza (@LuizaMaluf)

## Contexto

O projeto mede a vitalidade dos conselhos nacionais de participação social a partir do que eles publicam no DOU, classificando cada ato numa tipologia de 5 categorias (`DEF`, `FISC`, `GEST`, `AUTO`, `IP`). A E1 pede uma fonte transacional própria. A pergunta é **onde, neste domínio, um dado nasce por um evento transacional nosso**: o DOU nasce na Imprensa Nacional, e copiá-lo é ingestão, não transação. O espelho do DOU é a camada bronze, que é OLAP e vem na E2.

**Caracterização da carga** (números do domínio, diário de 25/09):

| Dimensão | Valor | Fonte |
|---|---|---|
| Carga inicial | 2.638 atos classificados à mão, 2003–2022, em 5 conselhos | planilhas da pesquisadora |
| Taxa de escrita humana | ~130 classificações/ano (2.638 em ~20 anos, uma pessoa) | idem |
| Fluxo do DOU | ~300 matérias/dia útil na Seção 1; ~2,5 GB de XML/ano desde 2020 | INLABS |
| Fração do DOU que é ato de conselho | **não medida** — depende do ingestor (#6) | — |
| Identidade dos conselhos | 125 linhas → 96 nomes distintos após normalização; renomeações por lei | aba "Conselhos mapeados" |
| Padrão de acesso | por chave (a tela de curadoria abre um ato) + agregação diária (indicador por conselho) | — |
| Latência tolerada | tela de curadoria: interativa; indicador: lote diário | — |

**Restrições:** a pesquisadora vai operar o sistema sozinha (custo de operação mínimo); a fronteira entre `DEF` e `GEST` é interpretação jurídica, então um classificador automático vai errar e precisa ser corrigível; ninguém na squad opera Kafka ou banco distribuído, e a carga acima não pede isso.

## Alternativas consideradas

### A. Opção nula: não ter OLTP próprio — as planilhas continuam sendo o registro

Viável: é o que existe hoje e funcionou por 20 anos. Não foi escolhida porque as 5 abas têm esquemas divergentes (o método mudou com o tempo), não há integridade nem histórico de reclassificação, e o projeto viraria só pipeline analítico: sem lugar para a pesquisadora corrigir o classificador, a acurácia humano × máquina não é mensurável.

### B. Espelho do DOU no Postgres como OLTP

Cumpre a letra do requisito. Mas o dado nasceu na Imprensa Nacional, e ninguém dá `UPDATE ... WHERE id = ?` nele: é a camada bronze da E2, com outra carga de trabalho.

### C. Entidades do Brasil Participativo (composição, mandatos, reuniões)

Têm ciclo de vida real e mudam de estado, mas também nascem fora do nosso sistema, e não guardam a classificação, que é o que o projeto produz.

### D. Sistema de curadoria (escolhida), em duas variantes de modelagem

É o único lugar onde o dado nasce aqui: o julgamento humano sobre um ato não existe em fonte nenhuma antes. Modelagem comum às duas variantes: `orgao` com `orgao_nome` com vigência (o CONAMA muda de ministério em 2023 sem quebrar a série), `ato` com `origem` DOU|PLANILHA e `versao` para retificações.

- **D1 — CRUD:** uma linha por ato × revisor; mudar de ideia é `UPDATE`.
- **D2 — insert-only (escolhida):** reclassificar é nova linha; a view `classificacao_vigente` devolve a última de cada revisor; um trigger bloqueia `UPDATE`/`DELETE`.

## Medição

A escolha entre A, B, C e D **não tem benchmark**: o critério é onde o dado nasce, não desempenho. A escolha entre D1 e D2 tem, e foi medida.

**Como reproduzir** (banco migrado; roda numa transação desfeita, não altera o banco):

```bash
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v n=2638' \
  < docs/adr/medicoes/0001-classificacao-vigente.sql
```

**Condição:** PostgreSQL 16.15 no Docker Desktop 29.6.2, Mac Apple Silicon; mediana de 5 execuções. Atos e classificações **sintéticos no volume do domínio**: por ato, a pesquisadora classifica de 1 a 3 vezes e o pipeline 1 vez. `n = 2.638` é a carga inicial; `n = 26.380` projeta 10× para quando o DOU entrar. Refazer com a carga real quando a #3 terminar.

| Consulta | n | D1 CRUD | D2 insert-only |
|---|---|---|---|
| Linhas em `classificacao` | 2.638 | 5.276 | 7.915 (+50%) |
| Q1 — vigente de um ato (tela de curadoria) | 2.638 | 0,1 ms | 0,2 ms |
| Q1 | 26.380 | 0,1 ms | 0,1 ms |
| Q2 — distribuição da tipologia vigente (indicador) | 2.638 | 4,1 ms | 16,4 ms (4×) |
| Q2 | 26.380 | 23,5 ms | 126,3 ms (5,4×) |
| Q3 — atos em que a pesquisadora mudou de ideia | 2.638 | **impossível** | 8,9 ms |
| Q3 | 26.380 | **impossível** | 112,9 ms |

A correção do modelo é coberta por `tests/db/test_schema.sh` (16 casos, `make test`).

## Decisão

Adotamos o **sistema de curadoria como OLTP**, com a **classificação insert-only** (D2). Os 2.638 atos da pesquisadora entram como carga inicial com `origem = 'PLANILHA'`, e classificamos a **versão** do ato.

## Consequências

**O que ganhamos:** o histórico inteiro do julgamento humano, que é o dado que só existe aqui; a divergência humano × pipeline vira métrica ao longo do tempo (Q3 só existe nesta variante); nenhum julgamento se perde por engano, porque o banco recusa `UPDATE`/`DELETE`; a série histórica sobrevive a renomeação de ministério.

**O que perdemos:**
- **+50% de linhas** em `classificacao` na carga inicial, crescendo a cada reclassificação.
- **O indicador fica 4 a 5,4× mais lento** (Q2: 16,4 ms contra 4,1 ms; 126 ms contra 23,5 ms a 10×). Aceitável num lote diário; não seria numa tela que agregasse a cada clique.
- **Erro de digitação não se corrige no lugar:** uma classificação atribuída ao revisor errado fica para sempre, e a correção é uma linha nova que a sobrepõe. Toda leitura do estado atual precisa passar pela view, e quem esquecer lê o histórico como se fosse o presente.
- **Retificação nasce sem classificação:** a versão 2 de um ato precisa ser reclassificada.
- **Mais uma peça para manter:** o trigger e a view, para uma pesquisadora que vai operar sozinha.

**O que se torna irreversível:** nada de imediato, e essa é a razão de preferir D2 agora. Voltar para CRUD é colapsar a view numa tabela (uma consulta). O caminho inverso não existe: um CRUD adotado hoje apaga o histórico que teríamos no futuro.

## Gatilho de revisão

Refazer a medição acima com a carga real e revisar esta decisão se:

- **Q2 passar de 1 s** de mediana → materializar o estado corrente (tabela `classificacao_atual` mantida por trigger);
- **Q1 passar de 50 ms** → a tela de curadoria deixa de ser interativa;
- **a pesquisadora pedir para apagar uma classificação** (por exemplo, por LGPD) → o bloqueio de `DELETE` precisa de uma exceção auditada.
