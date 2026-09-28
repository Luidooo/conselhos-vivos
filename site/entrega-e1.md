---
title: Entrega E1
outline: [2, 3]
---

# Entrega E1 · Fonte transacional modelada e populada

Cada item do [checklist de aceite da E1](https://unb-bd2.github.io/PlanoEnsino/projeto/e1/), na ordem da página da disciplina, com o lugar exato onde conferir.

::: tip Conferir em máquina limpa
```bash
git clone https://github.com/Luidooo/conselhos-vivos.git && cd conselhos-vivos
make setup    # cria o .env, sobe o Postgres, aplica as migrações e carrega a planilha
make test     # infra, esquema, leitura da planilha, identidade dos conselhos e carga
```
Pré-requisitos: Docker com Compose v2 e `make`. Detalhes em [Como rodar](/visao-geral#como-rodar).
:::

## 1. Domínio e pergunta de gestão

**Domínio:** a produção decisória dos conselhos nacionais de participação social, lida no Diário Oficial da União.

**Pergunta:** *Quais conselhos nacionais de participação social ainda estão funcionando?*

Conferir: [Visão geral](/visao-geral).

## 2. Esquema físico versionado, com migrações executáveis do zero em ordem

- Migrações numeradas em [`sql/`](https://github.com/Luidooo/conselhos-vivos/tree/main/sql), de `001` a `006`.
- `make migrate` ([`scripts/migrate.sh`](https://github.com/Luidooo/conselhos-vivos/blob/main/scripts/migrate.sh)) aplica cada arquivo uma vez, em ordem e dentro de uma transação, e registra em `schema_migrations`. Uma migração que quebra no meio é desfeita inteira: essa garantia foi medida no [ADR 0002](/docs/adr/0002-manter-postgresql-como-motor-do-oltp#medicao).
- Chaves, restrições e `COMMENT ON` são testados por [`tests/db/test_schema.sh`](https://github.com/Luidooo/conselhos-vivos/blob/main/tests/db/test_schema.sh). Cada recusa confere o nome da restrição que recusou.

## 3. Carga reprodutível com um comando, sem passo manual

- `make setup` (ou `make carga` num banco que já existe) lê a planilha versionada e grava conselhos, atos e classificações. É idempotente: rodar de novo não duplica nada.
- A leitura usa só a biblioteca padrão do Python, num serviço do compose sem rede: [ADR 0003](/docs/adr/0003-carregar-a-planilha-como-rotulo-da-curadoria).
- Cada carga reescreve o [relatório da planilha](/docs/carga/relatorio-planilha), que diz quantas linhas entraram e quantas foram descartadas, e por quê.

## 4. Volume

- **215 atos** de 5 conselhos (2003–2020), todos com a classificação da pesquisadora: [relatório da carga](/docs/carga/relatorio-planilha).
- **125 nomes → 82 conselhos**, com renomeações em `orgao_nome` e grafias em `orgao_alias`: [identidade dos conselhos](/docs/carga/relatorio-conselhos).
- O relatório da carga explica por que o número é 215, e não os 2.638 contados no primeiro dia: eram linhas com formatação, mas sem valor.

## 5. Caracterização da carga de trabalho

Volume, taxa de escrita e leitura, padrão de acesso e latência tolerada, com números do domínio: [ADR 0001 · Contexto](/docs/adr/0001-adotar-sistema-de-curadoria-insert-only-como-oltp#contexto).

## 6. Como a origem trata histórico

**Insert-only** na classificação: reclassificar é uma linha nova, a view `classificacao_vigente` devolve a última de cada revisor, e um trigger bloqueia `UPDATE` e `DELETE`. A comparação com CRUD foi medida: [ADR 0001 · Medição](/docs/adr/0001-adotar-sistema-de-curadoria-insert-only-como-oltp#medicao).

Os nomes dos órgãos guardam vigência em `orgao_nome`, e os atos retificados ganham nova `versao` sem sobrescrever a anterior.

## 7. ADR sobre a modelagem do sistema de origem

| ADR | Decisão |
|---|---|
| [0001](/docs/adr/0001-adotar-sistema-de-curadoria-insert-only-como-oltp) | O OLTP é o sistema de curadoria, com classificação insert-only |
| [0002](/docs/adr/0002-manter-postgresql-como-motor-do-oltp) | O OLTP continua em PostgreSQL 16 (benchmark com 5 motores) |
| [0003](/docs/adr/0003-carregar-a-planilha-como-rotulo-da-curadoria) | A planilha entra como rótulo da curadoria |
| [0004](/docs/adr/0004-resolver-identidade-dos-conselhos-por-chave-e-decisao-registrada) | A identidade dos conselhos sai de uma chave mais decisões registradas |

## 8. README para subir tudo com Docker Compose

[Visão geral · Como rodar](/visao-geral#como-rodar): `make setup` e `make test`, a tabela de serviços e o que fazer com porta ocupada.

## Processo da squad

- Diários: [25/09](/docs/diario/2026-09-25) e [26/09](/docs/diario/2026-09-26).
- Registro de uso de IA, uma entrada por uso: [AI-USAGE](/AI-USAGE).
- Histórico e revisões entre pares: [pull requests](https://github.com/Luidooo/conselhos-vivos/pulls?q=is%3Apr).
