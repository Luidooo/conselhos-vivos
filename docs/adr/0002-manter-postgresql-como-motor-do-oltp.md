# 0002 — O OLTP de curadoria continua em PostgreSQL 16

- **Status:** proposto
- **Data:** 2026-09-26
- **Decisores:** a confirmar no PR — Luis (@Luidooo), Bruno (@BrunoBReis), Moura (@thegm445), Iago (@iagorrr), Luiza (@LuizaMaluf)

## Contexto

O PostgreSQL entrou no projeto pela issue #1 sem decisão registrada. O ADR 0001 fixou **o que** o OLTP guarda; este decide **em que motor** ele roda, antes que o esquema dependa mais dele.

**Carga** (ver ADR 0001): ~12 classificações humanas/ano; carga inicial de 215 atos; leitura por chave na tela de curadoria e agregação diária para o indicador. Carga pequena: **desempenho não deve decidir**, e a medição confirma.

**O que o nosso esquema exige do motor** (ADR 0001, `sql/001_schema.sql`, `scripts/migrate.sh`):

- **C1** migração atômica: o `make migrate` roda cada arquivo numa transação, e uma migração que quebra no meio não pode deixar o esquema pela metade;
- **C2** um só nome vigente por órgão (`uq_orgao_nome_vigente`);
- **C3** apagar um ato não pode apagar julgamento humano (FK `RESTRICT`);
- **C4** `CHECK`: ato do DOU exige `id_dou` e `conteudo`;
- **C5** classificação insert-only: `UPDATE` bloqueado por trigger.

**Restrições:** software livre, rodando no Docker Compose (regra da disciplina); a pesquisadora vai operar sozinha, então o custo de operação pesa; **a E2 exige CDC** a partir do OLTP.

## Alternativas consideradas

### A. Opção nula: continuar no PostgreSQL 16 que já está no compose

### B. MySQL 8.4 · C. MariaDB 11.4

Os relacionais livres mais usados; o Debezium lê o binlog deles tão bem quanto o WAL do Postgres.

### D. SQLite

A candidata mais séria contra a nula: um arquivo, sem servidor, zero operação, o que o briefing pede para uma pesquisadora sozinha.

### E. Cassandra 5.0

Não relacional. Entra para medir o que se perde saindo do modelo relacional; o XML do DOU sugere "documento", mas a curadoria é relacional.

## Medição

**Como reproduzir**, da raiz do repositório (sobe containers descartáveis em portas livres de `127.0.0.1`, não toca o banco do projeto):

```bash
uv run docs/adr/medicoes/0002-motor/bench.py
```

**Condição:** Mac Apple Silicon, Docker Desktop 29.6.2, imagens oficiais `postgres:16.15`, `mysql:8.4`, `mariadb:11.4`, `cassandra:5.0` e SQLite 3 do Python. C1–C5 foram **executadas**, não lidas na documentação. Q1/Q2: mediana de 7 execuções após aquecimento, dados sintéticos no volume do domínio (n = 2.638 e 10×, ~12× e ~120× a carga inicial real de 215 atos, recontada em 26/09), medidos pelo cliente. O benchmark rodou duas vezes com resultados estáveis. Dados brutos em `docs/adr/medicoes/0002-motor/resultados.json`.

| | PostgreSQL | MySQL | MariaDB | SQLite | Cassandra |
|---|---|---|---|---|---|
| C1 migração que quebra no meio é desfeita | ✅ | ❌ tabela órfã | ❌ tabela órfã | ✅ | ❌ tabela órfã |
| C2 um nome vigente por órgão | ✅ nativo | ✅ contorno (coluna gerada) | ✅ contorno | ✅ nativo | ❌ aceita dois |
| C3 apagar ato com classificação | ✅ recusa | ✅ recusa | ✅ recusa | ❌ **aceita** (só recusa com `PRAGMA foreign_keys = ON`) | ❌ aceita |
| C4 `CHECK` | ✅ | ✅ | ✅ | ✅ | ❌ aceita |
| C5 `UPDATE` bloqueado | ✅ | ✅ | ✅ | ✅ | ❌ aceita e **alterou o indicador** (DEF −1, IP +1) |
| CDC na configuração padrão | `wal_level=replica` (precisa `logical`) | binlog `ROW` ligado | binlog desligado | não existe | desligado |
| Q1 vigente de 1 ato, n = 2.638 / 26.380 | 0,22 / 0,27 ms | 0,20 / 0,24 ms | 0,21 / 0,37 ms | 0,01 / 0,01 ms¹ | 0,77 / 0,70 ms |
| Q2 indicador, n = 2.638 / 26.380 | 3,7 / 21,9 ms (3,0 / 15,4 com `DISTINCT ON`) | 6,8 / 73,0 ms | 7,9 / 27,9 ms | 3,2 / 33,5 ms¹ | 136 / 118 ms² |
| Download da imagem (comprimida) | 159 MB | 234 MB | 101 MB | — | 168 MB |
| Até aceitar conexão | 1,3 s | 6,2 s | 3,2 s | 0 s | 57,5 s |
| RAM após a carga | **41 MB** | 547 MB | 166 MB | no processo da aplicação | 4.744 MB |

¹ SQLite roda dentro do processo, sem rede: a comparação de latência o favorece.
² Cassandra não tem `JOIN` nem agregação global: o indicador varre a tabela e agrega no cliente.

**Leitura.** Desempenho não separa os relacionais: o pior Q2 a 10× (73 ms) está longe do gatilho de 1 s do ADR 0001. O que separa é o comportamento sob erro:

- **MySQL e MariaDB** deixam uma migração quebrada pela metade (C1). O `schema_migrations` não registra o arquivo, e o `make migrate` seguinte quebra com "tabela já existe". O MySQL ainda usa 13× a RAM do Postgres.
- **SQLite** passa em C1, C2, C4 e C5 e é o mais barato de operar. Mas vem com a **chave estrangeira desligada**: um script que esquecer o `PRAGMA` apaga julgamento humano sem erro (C3). E **não tem CDC**, que a E2 exige.
- **Cassandra** falha em C2 a C5, sobe em ~1 min e ocupou 4,7 GB de RAM. O C5 mostrou na prática o que o insert-only protege: o `UPDATE` aceito mudou o indicador.

## Decisão

**Mantemos o PostgreSQL 16** (opção nula) como motor do OLTP de curadoria.

## Consequências

**O que ganhamos:** migrações atômicas (C1), e as cinco garantias do esquema nativas, sem contorno; o menor consumo de RAM entre os servidores medidos (41 MB); o ecossistema do domínio, com o Ro-dou (Ministério da Gestão) carregando o INLABS em Postgres e o GovHub como referência.

**O que perdemos:**
- **Um servidor para a pesquisadora operar.** Frente ao SQLite, ela precisa do Docker Desktop rodando, 159 MB de download e ~41 MB de RAM, em vez de um arquivo.
- **O CDC não vem pronto.** A E2 precisa de `wal_level=logical`, o que exige mudar a configuração e reiniciar o banco. O MySQL já vem com binlog `ROW`.
- **Dependência de recursos do Postgres.** O esquema já usa `DISTINCT ON` (na view `classificacao_vigente`), índice único parcial, trigger em PL/pgSQL e DDL transacional (no `migrate.sh`).

**O que se torna irreversível:** nenhum dado fica preso. O custo de sair cresce a cada recurso próprio do Postgres. Hoje, migrar para o MySQL exigiria:
- reescrever a view com `ROW_NUMBER()`;
- trocar o índice parcial por uma coluna gerada;
- reescrever o trigger;
- **aceitar que o `make migrate` deixa de ser atômico.**

## Gatilho de revisão

- **A pesquisadora não conseguir manter o Docker** na máquina dela (política da instituição, suporte) → reavaliar o SQLite com `PRAGMA foreign_keys = ON` imposto pela conexão, aceitando CDC por recarga em lote na E2.
- **O ADR da E2 escolher recarga em lote em vez de CDC** → o principal argumento contra o SQLite cai; refazer esta medição.
- **O Q2 passar de 1 s** com a carga real (mesmo gatilho do ADR 0001) → o problema é de modelagem, não de motor; os números acima mostram que trocar de motor relacional não resolve.
