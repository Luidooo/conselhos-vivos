# 0011 — Disponibilizar as métricas por uma camada semântica no MetricFlow, levar os alertas ao Postgres por push e dar a cada serviço um papel com privilégio mínimo

- **Status:** proposto
- **Data:** 2026-11-24
- **Decisores:** a squad — Luis (@Luidooo), Bruno (@BrunoBReis), Moura (@thegm445), Iago (@iagorrr), Luiza (@LuizaMaluf), Marcio (@DeM4rcio)

## Contexto

A E3 entregou a gold e um painel que responde à pergunta da E1 ([ADR 0009](0009-modelar-a-gold-em-estrela-com-dbt-e-orquestrar-com-dagster.md)). A E4 pede quatro coisas:
- que o dado chegue a quem decide por dois caminhos, o painel e uma camada semântica com a definição de cada métrica;
- que uma métrica volte a um sistema operacional onde alguém age;
- que o acesso siga o privilégio mínimo;
- que o dado pessoal seja tratado com base legal.

Até a E3, o painel calculava "atos por mês" no próprio código, e esse número não existia fora dele.

## Decisão

1. **Camada semântica no MetricFlow do dbt.** As métricas `atos_publicados`, `atos_classificados`, `atos_de_autorregulacao`, `proporcao_autorregulacao` e `mencoes_recebidas` ficam definidas uma vez, no YAML dos modelos. As consultas salvas `atividade_por_mes` e `atividade_por_conselho` viram CSV em `data/gold/metricas/` depois da gold, no job mensal. O painel lê esses CSVs; quem quiser os números fora do painel abre o mesmo arquivo.
2. **Cópia por arquivo, não federação nem warehouse.** O consumo lê CSV e o DuckDB em modo só leitura. Não há servidor de consulta a manter.
3. **ETL reverso por push.** Depois da gold, o job grava na tabela `alerta` do Postgres a situação que pede ação. A gravação é idempotente e não reescreve alerta já tratado. A pesquisadora trata o alerta na página Revisar do painel.
4. **Papéis com privilégio mínimo:**
   - `etl_reverso` só escreve alerta;
   - `app_curadoria` lê o alerta e o nome do revisor, nunca o e-mail (o recorte de coluna), e só marca o alerta como tratado;
   - `leitor_analitico` é o dbt lendo os órgãos.

   O dado pessoal que esses papéis protegem, com a base legal, a retenção e o descarte, está na [análise de LGPD](../lgpd.md).

## Alternativas consideradas

- **Visões materializadas escritas à mão, a opção nula da camada semântica:** um modelo `metricas` no dbt, com a definição na descrição de cada coluna. Não pede dependência nova e lê igual. Perde a validação da definição (`mf validate-configs`), as métricas de razão sem SQL novo e a consulta por dimensão sob demanda. Medido: o mesmo "atos por mês" em SQL direto levou 0,005 s, contra 8,2 s do `mf query`, que inclui a subida do MetricFlow (`medicoes.txt`). Os 8 s são pagos uma vez por mês, no job, e não por quem abre o painel.
- **CSV agendado direto da gold, sem camada semântica:** é a opção nula do consumo. O arquivo seria o mesmo, mas a definição da métrica voltaria a morar no SQL de quem exporta.
- **Federação (o painel consultando o Postgres e o Delta ao vivo) ou um warehouse:** mais um serviço para a pesquisadora manter, para um volume de 4,1 MB de gold.
- **ETL reverso por pull (a curadoria consulta a gold quando quer):** o alerta não chegaria a quem age. O enunciado pede que a métrica volte ao sistema operacional.
- **Row-level security no lugar do recorte de coluna:** não há hoje um recorte de linha com sentido de negócio. O dado pessoal está numa coluna, o e-mail do revisor.

## Consequências

- **Um número, uma definição:** o painel não recalcula a métrica, e a camada semântica é validada a cada `make metricas`.
- **O job mensal ganha dois passos depois da gold, com o mesmo retry.** O MetricFlow abre o DuckDB para escrita, então a exportação só roda em sequência com o dbt.
- **A página Revisar fala com o Postgres.** Ela só roda em `127.0.0.1` e não tem login: quem marca o alerta escolhe o próprio nome na lista.
- **O superusuário ainda roda a carga, o lake e o CDC.** Os papéis novos cobrem o consumo, não a ingestão.
- **Alerta que deixou de valer não fecha sozinho.** Se a gold muda e a regra para de apontar um conselho, o alerta aberto continua na tabela até a curadoria fechá-lo na página Revisar.

## Medições

De 24/11/2026, num banco refeito do zero com a planilha e o DOU de julho a setembro de 2026, menos a linha do ETL reverso, que é do banco de trabalho da squad, com os mesmos três meses. As provas estão em [`medicoes/0011-disponibilizacao/`](https://github.com/Luidooo/conselhos-vivos/tree/main/docs/adr/medicoes/0011-disponibilizacao).

| O que | Resultado | Prova |
|---|---|---|
| `mf query` das consultas salvas | 3 linhas em 8,2 s (`atividade_por_mes`) e 37 linhas em 5,7 s (`atividade_por_conselho`) | `medicoes.txt` |
| SQL direto, opção nula | os mesmos números (94, 56 e 93 atos em julho, agosto e setembro), em 0,005 s | `medicoes.txt` |
| ETL reverso, duas rodadas, no banco de trabalho | `novos=10`, depois `inalterados=10`; no banco refeito do zero deu o mesmo | `alertas-idempotencia.txt` |
| Job mensal com os dois passos novos | `RUN_SUCCESS` | `backfill-*.txt`, `grafo-dagster.jpg` |
| Controle de acesso | 19 casos em `ok`, com os 5 do `app_perguntas` (#107) | `acesso.txt`, a saída do `bash tests/db/test_acesso.sh` |

## Gatilho de revisão

- A pesquisadora pedir métrica por uma dimensão que o MetricFlow não junte sozinho: por exemplo, pelo nome vigente do conselho, que mora numa dimensão de variação lenta.
- O `dbt-metricflow` ficar sem versão compatível com o dbt-core que o projeto usar.
- O painel sair de `127.0.0.1` ou ganhar mais de um usuário: aí a página Revisar precisa de login, e o `tratado_por` deixa de ser escolhido numa lista.
- Aparecer um recorte por linha com sentido, como bolsistas que só tratam alertas de alguns conselhos: aí entra RLS em `alerta`.
